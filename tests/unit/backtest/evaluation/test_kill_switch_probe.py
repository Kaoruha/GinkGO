# KillSwitchProbe 测试 (G3 联动求值):
# - 现状探测: livecore P1 未落地 → 四件套全缺 → BLOCKED + detail 列缺口
# - 能力翻转: 四件套补齐 (mock 探测目标) → ready → PASS (联动显示, P1 落地自动翻转)
# - detail 文案: 就位列全件, 未位列缺口

from unittest.mock import patch

from ginkgo.trading.analysis.evaluation import kill_switch_probe as ksp


def test_current_state_all_missing():
    # 真实探测当前代码库: emergency_stop_all 只停连, 四件套方法均不存在
    cap = ksp.probe_kill_switch()
    assert not cap.ready
    assert not (cap.flatten or cap.cancel_all or cap.daily_loss_breaker or cap.manual_trigger)
    detail = ksp.gate_detail(cap)
    assert detail.startswith("未就位:")
    for kw in ("flatten", "cancel-all", "日损熔断", "手动开关"):
        assert kw in detail


def test_capability_flip_to_ready():
    # P1 落地: 探测目标补齐四件套方法 → ready 翻转, detail 变成就位文案
    class FakeLive:
        flatten_all = True
        cancel_all_orders = True
        daily_loss_breaker = True
        kill_switch = True

    with patch.object(ksp, "_PROBE_TARGETS", (("fake.mod", "Fake"),)), \
         patch.object(ksp, "_import_target", return_value=FakeLive):
        cap = ksp.probe_kill_switch()

    assert cap.ready
    assert cap.gaps == []
    assert "全部就位" in ksp.gate_detail(cap)


def test_partial_capability_lists_only_gaps():
    # 只补 flatten → 仍不 ready, gaps 只列缺的三件
    class FakePartial:
        flatten_positions = True

    with patch.object(ksp, "_PROBE_TARGETS", (("fake.mod", "F"),)), \
         patch.object(ksp, "_import_target", return_value=FakePartial):
        cap = ksp.probe_kill_switch()

    assert not cap.ready
    assert len(cap.gaps) == 3
    assert not any("flatten" in g for g in cap.gaps)


def test_no_targets_importable_all_missing():
    # 探测目标全不可导入 (模块缺失) → 四件套全 False, 不崩
    with patch.object(ksp, "_PROBE_TARGETS", (("no.such.module", "X"),)):
        cap = ksp.probe_kill_switch()
    assert not cap.ready


def test_funnel_g3_kill_switch_uses_probe():
    # 集成: funnel G3 kill_switch gate 用探针真判 (当前必 BLOCKED, value=0)
    from ginkgo.trading.analysis.evaluation.funnel_evaluator import BLOCKED, FunnelEvaluator
    from tests.unit.backtest.evaluation.test_funnel_evaluator import _dp, _nav, _evaluator

    fe = _evaluator(_dp(_nav()))
    r = fe.evaluate("p" * 32, "t" * 32)
    ks = [g for g in r.gates if g.gate.id == "g3_kill_switch"][0]
    assert ks.status == BLOCKED
    assert ks.value == 0.0
    assert "未就位" in ks.detail
