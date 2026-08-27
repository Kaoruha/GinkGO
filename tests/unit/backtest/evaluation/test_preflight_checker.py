# PreflightChecker 纯计算契约测试:
# - 完美对齐 → 全 ok 无 issue
# - 单 code 中间断档 → 按缺口率分 warning/blocker 两档
# - 基准日历多数决: 2/3 codes 缺同一日 → 该日在基准 (缺失), 1/3 缺 → 该日不在基准
# - 复权因子: 单调不减 0 回跳 / 回跳>0 blocker / 记录缺失 None
# - 编排: 空 codes 放行 + notes; sparse blocker; ok 聚合
# - probe: 全异常 blocker / 部分异常 warning / 恒空 warning / 正常返回抽样按 code 预检
# - 底座: 空 blocker / 稀疏 warning(gate severity) / 充足仅画像 / loader 失败进 notes

from datetime import date

from ginkgo.trading.analysis.evaluation.preflight_checker import (
    GAP_BLOCKER_PCT,
    GAP_WARNING_PCT,
    PreflightChecker,
    evaluate_calendar_alignment,
    evaluate_factor_reversals,
)


def _dates(start, days, skip=()):
    """连续 days 个日历日, 跳过 skip 中的偏移量"""
    from datetime import timedelta
    return {start + timedelta(days=i) for i in range(days) if i not in skip}


D0 = date(2026, 1, 1)


# ---------- evaluate_calendar_alignment ----------

def test_perfect_alignment_all_ok():
    series = {c: _dates(D0, 60) for c in ("000001.SZ", "000002.SZ", "600000.SH")}
    r = evaluate_calendar_alignment(series)
    assert all(q["severity"] == "ok" for q in r.values())
    assert all(q["gap_pct"] == 0.0 for q in r.values())


def test_mid_gap_graded_by_pct():
    # 60 日基准 (span 剔除首末=58): 各 code 缺「不同」区间 — 缺口区间重叠会在多数决下
    # 被踢出基准 (全市场同步缺失不算缺口), 故 000002 缺 10 日(17.2%→warning),
    # 600000 缺另一段 15 日(25.9%→blocker)
    base = _dates(D0, 60)
    series = {
        "000001.SZ": base,
        "000002.SZ": base - set(sorted(base)[25:35]),   # 10 日
        "600000.SH": base - set(sorted(base)[5:20]),     # 15 日
    }
    r = evaluate_calendar_alignment(series)
    assert r["000002.SZ"]["severity"] == "warning"
    assert r["600000.SH"]["severity"] == "blocker"
    assert 0 < r["000002.SZ"]["gap_pct"] <= GAP_BLOCKER_PCT
    assert r["600000.SH"]["gap_pct"] > GAP_BLOCKER_PCT


def test_calendar_majority_vote():
    # 3 codes: 只有 1 个缺某日 → 出现率 2/3 ≥ 半数, 该日在基准; 反过来 1 个独有日不在基准
    common = _dates(D0, 40)
    series = {
        "000001.SZ": common,
        "000002.SZ": common,
        "600000.SH": common - {sorted(common)[20]} | {date(2026, 3, 31)},
    }
    r = evaluate_calendar_alignment(series)
    # 600000 缺的那天: 基准含它 (2/3 出现) → 记 1 个缺失; 但独有日不入基准 → 不计缺口
    assert r["600000.SH"]["missing_days"] == 1
    assert r["600000.SH"]["severity"] in ("ok", "warning")  # 1/38 极小


def test_head_missing_not_counted_as_gap():
    # code 数据从第 20 日才开始 (头部缺失=未上市/未同步, 不算断档)
    base = _dates(D0, 60)
    series = {"000001.SZ": base, "000002.SZ": set(sorted(base)[20:])}
    r = evaluate_calendar_alignment(series)
    assert r["000002.SZ"]["gap_pct"] == 0.0
    assert r["000002.SZ"]["head_missing_days"] == 20


def test_empty_series_blocked():
    r = evaluate_calendar_alignment({"000001.SZ": set(), "000002.SZ": set()})
    assert all(q["severity"] == "blocker" for q in r.values())


# ---------- evaluate_factor_reversals ----------

def test_monotonic_factors_zero_reversals():
    facs = [(date(2026, 1, i + 1), v) for i, v in enumerate((1.0, 1.0, 1.2, 1.2, 1.5))]
    assert evaluate_factor_reversals(facs) == 0


def test_factor_reversal_counted():
    facs = [(date(2026, 1, i + 1), v) for i, v in enumerate((1.0, 1.2, 1.1, 1.5, 1.4))]
    assert evaluate_factor_reversals(facs) == 2


def test_factor_series_too_short_is_none():
    assert evaluate_factor_reversals([(date(2026, 1, 1), 1.0)]) is None
    assert evaluate_factor_reversals([]) is None


# ---------- PreflightChecker 编排 (stub 取数) ----------

class _Bar:
    def __init__(self, ts):
        self.timestamp = ts


def _checker(bars_by_code, factors_by_code=None, with_factors=True, selector=None, daily_counts=None):
    bar_crud = _BarCrud(bars_by_code)
    loader = None
    if with_factors:
        loader = lambda code, s, e: factors_by_code.get(code, [])
    counts_loader = (lambda s, e: daily_counts) if daily_counts is not None else None
    return PreflightChecker(
        bar_crud=bar_crud, factor_loader=loader,
        selector=selector, daily_counts_loader=counts_loader,
    )


class _BarCrud:
    def __init__(self, bars_by_code):
        self._bars = bars_by_code

    def find_by_code_and_date_range(self, code, start, end):
        return self._bars.get(code, [])


def test_checker_empty_codes_pass():
    r = _checker({}).check("p" * 32, [], "2026-01-01", "2026-06-30")
    assert r.ok and r.notes and "动态 selector" in r.notes[0]


def test_checker_sparse_blocker():
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in ("000001.SZ",)}
    # 覆盖充足 (60>10) 但另一 code 只有 3 条 → sparse blocker
    bars["000002.SZ"] = [_Bar(d) for d in sorted(_dates(D0, 60))[:3]]
    r = _checker(bars, with_factors=False).check("p" * 32, list(bars), D0, date(2026, 3, 1))
    kinds = {(i.code, i.kind, i.severity) for i in r.issues}
    assert ("000002.SZ", "sparse", "blocker") in kinds
    assert not r.ok


def test_checker_factor_reversal_blocker():
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}
    facs = {"000001.SZ": [(date(2026, 1, i + 1), v) for i, v in enumerate((1.0, 1.2, 1.1))]}
    r = _checker(bars, facs).check("p" * 32, list(codes), D0, date(2026, 3, 1))
    kinds = {(i.code, i.kind, i.severity) for i in r.issues}
    assert ("000001.SZ", "factor_reversal", "blocker") in kinds
    assert not r.ok


def test_checker_factor_missing_warning():
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}
    r = _checker(bars, {}).check("p" * 32, list(codes), D0, date(2026, 3, 1))
    kinds = {(i.code, i.kind) for i in r.issues}
    assert ("000001.SZ", "factor_missing") in kinds
    assert r.quality["000001.SZ"]["factor_reversals"] is None
    assert any(i.severity == "warning" for i in r.issues) and r.ok


def test_checker_clean_all_pass():
    codes = ("000001.SZ", "000002.SZ")
    days = sorted(_dates(D0, 60))
    bars = {c: [_Bar(d) for d in days] for c in codes}
    facs = {c: [(days[0], 1.0), (days[-1], 1.0)] for c in codes}
    r = _checker(bars, facs).check("p" * 32, list(codes), D0, date(2026, 3, 1))
    assert r.ok and not r.issues
    assert r.coverage == {c: 60 for c in codes}


def test_to_dict_serializable():
    import json
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}
    r = _checker(bars, with_factors=False).check("p" * 32, list(codes), D0, date(2026, 3, 1))
    payload = json.dumps(r.to_dict(), default=str)
    assert "coverage" in payload and "issues" in payload


# ---------- 动态 selector probe (codes 空 + selector 注入) ----------

class _BoomSelector:
    def pick(self, t):
        raise RuntimeError("no data")


class _EmptySelector:
    def pick(self, t):
        return []


class _DynSelector:
    """恒定返回固定池 (模拟窗口内稳定选股)"""

    def __init__(self, codes):
        self._codes = codes

    def pick(self, t):
        return list(self._codes)


class _FlakySelector:
    """首个采样点异常, 其余正常 → 部分异常 warning"""

    def __init__(self, codes):
        self._codes = codes
        self.n = 0

    def pick(self, t):
        self.n += 1
        if self.n == 1:
            raise RuntimeError("flaky")
        return list(self._codes)


def test_probe_all_points_error_blocker():
    r = _checker({}, with_factors=False, selector=_BoomSelector()).check(
        "p" * 32, [], "2026-01-01", "2026-06-30"
    )
    kinds = {(i.code, i.kind, i.severity) for i in r.issues}
    assert ("(selector)", "selector_error", "blocker") in kinds
    assert not r.ok
    assert r.codes == []  # 空池提前返回, 不再按 code 预检


def test_probe_partial_error_warning():
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}
    r = _checker(bars, with_factors=False, selector=_FlakySelector(list(codes))).check(
        "p" * 32, [], D0, date(2026, 3, 1)
    )
    kinds = {(i.code, i.kind, i.severity) for i in r.issues}
    assert ("(selector)", "selector_error", "warning") in kinds
    assert r.ok  # warning 不挡; 其余时点可用 → 抽样照走按 code 预检
    assert r.coverage.get("000001.SZ") == 60


def test_probe_always_empty_warning():
    r = _checker({}, with_factors=False, selector=_EmptySelector()).check(
        "p" * 32, [], "2026-01-01", "2026-06-30"
    )
    kinds = {(i.code, i.kind, i.severity) for i in r.issues}
    assert ("(selector)", "selector_empty", "warning") in kinds
    assert r.ok and r.codes == []


def test_probe_samples_codes_for_per_code_check():
    pool = [f"{i:06d}.SZ" for i in range(1, 11)]  # 10 只, 抽样上限 5
    days = sorted(_dates(D0, 60))
    bars = {c: [_Bar(d) for d in days] for c in pool}
    r = _checker(bars, with_factors=False, selector=_DynSelector(pool)).check(
        "p" * 32, [], D0, date(2026, 3, 1)
    )
    assert 0 < len(r.codes) <= 5  # PROBE_SAMPLE_CODES
    assert set(r.codes) <= set(pool)
    assert r.ok and not r.issues
    import re
    # 三采样点记录 (带日期) + 一条「probe 去重」汇总
    assert len([n for n in r.notes if re.match(r"probe \d{4}-", n)]) == 3
    assert any("去重" in n for n in r.notes)
    assert all(r.coverage.get(c) == 60 for c in r.codes)


# ---------- 数据底座密度 (selector 无关) ----------

def test_universe_empty_blocker():
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}
    r = _checker(bars, with_factors=False, daily_counts={}).check(
        "p" * 32, list(codes), D0, date(2026, 3, 1)
    )
    kinds = {(i.code, i.kind, i.severity) for i in r.issues}
    assert ("(universe)", "universe_empty", "blocker") in kinds
    assert not r.ok


def test_universe_sparse_warning():
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}
    daily = {f"2026-01-{d:02d}": 100 for d in range(1, 29)}  # 日均 100 < 1000
    r = _checker(bars, with_factors=False, daily_counts=daily).check(
        "p" * 32, list(codes), D0, date(2026, 3, 1)
    )
    kinds = {(i.code, i.kind, i.severity) for i in r.issues}
    assert ("(universe)", "universe_sparse", "warning") in kinds  # gate severity
    assert r.ok  # warning 不挡
    assert r.quality["(universe)"]["daily_code_counts"] == {"avg": 100.0, "min": 100, "days": 28}


def test_universe_dense_only_profile():
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}
    daily = {"2026-01-01": 5386, "2026-01-02": 5000}  # 日均 > 1000 → 无 issue 只画像
    r = _checker(bars, with_factors=False, daily_counts=daily).check(
        "p" * 32, list(codes), D0, date(2026, 3, 1)
    )
    assert r.ok and not r.issues
    assert r.quality["(universe)"]["daily_code_counts"]["days"] == 2


def test_universe_loader_failure_noted():
    codes = ("000001.SZ",)
    bars = {c: [_Bar(d) for d in sorted(_dates(D0, 60))] for c in codes}

    def boom(s, e):
        raise RuntimeError("ch down")

    r = PreflightChecker(bar_crud=_BarCrud(bars), daily_counts_loader=boom).check(
        "p" * 32, list(codes), D0, date(2026, 3, 1)
    )
    assert any("底座画像加载失败" in n for n in r.notes)
    assert r.ok  # 画像失败不挡 (按 code 预检照常)
