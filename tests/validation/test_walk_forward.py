# Upstream: ginkgo.validation.walk_forward
# Downstream: pytest
# Role: WalkForwardValidator 测试

"""
WalkForwardValidator 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_date_range():
    """创建示例日期范围"""
    start = datetime(2023, 1, 1)
    end = datetime(2023, 12, 31)
    return start, end


@pytest.fixture
def sample_data():
    """创建示例回测数据"""
    dates = pd.date_range("2023-01-01", periods=365, freq="D")
    data = pd.DataFrame({
        "date": dates,
        "value": np.random.randn(365).cumsum() + 100,
    })
    return data


@pytest.mark.unit
class TestWalkForwardFold:
    """WalkForwardFold 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.validation.models import WalkForwardFold

        fold = WalkForwardFold(
            fold_num=1,
            train_start="2023-01-01",
            train_end="2023-06-30",
            test_start="2023-07-01",
            test_end="2023-12-31",
        )

        assert fold.fold_num == 1
        assert fold.train_start == "2023-01-01"
        assert fold.test_end == "2023-12-31"

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.validation.models import WalkForwardFold

        fold = WalkForwardFold(
            fold_num=1,
            train_start="2023-01-01",
            train_end="2023-06-30",
            test_start="2023-07-01",
            test_end="2023-12-31",
        )

        d = fold.to_dict()
        assert d["fold_num"] == 1
        assert "train_start" in d


@pytest.mark.unit
class TestWalkForwardResult:
    """WalkForwardResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.validation.models import WalkForwardResult

        result = WalkForwardResult(n_folds=5)

        assert result.n_folds == 5
        assert result.folds == []

    def test_add_fold_result(self):
        """测试添加折结果"""
        from ginkgo.validation.models import WalkForwardResult, WalkForwardFold

        result = WalkForwardResult(n_folds=3)

        fold = WalkForwardFold(
            fold_num=1,
            train_start="2023-01-01",
            train_end="2023-04-30",
            test_start="2023-05-01",
            test_end="2023-08-31",
        )
        fold.train_score = 0.85
        fold.test_score = 0.75

        result.add_fold_result(fold)

        assert len(result.folds) == 1
        assert result.mean_train_score == 0.85
        assert result.mean_test_score == 0.75

    def test_calculate_degradation(self):
        """测试计算退化程度"""
        from ginkgo.validation.models import WalkForwardResult, WalkForwardFold

        result = WalkForwardResult(n_folds=2)

        # 第一折
        fold1 = WalkForwardFold(
            fold_num=1,
            train_start="2023-01-01",
            train_end="2023-04-30",
            test_start="2023-05-01",
            test_end="2023-08-31",
        )
        fold1.train_score = 0.90
        fold1.test_score = 0.72

        # 第二折
        fold2 = WalkForwardFold(
            fold_num=2,
            train_start="2023-05-01",
            train_end="2023-08-31",
            test_start="2023-09-01",
            test_end="2023-12-31",
        )
        fold2.train_score = 0.88
        fold2.test_score = 0.70

        result.add_fold_result(fold1)
        result.add_fold_result(fold2)

        # 退化程度 = (train_score - test_score) / train_score
        # 平均退化 = (0.89 - 0.71) / 0.89 ≈ 0.20
        degradation = result.calculate_degradation()
        assert 0.15 < degradation < 0.25

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.validation.models import WalkForwardResult, WalkForwardFold

        result = WalkForwardResult(n_folds=1)

        fold = WalkForwardFold(
            fold_num=1,
            train_start="2023-01-01",
            train_end="2023-06-30",
            test_start="2023-07-01",
            test_end="2023-12-31",
        )
        fold.train_score = 0.85
        fold.test_score = 0.75
        result.add_fold_result(fold)

        d = result.to_dict()
        assert d["n_folds"] == 1
        assert "degradation" in d


@pytest.mark.unit
class TestWalkForwardValidator:
    """WalkForwardValidator 测试"""

    def test_init(self, sample_date_range):
        """测试初始化"""
        from ginkgo.validation.walk_forward import WalkForwardValidator

        start, end = sample_date_range
        validator = WalkForwardValidator(
            start_date=start,
            end_date=end,
            n_folds=5,
        )

        assert validator is not None
        assert validator.n_folds == 5

    def test_generate_folds(self, sample_date_range):
        """测试生成折"""
        from ginkgo.validation.walk_forward import WalkForwardValidator

        start, end = sample_date_range
        validator = WalkForwardValidator(
            start_date=start,
            end_date=end,
            n_folds=5,
            train_ratio=0.7,
        )

        folds = validator.generate_folds()

        assert len(folds) == 5
        # 第一折应该从开始日期附近开始
        assert folds[0].fold_num == 1

    def test_generate_folds_rolling(self, sample_date_range):
        """测试滚动窗口生成"""
        from ginkgo.validation.walk_forward import WalkForwardValidator

        start, end = sample_date_range
        validator = WalkForwardValidator(
            start_date=start,
            end_date=end,
            n_folds=5,
            expanding=False,  # 滚动窗口
        )

        folds = validator.generate_folds()

        # 滚动窗口：训练期长度应该相同
        assert len(folds) == 5

    def test_validate(self, sample_date_range, sample_data):
        """测试验证运行"""
        from ginkgo.validation.walk_forward import WalkForwardValidator

        start, end = sample_date_range

        # 模拟回测函数
        def mock_backtest(params, train_start, train_end):
            return {"score": 0.85 + np.random.randn() * 0.05}

        def mock_test(params, test_start, test_end):
            return {"score": 0.75 + np.random.randn() * 0.1}

        validator = WalkForwardValidator(
            start_date=start,
            end_date=end,
            n_folds=3,
        )
        validator.set_backtest_function(mock_backtest)
        validator.set_test_function(mock_test)

        result = validator.validate(params={})

        assert result is not None
        assert len(result.folds) == 3

    def test_get_summary(self, sample_date_range):
        """测试获取摘要"""
        from ginkgo.validation.walk_forward import WalkForwardValidator

        start, end = sample_date_range
        validator = WalkForwardValidator(
            start_date=start,
            end_date=end,
            n_folds=5,
        )
        validator.generate_folds()

        summary = validator.get_summary()

        assert "n_folds" in summary
        assert summary["n_folds"] == 5

    def test_custom_fold_size(self, sample_date_range):
        """测试自定义折大小"""
        from ginkgo.validation.walk_forward import WalkForwardValidator

        start, end = sample_date_range
        validator = WalkForwardValidator(
            start_date=start,
            end_date=end,
            n_folds=3,
            train_ratio=0.6,
        )

        folds = validator.generate_folds()

        # 验证训练期占 60%
        assert len(folds) == 3
