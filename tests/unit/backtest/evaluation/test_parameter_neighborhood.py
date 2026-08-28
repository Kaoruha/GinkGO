# ParameterNeighborhood 纯计算测试 (G1 参数邻域衰减):
# - 邻域空/含 NaN → decay None (上游报样本不足, 不编数)
# - center <= 0 → 衰减分母无意义 → None
# - 正常求值: worst/median/衰减; gate 语义 PASS(≤阈值)/FAIL(参数尖峰)

import math

from ginkgo.trading.analysis.evaluation.parameter_neighborhood import (
    evaluate_neighborhood,
    gate_status,
)


def test_empty_neighbors_not_computable():
    r = evaluate_neighborhood(1.5, [])
    assert not r.computable
    assert r.decay is None and r.worst is None

    status, value, detail = gate_status(r, threshold=0.3)
    assert status == "INSUFFICIENT_DATA"
    assert value is None


def test_nan_neighbors_filtered():
    r = evaluate_neighborhood(1.5, [1.4, float("nan"), None, 1.2])
    assert r.computable
    assert r.worst == 1.2  # NaN/None 剔除, 剩两个有效点


def test_center_nonpositive_decay_undefined():
    # 中心 Sharpe <= 0: 策略本身已被 G1 其他 gate 拦, 衰减分母无意义
    for center in (0.0, -0.5, float("nan")):
        r = evaluate_neighborhood(center, [1.0, 0.5])
        assert not r.computable
        status, _, _ = gate_status(r, threshold=0.3)
        assert status == "INSUFFICIENT_DATA"


def test_decay_pass_flat_neighborhood():
    # 中心 2.0, 邻域最差 1.6 → 衰减 0.2 ≤ 0.3 → PASS (参数不敏感)
    r = evaluate_neighborhood(2.0, [1.9, 1.6, 2.1])
    assert math.isclose(r.decay, 0.2)
    assert r.worst == 1.6
    assert r.median == 1.9
    status, value, _ = gate_status(r, threshold=0.3)
    assert status == "PASS" and math.isclose(value, 0.2)


def test_decay_fail_param_spike():
    # 中心 3.0, 邻域最差 0.3 → 衰减 0.9 > 0.3 → FAIL (参数尖峰, 疑似过拟合)
    r = evaluate_neighborhood(3.0, [2.8, 0.3, 2.9])
    assert math.isclose(r.decay, 0.9)
    status, value, _ = gate_status(r, threshold=0.3)
    assert status == "FAIL" and math.isclose(value, 0.9)


def test_median_even_count():
    r = evaluate_neighborhood(2.0, [1.0, 1.2, 1.8, 2.2])
    assert r.median == 1.5  # 偶数个取中间均值


def test_neighbor_beats_center_no_negative_decay_issue():
    # 邻域全优于中心 (中心即最差): 衰解应为负 → 仍 PASS (比中心好不算衰减)
    r = evaluate_neighborhood(1.0, [1.5, 1.8])
    assert r.worst == 1.5
    assert r.decay < 0
    status, _, _ = gate_status(r, threshold=0.3)
    assert status == "PASS"
