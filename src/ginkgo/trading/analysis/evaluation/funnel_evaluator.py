# Upstream: AnalysisEngine (_load_data 取数), ParityCalculator, gate_definitions, RollingReport (平稳度)
# Downstream: evaluation_cli (eval funnel), EvaluationService/API (M3)
# Role: 四级漏斗汇总评估 — 输入 portfolio/task，逐 gate 求值出 FunnelReport


"""
FunnelEvaluator — 四级漏斗汇总评估器

G0 回测可信 → G1 回测有效 → G2 模拟一致 → G3 实盘就绪。
逐 gate 求值，状态四态:
- PASS: 通过
- FAIL: 未过 (值可算且越阈)
- INSUFFICIENT_DATA: 样本不足/数据缺失 — 如实报告，不静默降级
- BLOCKED: 依赖未就绪 (如 kill switch) — 不假装通过

level_reached = 最高连续通过级 (该级内全部 blocker gate PASS 才算过级)。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.engine import AnalysisEngine
from ginkgo.trading.analysis.evaluation.gate_definitions import (
    GateDefinition,
    gates_by_level,
    get_gate,
)
from ginkgo.trading.analysis.evaluation.parity_calculator import (
    ParityCalculator,
    ParityResult,
)
from ginkgo.trading.analysis.reports.rolling import RollingReport

PASS = "PASS"
FAIL = "FAIL"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
BLOCKED = "BLOCKED"
LEVELS = ("G0", "G1", "G2", "G3")


@dataclass
class GateResult:
    """单条 gate 求值结果"""

    gate: GateDefinition
    status: str
    value: Optional[float] = None
    detail: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.gate.id,
            "level": self.gate.level,
            "name": self.gate.name,
            "status": self.status,
            "value": self.value,
            "threshold": self.gate.threshold,
            "direction": self.gate.direction,
            "unit": self.gate.unit,
            "severity": self.gate.severity,
            "remediation": self.gate.remediation,
            "detail": self.detail,
        }


@dataclass
class FunnelReport:
    """漏斗报告"""

    portfolio_id: str = ""
    task_id: str = ""
    candidate_task_id: Optional[str] = None
    level_reached: str = ""
    gates: List[GateResult] = field(default_factory=list)
    parity: Optional[ParityResult] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "portfolio_id": self.portfolio_id,
            "task_id": self.task_id,
            "candidate_task_id": self.candidate_task_id,
            "level_reached": self.level_reached,
            "gates": [g.to_dict() for g in self.gates],
            "parity": self.parity.to_dict() if self.parity else None,
            "notes": list(self.notes),
        }

    def failed_blockers(self) -> List[GateResult]:
        """未过的 blocker gate (前端行动列表直接用)"""
        return [
            g
            for g in self.gates
            if g.status in (FAIL, BLOCKED) and g.gate.severity == "blocker"
        ]


class FunnelEvaluator:
    """四级漏斗汇总评估器

    Args:
        analysis_engine: AnalysisEngine 实例 (复用其 _load_data 单一取数路径)
    """

    def __init__(self, analysis_engine: AnalysisEngine):
        self._engine = analysis_engine
        self._parity = ParityCalculator()

    def evaluate(
        self,
        portfolio_id: str,
        task_id: str,
        candidate_task_id: Optional[str] = None,
        stability_window: int = 60,
    ) -> FunnelReport:
        """评估一个回测 task 在漏斗中的位置

        Args:
            portfolio_id: 组合标识
            task_id: 回测 task (G0/G1 数据源, G2 的 baseline)
            candidate_task_id: 模拟盘/对比 task (G2 的 candidate, 缺省时 G2 整级样本不足)
            stability_window: G1 滚动平稳度窗口 (天数)

        Returns:
            FunnelReport
        """
        report = FunnelReport(
            portfolio_id=portfolio_id,
            task_id=task_id,
            candidate_task_id=candidate_task_id,
        )

        try:
            dp = self._engine._load_data(task_id, portfolio_id)
        except ValueError as e:
            report.notes.append(f"回测记录不可用: {e}")
            report.gates = self._all_gates_status(
                INSUFFICIENT_DATA, "回测分析记录不可用"
            )
            report.level_reached = self._compute_level_reached(report)
            return report

        nav = self._get_df(dp, "net_value")
        if nav is None or nav.empty:
            report.notes.append("net_value 链缺失，G0/G1 无法评估")
            report.gates = self._all_gates_status(INSUFFICIENT_DATA, "net_value 缺失")
            report.level_reached = self._compute_level_reached(report)
            return report

        # --- G0 / G1: 从 baseline task 单侧计算 ---
        g0_g1: List[GateResult] = self._evaluate_g0_g1(dp, nav, stability_window)
        report.gates.extend(g0_g1)

        # --- G2: parity (有 candidate 才算) ---
        report.parity = None
        parity_results: List[GateResult] = []
        if candidate_task_id:
            try:
                cand_dp = self._engine._load_data(candidate_task_id, portfolio_id)
                cand_nav = self._get_df(cand_dp, "net_value")
                if cand_nav is not None and not cand_nav.empty:
                    report.parity = self._parity.compare(
                        baseline=nav,
                        candidate=cand_nav,
                        baseline_label=f"backtest:{task_id[:8]}",
                        candidate_label=f"candidate:{candidate_task_id[:8]}",
                        baseline_turnover=self._get_df(dp, "order_count"),
                        candidate_turnover=self._get_df(cand_dp, "order_count"),
                    )
                else:
                    report.notes.append("candidate 无 net_value 链，G2 样本不足")
            except ValueError as e:
                report.notes.append(f"candidate 记录不可用: {e}")
        else:
            report.notes.append("未指定对比对象 (--candidate)，G2 未评估")

        for gate in gates_by_level("G2"):
            if report.parity is not None:
                passed = self._parity.evaluate_gate(report.parity, gate)
                status = PASS if passed else FAIL if passed is not None else INSUFFICIENT_DATA
                detail = self._parity_detail(report.parity, gate)
            else:
                passed, status, detail = None, INSUFFICIENT_DATA, "对比数据缺失"
            value = self._gate_value(report.parity, gate)
            parity_results.append(
                GateResult(gate=gate, status=status, value=value, detail=detail)
            )
        report.gates.extend(parity_results)

        # --- G3: kill switch 探针真判 (P1 落地后自动翻转), 其余持续跟踪类如实 BLOCKED ---
        from ginkgo.trading.analysis.evaluation.kill_switch_probe import (
            gate_detail as ks_detail,
            probe_kill_switch,
        )

        for gate in gates_by_level("G3"):
            if gate.id == "g3_kill_switch":
                cap = probe_kill_switch()
                report.gates.append(
                    GateResult(
                        gate=gate,
                        status=PASS if cap.ready else BLOCKED,
                        value=1.0 if cap.ready else 0.0,
                        detail=ks_detail(cap),
                    )
                )
                continue
            report.gates.append(
                GateResult(
                    gate=gate,
                    status=BLOCKED,
                    detail=f"依赖未就绪: {gate.requires}" if gate.requires else "持续跟踪数据未建立",
                )
            )

        report.level_reached = self._compute_level_reached(report)
        GLOG.INFO(
            f"FunnelEvaluator: portfolio={portfolio_id[:8]} task={task_id[:8]} "
            f"level_reached={report.level_reached}"
        )
        return report

    # ============================================================
    # 内部
    # ============================================================

    @staticmethod
    def _get_df(dp, name: str):
        df = dp.get(name)
        if df is not None and hasattr(df, "empty"):
            return df
        return None

    def _evaluate_g0_g1(self, dp, nav, stability_window: int) -> List[GateResult]:
        """G0 样本量 + G1 收益质量/平稳度"""
        results: List[GateResult] = []
        days = nav["timestamp"].dt.date.nunique() if hasattr(
            nav["timestamp"].dt, "date"
        ) else len(nav)

        # G0 样本跨度
        span_years = days / 252.0
        results.append(
            self._mk("g0_sample_span", span_years, f"{days} 个交易日")
        )

        # G0 成交笔数 (order_count 日频累计)
        oc = self._get_df(dp, "order_count")
        trades = float(oc["value"].sum()) if oc is not None and not oc.empty else None
        results.append(
            self._mk(
                "g0_trade_count",
                trades,
                f"order_count 链 {'缺失' if trades is None else f'合计 {trades:.0f}'}",
            )
        )

        # G1 Sharpe (取链末端值)
        sharpe = self._final_value(dp, "sharpe_ratio")
        results.append(self._mk("g1_sharpe_floor", sharpe, "sharpe_ratio 末端值"))

        # G1 最大回撤 (链末端, 负值)
        mdd = self._final_value(dp, "max_drawdown")
        results.append(self._mk("g1_mdd_tolerance", mdd, "max_drawdown 末端值"))

        # G1 滚动平稳度 (net_value 跨窗口 mean 序列综合分)
        stability = None
        try:
            rr = RollingReport(
                task_id="", data=dp, window=stability_window, step=stability_window,
                analyzers=["net_value"],
            )
            summary = rr.stability_summary().get("net_value")
            if summary:
                stability = float(summary.get("comprehensive_score"))
        except Exception as e:  # 平稳度失败不阻塞整体报告
            GLOG.WARNING(f"FunnelEvaluator: 平稳度计算失败: {e}")
        results.append(
            self._mk(
                "g1_rolling_stability",
                stability,
                f"net_value 滚动窗 (window={stability_window}) 综合平稳度",
            )
        )

        # G1 参数邻域: 依赖 optimize 接线 (四优化器未接入回测链, 邻域数据不可得)
        # 求值器已就位 (parameter_neighborhood.evaluate_neighborhood), 接线后即插即算;
        # 未接线如实 BLOCKED, 不假装通过 — 宁响亮
        results.append(
            GateResult(
                gate=get_gate("g1_param_neighborhood"),
                status=BLOCKED,
                detail="optimize 未接线: 邻域回测数据不可得 (依赖未就绪)",
            )
        )
        return results

    def _final_value(self, dp, name: str) -> Optional[float]:
        """取分析器链末端值"""
        df = self._get_df(dp, name)
        if df is None or df.empty:
            return None
        return float(df["value"].iloc[-1])

    def _mk(self, gate_id: str, value: Optional[float], detail: str) -> GateResult:
        """按定义求值单条 gate (通用: 有值比阈值, 无值样本不足)"""
        from ginkgo.trading.analysis.evaluation.gate_definitions import get_gate

        gate = get_gate(gate_id)
        if value is None or value != value:  # None or NaN
            return GateResult(gate=gate, status=INSUFFICIENT_DATA, detail=detail)
        passed = (
            value >= gate.threshold if gate.direction == "gte" else value <= gate.threshold
        )
        return GateResult(gate=gate, status=PASS if passed else FAIL, value=value, detail=detail)

    @staticmethod
    def _all_gates_status(status: str, detail: str) -> List[GateResult]:
        return [
            GateResult(gate=g, status=status, detail=detail) for g in gates_by_level_all()
        ]

    @staticmethod
    def _parity_detail(p: ParityResult, gate) -> str:
        if gate.id == "g2_cum_return_band":
            if p.band_ratio is None:
                return "带宽不可算"
            return f"累计差 {p.cum_return_diff:.4f} vs 带宽 {p.cum_return_band:.4f}"
        if gate.id == "g2_turnover_deviation":
            return "换手序列缺失" if p.turnover_deviation_pct is None else "order_count 同窗合计偏差"
        return f"重叠 {p.overlap_days} 天 ({p.overlap_start}~{p.overlap_end})"

    @staticmethod
    def _gate_value(p: Optional[ParityResult], gate) -> Optional[float]:
        if p is None:
            return None
        field_map = {
            "g2_overlap_days": p.overlap_days,
            "g2_daily_return_corr": p.daily_return_corr,
            "g2_cum_return_band": p.band_ratio,
            "g2_turnover_deviation": p.turnover_deviation_pct,
            "g2_drawdown_shape": p.drawdown_shape_corr,
        }
        v = field_map.get(gate.id)
        return float(v) if v is not None else None

    @staticmethod
    def _compute_level_reached(report: FunnelReport) -> str:
        """最高连续通过级: 该级全部 blocker gate PASS 才算过级"""
        reached = "未通过 G0"
        for level in LEVELS:
            gates = [g for g in report.gates if g.gate.level == level]
            blockers = [g for g in gates if g.gate.severity == "blocker"]
            if gates and all(g.status == PASS for g in blockers):
                reached = level
            else:
                break
        return reached


def gates_by_level_all():
    """全量 gate (供全 BLOCKED/INSUFFICIENT 报告)"""
    from ginkgo.trading.analysis.evaluation.gate_definitions import ALL_GATES

    return ALL_GATES
