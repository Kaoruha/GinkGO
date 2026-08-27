# ParityCalculator 纯计算契约测试:
# - 同序列自反 → 相关性 1.0 全 PASS
# - 无重叠/短重叠 → 样本不足三态如实
# - 反相关 → FAIL
# - 换手缺失 → INSUFFICIENT_DATA 不猜值

import math

import pandas as pd

from ginkgo.trading.analysis.evaluation.gate_definitions import (
    ALL_GATES,
    gates_by_level,
    get_gate,
)
from ginkgo.trading.analysis.evaluation.parity_calculator import ParityCalculator


def _nav_df(values, start="2026-01-01"):
    dates = pd.bdate_range(start, periods=len(values))
    return pd.DataFrame({"timestamp": dates, "value": values})


def _trend(n, drift=0.001, start=1.0, wave=0.0, period=10):
    """趋势 + 正弦波动的净值序列 (wave>0 保证日收益/回撤有波动)"""
    out = []
    for i in range(n):
        v = start * math.pow(1 + drift, i)
        if wave:
            v *= 1.0 + wave * math.sin(2 * math.pi * i / period)
        out.append(v)
    return out


CALC = ParityCalculator()


def test_identical_series_full_pass():
    nav = _nav_df(_trend(60, wave=0.02))
    r = CALC.compare(nav, nav.copy(), baseline_turnover=_nav_df([1.0] * 60), candidate_turnover=_nav_df([1.0] * 60))
    assert r.overlap_days == 60
    assert r.daily_return_corr is not None and r.daily_return_corr > 0.999
    assert r.cum_return_diff is not None and r.cum_return_diff < 1e-9
    assert r.turnover_deviation_pct == 0.0
    # 全部 G2 gate PASS
    for gate in gates_by_level("G2"):
        assert CALC.evaluate_gate(r, gate) is True, gate.id


def test_no_overlap_insufficient():
    a = _nav_df(_trend(30), start="2025-01-01")
    b = _nav_df(_trend(30), start="2026-06-01")
    r = CALC.compare(a, b)
    assert r.overlap_days == 0
    assert r.daily_return_corr is None
    for gate in gates_by_level("G2"):
        assert CALC.evaluate_gate(r, gate) is None, gate.id  # INSUFFICIENT_DATA


def test_short_overlap_fails_days_gate_only():
    nav = _nav_df(_trend(60, wave=0.02))
    # 只取 10 天重叠
    other = pd.concat([_nav_df(_trend(10), start="2025-06-01"), nav.iloc[:10]]).sort_values("timestamp")
    r = CALC.compare(nav, other)
    assert r.overlap_days == 10
    days_gate = get_gate("g2_overlap_days")
    assert CALC.evaluate_gate(r, days_gate) is False  # FAIL: <20 天
    corr_gate = get_gate("g2_daily_return_corr")
    assert CALC.evaluate_gate(r, corr_gate) is True  # 指标本身仍可算且过


def test_anticorrelated_fails_corr():
    up = _nav_df(_trend(60, 0.002, wave=0.02))
    down = _nav_df(_trend(60, -0.002, wave=-0.02))
    r = CALC.compare(up, down)
    assert r.daily_return_corr is not None and r.daily_return_corr < 0
    assert CALC.evaluate_gate(r, get_gate("g2_daily_return_corr")) is False


def test_missing_turnover_reports_insufficient():
    nav = _nav_df(_trend(60, wave=0.02))
    r = CALC.compare(nav, nav.copy())  # 不传换手
    assert r.turnover_deviation_pct is None
    assert CALC.evaluate_gate(r, get_gate("g2_turnover_deviation")) is None
    assert any("换手" in n for n in r.notes)


def test_flat_series_notes_no_crash():
    flat = _nav_df([1.0] * 60)
    r = CALC.compare(flat, flat.copy())
    assert r.daily_return_corr is None  # 无波动 → 不可算
    assert r.notes  # 有说明而非静默


def test_gate_definitions_unique_ids():
    ids = [g.id for g in ALL_GATES]
    assert len(ids) == len(set(ids))
    assert {g.level for g in ALL_GATES} == {"G0", "G1", "G2", "G3"}
    assert get_gate("g2_daily_return_corr").threshold == 0.8
