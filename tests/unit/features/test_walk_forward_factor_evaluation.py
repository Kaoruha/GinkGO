"""walk_forward_factor_evaluation 测试 -- #6793 验收3 (走步验证接入)

防样本内拟合: 滑动 train/test 折, 每折 PIT 读取因子, 输出样本外折结果。
(与 memory project_profit_strategy_iter037 OOS 证伪教训对齐: 禁全样本拟合)

evaluator 注入: 具体指标 (IC/IR/decay) 由调用方提供 (#6794 提供 IC evaluator)。
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

try:
    from ginkgo.features.services.factor_service import FactorService
    HAS_SVC = True
except ImportError:
    HAS_SVC = False


@pytest.mark.skipif(not HAS_SVC, reason="FactorService not available")
class TestWalkForwardFactorEvaluation:
    @pytest.fixture
    def factor_service(self):
        return FactorService(MagicMock(), MagicMock())

    def test_produces_folds_with_train_test_split(self, factor_service):
        """走步: 输出 n_folds 折, 每折 train_score + test_score 分离 (非全样本单一值)。"""
        crud = MagicMock()
        crud.get_factors_by_entity.return_value = [MagicMock()]

        result = factor_service.walk_forward_factor_evaluation(
            factor_name="ROC", entity_ids=["000001.SZ"],
            start_date="2024-01-01", end_date="2024-12-31",
            evaluator=lambda factors: len(factors),
            n_folds=3, factor_crud=crud,
        )

        assert result.success
        folds = result.data["folds"]
        assert len(folds) == 3
        for f in folds:
            assert "train_score" in f and "test_score" in f
            # train 时序在 test 前 (无重叠, 防泄漏)
            assert f["train_end"] < f["test_start"]

    def test_pit_each_fold_queries_bounded_window(self, factor_service):
        """PIT: 每折 crud 查询的 [start_time, end_time] 有界, start <= end (不读窗口外未来)。"""
        crud = MagicMock()
        crud.get_factors_by_entity.return_value = []

        factor_service.walk_forward_factor_evaluation(
            factor_name="ROC", entity_ids=["000001.SZ"],
            start_date="2024-01-01", end_date="2024-03-31",
            evaluator=lambda f: 0.0, n_folds=2, factor_crud=crud,
        )

        calls = crud.get_factors_by_entity.call_args_list
        # 每折 2 查询 (train + test) × 2 折 × 1 entity = 4
        assert len(calls) == 4
        for c in calls:
            kw = c[1]
            assert "start_time" in kw and "end_time" in kw
            assert kw["start_time"] <= kw["end_time"]
            # 全部查询窗口不超评估终点 (PIT: 评估日 end_date 前的数据)
            assert kw["end_time"] <= datetime(2024, 3, 31)

    def test_outputs_degradation_and_oos_split(self, factor_service):
        """输出含 degradation + mean_train/test_score (样本外折对比, 检测过拟合)。"""
        crud = MagicMock()
        crud.get_factors_by_entity.return_value = [MagicMock()]

        result = factor_service.walk_forward_factor_evaluation(
            factor_name="ROC", entity_ids=["000001.SZ"],
            start_date="2024-01-01", end_date="2024-06-30",
            evaluator=lambda f: len(f), n_folds=2, factor_crud=crud,
        )

        assert result.success
        assert "degradation" in result.data
        assert "mean_train_score" in result.data
        assert "mean_test_score" in result.data
        assert result.data["n_folds"] == 2
