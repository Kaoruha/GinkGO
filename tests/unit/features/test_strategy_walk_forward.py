"""策略走步 OOS 验证测试 -- #6796 验收2 (接入走步) + 验收4 (如实报告 OOS)

backtest_func 是调用方注入的 callable (跑策略回测返回 {"return": float}),
此处 mock 固定收益序列验证切折 + OOS 报告 + 如实反映逻辑。
"""
import pytest

try:
    from ginkgo.features.services.strategy_walk_forward import (
        walk_forward_strategy_evaluation,
    )
    HAS_WF = True
except ImportError:
    HAS_WF = False


@pytest.mark.skipif(not HAS_WF, reason="walk_forward_strategy_evaluation not available")
@pytest.mark.unit
class TestStrategyWalkForward:
    def test_produces_folds_with_oos_report(self):
        """验收2: 走步切 n_folds 折, 每折 train/test, 报告 OOS mean。"""
        def bt(params, start, end):
            return {"return": 0.1}  # train/test 都正
        r = walk_forward_strategy_evaluation(
            bt, "2023-01-01", "2024-01-01", n_folds=3)
        assert r.success
        assert len(r.data["folds"]) == 3
        for f in r.data["folds"]:
            assert f["train_return"] == 0.1
            assert f["test_return"] == 0.1
        assert r.data["mean_test_return"] > 0
        assert r.data["effective"] is True

    def test_reports_ineffective_when_oos_nonpositive(self):
        """验收4: OOS <= 0 → effective=False (如实报告, 不强行声称有效)。"""
        def bt(params, start, end):
            return {"return": -0.02}  # OOS 负
        r = walk_forward_strategy_evaluation(
            bt, "2023-01-01", "2024-01-01", n_folds=3)
        assert r.success
        assert r.data["mean_test_return"] < 0
        assert r.data["effective"] is False  # 如实: 无效就说无效

    def test_degradation_is_train_minus_test(self):
        """degradation = mean_train - mean_test (train 好 test 差 → 正退化)。"""
        state = {"call": 0}
        def bt(params, start, end):
            # 交替: 奇数 call=train(高 0.20), 偶数 call=test(低 0.01)
            state["call"] += 1
            return {"return": 0.20 if state["call"] % 2 == 1 else 0.01}
        r = walk_forward_strategy_evaluation(
            bt, "2023-01-01", "2024-01-01", n_folds=3)
        assert r.success
        assert r.data["degradation"] is not None
        # train(0.20) - test(0.01) = 0.19 > 0 (显著退化)
        assert r.data["degradation"] > 0
