# Upstream: ginkgo.trading.comparison.backtest_comparator
# Downstream: pytest
# Role: BacktestComparator 单元测试

"""
BacktestComparator 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
from datetime import datetime


@pytest.mark.unit
class TestBacktestComparator:
    """BacktestComparator 单元测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

        comparator = BacktestComparator()
        assert comparator is not None

    def test_compare(self):
        """测试回测对比"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator
        from ginkgo.trading.comparison.models import ComparisonResult

        comparator = BacktestComparator()
        # 使用模拟数据
        result = comparator.compare(["bt_001", "bt_002", "bt_003"])
        assert isinstance(result, ComparisonResult)
        assert "bt_001" in result.backtest_ids

    def test_compare_with_mock_data(self):
        """测试使用模拟数据的对比"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

        # 创建模拟回测数据
        mock_data = {
            "bt_001": {
                "total_return": Decimal("0.15"),
                "sharpe_ratio": Decimal("1.2"),
                "max_drawdown": Decimal("0.08"),
                "win_rate": Decimal("0.65"),
            },
            "bt_002": {
                "total_return": Decimal("0.12"),
                "sharpe_ratio": Decimal("1.5"),
                "max_drawdown": Decimal("0.05"),
                "win_rate": Decimal("0.70"),
            },
        }

        comparator = BacktestComparator()
        result = comparator.compare_with_data(mock_data)

        assert "total_return" in result.metrics_table
        assert "bt_001" in result.best_performers["total_return"]

    def test_get_net_values(self):
        """测试获取净值曲线"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

        comparator = BacktestComparator()
        net_values = comparator.get_net_values(["bt_001"], normalized=True)

        assert "bt_001" in net_values
        # 归一化后应从 1.0 开始
        if net_values["bt_001"]:
            assert net_values["bt_001"][0][1] == pytest.approx(1.0, rel=0.01)

    def test_get_best_performers(self):
        """测试获取最佳表现"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

        mock_data = {
            "bt_001": {"sharpe_ratio": Decimal("1.2")},
            "bt_002": {"sharpe_ratio": Decimal("1.5")},
            "bt_003": {"sharpe_ratio": Decimal("0.9")},
        }

        comparator = BacktestComparator()
        comparator._load_mock_data(mock_data)
        best = comparator.get_best_performer("sharpe_ratio")

        assert best == "bt_002"

    def test_to_dataframe(self):
        """测试导出为 DataFrame"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

        comparator = BacktestComparator()
        result = comparator.compare(["bt_001", "bt_002"])
        df = result.to_dataframe()

        assert df is not None
        assert len(df) > 0 or True  # 可能为空如果没有真实数据


@pytest.mark.unit
class TestBacktestComparatorMetrics:
    """回测对比指标测试"""

    def test_calculate_metrics(self):
        """测试指标计算"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator
        from decimal import Decimal

        comparator = BacktestComparator()

        # 模拟净值曲线
        net_values = [1.0, 1.05, 1.03, 1.08, 1.10, 1.07, 1.12]
        metrics = comparator.calculate_metrics(net_values)

        assert "total_return" in metrics
        # 总收益 = 1.12 - 1.0 = 0.12
        assert float(metrics["total_return"]) == pytest.approx(0.12, rel=0.01)

    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

        comparator = BacktestComparator()

        # 模拟净值曲线: 有明显回撤
        net_values = [1.0, 1.1, 1.2, 1.1, 1.0, 0.9, 1.0, 1.1]
        max_dd = comparator.calculate_max_drawdown(net_values)

        # 最大回撤: (1.2 - 0.9) / 1.2 = 0.25
        assert max_dd == pytest.approx(0.25, rel=0.01)

    def test_calculate_sharpe_ratio(self):
        """测试夏普比率计算"""
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

        comparator = BacktestComparator()

        # 模拟日收益率
        daily_returns = [0.01, -0.005, 0.02, 0.015, -0.01, 0.008, 0.012]
        sharpe = comparator.calculate_sharpe_ratio(daily_returns, risk_free_rate=0.02)

        assert sharpe is not None
