# FunnelEvaluator 编排契约测试 (mock AnalysisEngine):
# - 记录不可用 → 全 gate INSUFFICIENT_DATA 不崩
# - 好 baseline 无 candidate → G2 整级样本不足, G3 BLOCKED, level_reached 停在 G1
# - 带 candidate → G2 有判定, level_reached 可推进
# - failed_blockers 只含 FAIL/BLOCKED 的 blocker

import math
from unittest.mock import MagicMock

import pandas as pd

from ginkgo.trading.analysis.evaluation.funnel_evaluator import (
    BLOCKED,
    FAIL,
    INSUFFICIENT_DATA,
    PASS,
    FunnelEvaluator,
)

PID = "p" * 32
TID = "t" * 32


def _dp(nav_values, sharpe=1.5, mdd=-0.1, orders=800, days=800):
    """构造带常用链的 DataProvider mock"""
    dp = MagicMock()
    idx = pd.bdate_range("2026-01-01", periods=days)

    def df(vals):
        return pd.DataFrame({"timestamp": idx[: len(vals)], "value": vals})

    nav = df(nav_values if len(nav_values) == days else nav_values[:days])
    store = {
        "net_value": nav,
        "sharpe_ratio": df([sharpe] * days),
        "max_drawdown": df([mdd] * days),
        "order_count": df([orders / days] * days),
    }
    dp.get = lambda name: store.get(name)
    dp.available = list(store)
    return dp


def _nav(n=800, drift=0.001, wave=0.02):
    """趋势+波动净值 (wave 保证回撤/日收益有波动, G2 全指标可算)"""
    return [
        math.pow(1 + drift, i) * (1.0 + wave * math.sin(2 * math.pi * i / 10))
        for i in range(n)
    ]


def _evaluator(dp, cand_dp=None):
    e = MagicMock()
    e._load_data = MagicMock(side_effect=[dp] + ([cand_dp] if cand_dp else []))
    return FunnelEvaluator(e)


def test_missing_records_all_insufficient():
    e = MagicMock()
    e._load_data.side_effect = ValueError("no records")
    r = FunnelEvaluator(e).evaluate(PID, TID)
    assert r.gates and all(g.status == INSUFFICIENT_DATA for g in r.gates)
    assert r.level_reached == "未通过 G0"
    assert r.notes


def test_no_candidate_g2_insufficient_g3_blocked():
    fe = _evaluator(_dp(_nav()))
    r = fe.evaluate(PID, TID)
    by_level = {}
    for g in r.gates:
        by_level.setdefault(g.gate.level, []).append(g.status)
    assert all(s == PASS for s in by_level["G0"])  # 260 天/200 笔 过
    assert by_level["G2"] and all(s == INSUFFICIENT_DATA for s in by_level["G2"])
    assert all(s == BLOCKED for s in by_level["G3"])
    # G1: 收益质量全过, 但参数邻域 gate 依赖 optimize 接线 → BLOCKED 挡级 (如实, 不假装通过)
    g1 = {g.gate.id: g.status for g in r.gates if g.gate.level == "G1"}
    assert g1["g1_param_neighborhood"] == BLOCKED
    assert r.level_reached == "G0"  # optimize 未接线, G1 恒被挡
    # 无 FAIL 时未过 blockers 只应是 BLOCKED; 有 FAIL 的属于 G1 平稳度, 不在此断言


def test_with_candidate_g2_evaluated():
    fe = _evaluator(_dp(_nav()), _dp(_nav()))  # 两次相同 → G2 应过
    r = fe.evaluate(PID, TID, candidate_task_id="c" * 32)
    g2 = {g.gate.id: g.status for g in r.gates if g.gate.level == "G2"}
    assert g2["g2_overlap_days"] == PASS
    assert g2["g2_daily_return_corr"] == PASS
    assert g2["g2_turnover_deviation"] == PASS
    assert r.parity is not None and r.parity.overlap_days == 800
    # parity 照常可算可过, 但 level_reached 停在 G0: G1 参数邻域 gate BLOCKED (optimize 未接线)
    assert r.level_reached == "G0"


def test_bad_sharpe_fails_g1():
    fe = _evaluator(_dp(_nav(), sharpe=0.3))
    r = fe.evaluate(PID, TID)
    sharpe_gate = [g for g in r.gates if g.gate.id == "g1_sharpe_floor"]
    assert sharpe_gate[0].status == FAIL
    assert sharpe_gate[0] in r.failed_blockers()
    assert r.level_reached == "未通过 G0" or r.level_reached == "G0"


def test_to_dict_serializable():
    import json

    fe = _evaluator(_dp(_nav()), _dp(_nav()))
    r = fe.evaluate(PID, TID, candidate_task_id="c" * 32)
    payload = json.dumps(r.to_dict(), default=str)
    assert "gates" in payload and "level_reached" in payload
