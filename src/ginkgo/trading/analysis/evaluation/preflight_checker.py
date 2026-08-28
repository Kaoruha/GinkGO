# Upstream: gate_definitions (G0 质量阈值), task_helpers.preflight_data_coverage (#6282 覆盖口径),
#           bar_crud.find_by_code_and_date_range (bar 序列), adjustfactor_service.get (因子序列)
# Downstream: evaluation_cli (eval preflight), EvaluationService/API (M3 聚合)
# Role: G0 数据质量预检 — 在 #6282 覆盖(数量)之上补缺口/日历对齐/复权一致三项质量检查


"""
PreflightChecker — 回测前数据质量预检 (G0 质量项)

与 #6282 覆盖检查的关系: 覆盖查「数量」(bar_count ≥ min_bars)，本模块查「质量」:
1. bar 缺口/日历对齐: 每 code 的日期集 vs 基准日历(多数决) → 缺失列表 + 缺口率
2. 复权一致: 前复权因子序列回跳计数 (回跳=混入不同口径数据)
3. 样本量: 复用覆盖结论
4. 动态 selector probe: codes 为空时窗口内采样调 pick() (契约驱动, 对开放扩展的
   selector 世界零假设) — 异常报 blocker、恒空报空转 warning、返回则抽样按 code 预检
5. 数据底座密度: 窗口内按日 distinct code 画像 (selector 无关, g0_universe_density)

gate 全集 vs 求值子集: g0_bar_gap / g0_adjustfactor_consistency 声明在
gate_definitions (单一事实源)，由本模块在 portfolio+窗口侧求值；
funnel (task 侧) 不含这两条 — M3 EvaluationService 聚合两路。

纯计算核心 (evaluate_calendar_alignment / evaluate_factor_reversals) 不碰 DB，
单测直接喂构造序列; 取数 (bar/因子) 由构造注入，CLI/Service 层装配。
"""

from dataclasses import dataclass, field
from datetime import date as Date, datetime as DateTime, timedelta as TimeDelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.evaluation.gate_definitions import get_gate

# 缺口率两档: >BLOCKER 挡回测, (WARNING, BLOCKER] 进 issues 明细
GAP_WARNING_PCT = 5.0
GAP_BLOCKER_PCT = 20.0

# 动态 selector probe: 窗口内采样时点数 / 抽样进按 code 预检的只数
PROBE_SAMPLE_POINTS = 3
PROBE_SAMPLE_CODES = 5

DateSeries = Dict[str, set]  # {code: {date, ...}}
FactorSeries = Sequence[Tuple[Date, float]]  # [(date, fore_adjustfactor), ...] 按时间升序
DailyCounts = Dict[str, int]  # {"YYYY-MM-DD": distinct_code_count}


@dataclass
class QualityIssue:
    """单条质量问题 (前端行动列表直接渲染)"""

    code: str
    kind: str  # sparse / gap / calendar_misalign / factor_reversal / factor_missing
    severity: str  # blocker / warning
    detail: str
    remediation: str = ""

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "kind": self.kind,
            "severity": self.severity,
            "detail": self.detail,
            "remediation": self.remediation,
        }


@dataclass
class PreflightReport:
    """数据预检报告"""

    portfolio_id: str = ""
    start: str = ""
    end: str = ""
    codes: List[str] = field(default_factory=list)
    coverage: Dict[str, int] = field(default_factory=dict)  # {code: bar_count} (#6282 口径)
    quality: Dict[str, Dict] = field(default_factory=dict)  # {code: {gap_pct, missing_days, factor_reversals}}
    issues: List[QualityIssue] = field(default_factory=list)
    ok: bool = True  # 无 blocker issue
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "portfolio_id": self.portfolio_id,
            "start": self.start,
            "end": self.end,
            "codes": list(self.codes),
            "coverage": dict(self.coverage),
            "quality": {k: dict(v) for k, v in self.quality.items()},
            "issues": [i.to_dict() for i in self.issues],
            "ok": self.ok,
            "notes": list(self.notes),
        }


def evaluate_calendar_alignment(series: DateSeries, warning_pct: float = GAP_WARNING_PCT,
                                blocker_pct: float = GAP_BLOCKER_PCT) -> Dict[str, Dict]:
    """日历对齐检查 (纯计算)

    基准日历 = 出现率 ≥50% codes 的日期集合 (多数决，防单 code 异常污染基准);
    每 code 缺口率 = 基准首末范围内缺失数 / 基准天数。头部缺失 (code 数据晚于基准开始)
    也计入 — 对回测而言「窗口内该日无数据」与断档同害。

    Args:
        series: {code: {date,...}} 窗口内每 code 的 bar 日期集
        warning_pct / blocker_pct: 缺口率两档阈值 (%)

    Returns:
        {code: {"gap_pct": float, "missing_days": int, "missing": [date,...] (最多 10 条示例),
                "severity": "ok"/"warning"/"blocker"}}
    """
    result: Dict[str, Dict] = {}
    if not series:
        return result

    codes = [c for c, dates in series.items() if dates]
    if not codes:
        return {c: {"gap_pct": 100.0, "missing_days": 0, "missing": [], "severity": "blocker"}
                for c in series}  # 全空序列: 无从建基准, 直接按 blocker 报稀疏

    # 基准日历: 每日期出现次数 ≥ 半数 code
    from collections import Counter
    date_counts = Counter(d for dates in (series[c] for c in codes) for d in dates)
    quorum = len(codes) / 2.0
    calendar = sorted(d for d, n in date_counts.items() if n >= quorum)
    if not calendar:
        calendar = sorted(set().union(*(series[c] for c in codes)))  # 退化: 并集兜底

    cal_start, cal_end = calendar[0], calendar[-1]
    cal_set = set(calendar)
    span = calendar[1:-1]  # 首末日剔除: 增量同步下边界日各 code 常有合法时差
    for code, dates in series.items():
        present = dates & cal_set
        if not present:
            result[code] = {"gap_pct": 100.0, "missing_days": len(span),
                            "missing": list(map(str, span[:10])), "severity": "blocker"}
            continue
        # 该 code 有效范围 = 自身首条 bar 到基准末日 (之前的缺失=未上市/未同步, 单独说明)
        own_start = min(dates)
        window = [d for d in span if d >= own_start]
        missing = [d for d in window if d not in dates]
        gap_pct = len(missing) / len(window) * 100.0 if window else 0.0
        severity = ("blocker" if gap_pct > blocker_pct
                    else "warning" if gap_pct > warning_pct else "ok")
        head_missing = sum(1 for d in calendar if d < own_start)
        result[code] = {
            "gap_pct": round(gap_pct, 2),
            "missing_days": len(missing),
            "missing": [str(d) for d in missing[:10]],
            "severity": severity,
            "head_missing_days": head_missing,  # 窗口头部缺失 (未上市/未同步, 非断档)
        }
    return result


def evaluate_factor_reversals(factors: FactorSeries) -> Optional[int]:
    """前复权因子回跳计数 (纯计算)

    正常 fore_adjustfactor 随时间单调不减 (分红/除权只使因子增大或不变);
    回跳 (后值 < 前值) = 疑似混入不同复权口径的数据。

    Returns:
        回跳次数; 序列不足 2 条时 None (无从判定, 调用方报 factor_missing)
    """
    if len(factors) < 2:
        return None
    reversals = 0
    prev = None
    for _, v in sorted(factors, key=lambda x: x[0]):
        if prev is not None and v < prev:
            reversals += 1
        prev = v
    return reversals


class PreflightChecker:
    """G0 数据质量预检 (编排: 取数 → 纯计算 → 报告)

    Args:
        bar_crud: 须支持 find_by_code_and_date_range(code, start, end) -> List[bar]
        factor_loader: Callable[code, start, end] -> FactorSeries;
            None 时跳过复权检查 (报告 notes 说明)
        selector: 已装配的 selector 实例 (契约 = pick(time) -> list[str]);
            codes 为空 (动态 selector) 时窗口内采样 probe — 异常报 blocker、
            恒空报空转 warning、返回 codes 则抽样按 code 预检。
            装配 (component_loader 同路径) 由 Service/CLI 层做, checker 只消费。
        daily_counts_loader: Callable[start, end] -> DailyCounts;
            bar_service.get_daily_code_counts 的包装, 数据底座密度检查用
            (selector 无关, 是动态 selector 盲区的兜底)。
    """

    def __init__(self, bar_crud, factor_loader: Optional[Callable] = None,
                 selector: Any = None, daily_counts_loader: Optional[Callable] = None):
        self._bar_crud = bar_crud
        self._factor_loader = factor_loader
        self._selector = selector
        self._daily_counts_loader = daily_counts_loader

    def check(self, portfolio_id: str, codes: List[str], start, end,
              min_bars: int = 10) -> PreflightReport:
        """执行预检

        Args:
            portfolio_id: 组合标识 (报告归属; codes 由调用方解析, 通常来自 selector)
            codes: 待检股票池 (空=动态 selector → probe 采样, 见 __init__ selector)
            start / end: 窗口边界
            min_bars: 覆盖充足阈值 (#6282 同款)

        Returns:
            PreflightReport — ok=False 表示存在 blocker, 回测前应先修数据
        """
        report = PreflightReport(
            portfolio_id=portfolio_id,
            start=str(start), end=str(end), codes=list(codes),
        )

        # --- 0. 数据底座密度 (selector 无关; 动态 selector 盲区的兜底) ---
        if self._daily_counts_loader is not None:
            self._check_universe_base(report, start, end)

        # --- 0.5 动态 selector probe (codes 空 + 已注入 selector) ---
        if not codes:
            if self._selector is None:
                report.notes.append("动态 selector 未注入 probe，无法按 code 预检，放行")
                report.ok = not any(i.severity == "blocker" for i in report.issues)
                return report
            codes = self._probe_selector(report, start, end)
            report.codes = list(codes)
            if not codes:
                # probe 异常(blocker)/恒空(warning)已写入 issues; 空池无从按 code 预检
                report.ok = not any(i.severity == "blocker" for i in report.issues)
                GLOG.INFO(
                    f"PreflightChecker: portfolio={portfolio_id[:8] if portfolio_id else '-'} "
                    f"probe-空池 issues={len(report.issues)} ok={report.ok}"
                )
                return report

        # --- 取数: bar 序列 (日期) + 复权因子 ---
        series: DateSeries = {}
        factors_by_code: Dict[str, FactorSeries] = {}
        for code in codes:
            try:
                bars = self._bar_crud.find_by_code_and_date_range(code, start, end)
                report.coverage[code] = len(bars) if bars else 0
                series[code] = {
                    b.timestamp.date() if hasattr(b.timestamp, "date") else b.timestamp
                    for b in (bars or [])
                }
            except Exception as e:
                GLOG.WARNING(f"[preflight] load bars failed for {code}: {e}")
                report.coverage[code] = 0
                series[code] = set()
            if self._factor_loader is not None:
                try:
                    factors_by_code[code] = self._factor_loader(code, start, end) or []
                except Exception as e:
                    GLOG.WARNING(f"[preflight] load factors failed for {code}: {e}")
                    factors_by_code[code] = []

        # --- 1. 覆盖 (#6282 口径复用) ---
        for code in codes:
            n = report.coverage.get(code, 0)
            if n < min_bars:
                report.issues.append(QualityIssue(
                    code=code, kind="sparse", severity="blocker",
                    detail=f"仅 {n} 条 bar (<{min_bars})",
                    remediation="ginkgo data sync --code <CODE> 或收窄窗口",
                ))

        # --- 2. 日历对齐 (纯计算; update 合并 — 底座画像 "(universe)" 先写入, 勿整体覆盖) ---
        calendar_quality = evaluate_calendar_alignment(series)
        report.quality.update(calendar_quality)
        for code, q in calendar_quality.items():  # 只迭代 code 条目, 伪 code 无 severity
            if q["severity"] == "blocker":
                report.issues.append(QualityIssue(
                    code=code, kind="calendar_misalign", severity="blocker",
                    detail=f"缺口率 {q['gap_pct']}%，缺 {q['missing_days']} 个交易日",
                    remediation="先补数: ginkgo data sync --code <CODE>",
                ))
            elif q["severity"] == "warning":
                report.issues.append(QualityIssue(
                    code=code, kind="gap", severity="warning",
                    detail=f"缺口率 {q['gap_pct']}%，缺 {q['missing_days']} 日"
                           f" (示例 {', '.join(q['missing'][:3]) or '无'})",
                    remediation="停牌为正常缺口可忽略；数据断档则补数",
                ))

        # --- 3. 复权一致 (纯计算) ---
        if self._factor_loader is None:
            report.notes.append("未注入 factor_loader，复权一致性未检查")
        else:
            gate = get_gate("g0_adjustfactor_consistency")
            for code in codes:
                reversals = evaluate_factor_reversals(factors_by_code.get(code, []))
                if reversals is None:
                    report.quality.setdefault(code, {})["factor_reversals"] = None
                    if report.coverage.get(code, 0) >= min_bars:
                        # 有 bar 却无因子记录: 前复权口径无从验证
                        report.issues.append(QualityIssue(
                            code=code, kind="factor_missing", severity="warning",
                            detail="有 bar 但无 adjustfactor 记录，复权口径未验证",
                            remediation="ginkgo data sync adjustfactor 后复查",
                        ))
                elif reversals > int(gate.threshold):
                    report.quality.setdefault(code, {})["factor_reversals"] = reversals
                    report.issues.append(QualityIssue(
                        code=code, kind="factor_reversal", severity="blocker",
                        detail=f"前复权因子回跳 {reversals} 次，疑似口径混入",
                        remediation=gate.remediation,
                    ))
                else:
                    report.quality.setdefault(code, {})["factor_reversals"] = reversals

        report.ok = not any(i.severity == "blocker" for i in report.issues)
        GLOG.INFO(
            f"PreflightChecker: portfolio={portfolio_id[:8] if portfolio_id else '-'} "
            f"codes={len(codes)} issues={len(report.issues)} ok={report.ok}"
        )
        return report

    # ------------------------------------------------------------------
    # 内部: 动态 selector probe / 数据底座
    # ------------------------------------------------------------------

    def _probe_selector(self, report: PreflightReport, start, end) -> List[str]:
        """窗口内采样调 selector.pick (真实求值, 不碰 advance_time/引擎)

        返回抽样 codes (进按 code 预检); 异常/恒空时写 issues 并返回 []。
        """
        s, e = _to_datetime(start), _to_datetime(end)
        span = (e - s).total_seconds()
        # 窗口内均匀 3 点 (1/6, 1/2, 5/6), 避开首末日增量同步边界
        points = [s + TimeDelta(seconds=span * frac) for frac in (1 / 6, 1 / 2, 5 / 6)]

        picked: List[str] = []
        errors: List[str] = []
        for t in points:
            try:
                codes_t = self._selector.pick(t) or []
                report.notes.append(f"probe {t:%Y-%m-%d}: {len(codes_t)} codes")
                picked.extend(codes_t)
            except Exception as ex:
                msg = f"{t:%Y-%m-%d}: {type(ex).__name__}: {ex}"
                errors.append(msg)
                GLOG.WARNING(f"[preflight] selector probe failed at {msg}")

        if errors and not picked:
            report.issues.append(QualityIssue(
                code="(selector)", kind="selector_error", severity="blocker",
                detail=f"probe {len(errors)}/{len(points)} 时点异常: {errors[0][:120]}",
                remediation="selector 在回测窗口内无法求值，回测将同样失败；先在组件页单测该 selector",
            ))
            return []
        if errors:
            report.issues.append(QualityIssue(
                code="(selector)", kind="selector_error", severity="warning",
                detail=f"probe 部分时点异常 ({len(errors)}/{len(points)})，其余时点可用",
                remediation="回测可能在该时点附近失败，检查 selector 数据依赖",
            ))

        uniq = sorted(set(picked))
        if not uniq:
            report.issues.append(QualityIssue(
                code="(selector)", kind="selector_empty", severity="warning",
                detail=f"probe {len(points)} 时点均返回空，疑似空转回测",
                remediation="检查 selector 参数与数据依赖 (窗口数据是否已同步)",
            ))
            return []

        sample = uniq[:PROBE_SAMPLE_CODES]
        report.notes.append(
            f"probe 去重 {len(uniq)} codes，抽样 {len(sample)} 只按 code 预检"
        )
        return sample

    def _check_universe_base(self, report: PreflightReport, start, end) -> None:
        """数据底座密度: 窗口内按日聚合的 distinct code 画像 (selector 无关)"""
        gate = get_gate("g0_universe_density")
        try:
            daily = self._daily_counts_loader(start, end) or {}
        except Exception as e:
            GLOG.WARNING(f"[preflight] daily counts load failed: {e}")
            report.notes.append(f"底座画像加载失败: {e}")
            return

        if not daily:
            report.issues.append(QualityIssue(
                code="(universe)", kind="universe_empty", severity="blocker",
                detail=f"窗口 [{start}, {end}] 内 bar 表无任何日线数据",
                remediation="先全量补数: `ginkgo data sync`，再回测",
            ))
            return

        counts = sorted(daily.values())
        avg = sum(counts) / len(counts)
        worst = counts[0]
        report.quality.setdefault("(universe)", {})["daily_code_counts"] = {
            "avg": round(avg, 1), "min": worst, "days": len(counts),
        }
        if avg < gate.threshold:
            report.issues.append(QualityIssue(
                code="(universe)", kind="universe_sparse", severity=gate.severity,
                detail=f"日均 distinct code 仅 {avg:.0f} (<{gate.threshold:.0f})，最低 {worst}",
                remediation=gate.remediation,
            ))


def _to_datetime(value) -> DateTime:
    """窗口边界 str/datetime 归一 (probe 采样点计算用)"""
    if isinstance(value, DateTime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
        try:
            return DateTime.strptime(str(value)[:19].strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析窗口边界: {value!r}")
