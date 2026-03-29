# Upstream: ginkgo.trading.comparison.models
# Downstream: pytest
# Role: ComparisonResult 测试

"""
ComparisonResult 测试
"""

import pytest
from decimal import Decimal


@pytest.mark.unit
class TestComparisonResult:
    """ComparisonResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.trading.comparison.models import ComparisonResult

        result = ComparisonResult(comparison_id="c1", backtest_ids=["bt1", "bt2"])
        assert result.comparison_id == "c1"
        assert result.backtest_ids == ["bt1", "bt2"]

    def test_metrics_table(self):
        """测试指标表格"""
        from ginkgo.trading.comparison.models import ComparisonResult

        result = ComparisonResult(
            comparison_id="c1",
            backtest_ids=["bt1", "bt2"],
            metrics_table={
                "total_return": {"bt1": Decimal("0.15"), "bt2": Decimal("0.12")},
                "sharpe_ratio": {"bt1": Decimal("1.2"), "bt2": Decimal("1.5")},
            },
        )

        assert "total_return" in result.metrics_table
        assert result.metrics_table["total_return"]["bt1"] == Decimal("0.15")

    def test_best_performers(self):
        """测试最佳表现"""
        from ginkgo.trading.comparison.models import ComparisonResult

        result = ComparisonResult(
            comparison_id="c1",
            backtest_ids=["bt1", "bt2"],
            best_performers={
                "total_return": "bt1",
                "sharpe_ratio": "bt2",
            },
        )

        assert result.best_performers["total_return"] == "bt1"
        assert result.best_performers["sharpe_ratio"] == "bt2"

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.trading.comparison.models import ComparisonResult

        result = ComparisonResult(
            comparison_id="c1",
            backtest_ids=["bt1", "bt2"],
            metrics_table={"return": {"bt1": Decimal("0.15")}},
        )
        d = result.to_dict()

        assert d["comparison_id"] == "c1"
        assert "metrics_table" in d

    def test_get_ranking(self):
        """测试排名获取"""
        from ginkgo.trading.comparison.models import ComparisonResult

        result = ComparisonResult(
            comparison_id="c1",
            backtest_ids=["bt1", "bt2", "bt3"],
            metrics_table={
                "total_return": {
                    "bt1": Decimal("0.15"),
                    "bt2": Decimal("0.20"),
                    "bt3": Decimal("0.10"),
                }
            },
        )

        ranking = result.get_ranking("total_return")
        assert ranking[0] == "bt2"  # 最高收益
        assert ranking[1] == "bt1"
        assert ranking[2] == "bt3"
