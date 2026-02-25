# Upstream: ginkgo.trading.paper.models
# Downstream: pytest
# Role: PaperTradingResult 测试

"""
PaperTradingResult 测试

TDD Red 阶段: 测试用例定义，预期失败
"""

import pytest
from decimal import Decimal


@pytest.mark.financial
class TestPaperTradingResult:
    """PaperTradingResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.trading.paper.models import PaperTradingResult

        result = PaperTradingResult(paper_id="p1", portfolio_id="pf1")
        assert result.paper_id == "p1"
        assert result.portfolio_id == "pf1"

    def test_difference_calculation(self):
        """测试差异计算"""
        from ginkgo.trading.paper.models import PaperTradingResult

        result = PaperTradingResult(
            paper_id="p1",
            portfolio_id="pf1",
            paper_return=Decimal("0.15"),
            backtest_return=Decimal("0.12"),
        )
        # difference = paper_return - backtest_return
        assert result.difference == Decimal("0.03")

    def test_is_acceptable_within_threshold(self):
        """测试可接受差异（在阈值内）"""
        from ginkgo.trading.paper.models import PaperTradingResult

        result = PaperTradingResult(
            paper_id="p1",
            portfolio_id="pf1",
            paper_return=Decimal("0.12"),
            backtest_return=Decimal("0.10"),
        )
        # difference_pct = 0.02 / 0.10 = 20% > 10%, not acceptable
        result.threshold = Decimal("0.10")  # 10% threshold
        assert result.is_acceptable == False

    def test_is_acceptable_exceeds_threshold(self):
        """测试不可接受差异（超出阈值）"""
        from ginkgo.trading.paper.models import PaperTradingResult

        result = PaperTradingResult(
            paper_id="p1",
            portfolio_id="pf1",
            paper_return=Decimal("0.105"),
            backtest_return=Decimal("0.10"),
        )
        result.threshold = Decimal("0.10")  # 10% threshold
        # difference_pct = 0.005 / 0.10 = 5% < 10%, acceptable
        assert result.is_acceptable == True

    def test_to_dict(self):
        """测试序列化为字典"""
        from ginkgo.trading.paper.models import PaperTradingResult

        result = PaperTradingResult(
            paper_id="p1",
            portfolio_id="pf1",
            paper_return=Decimal("0.15"),
            backtest_return=Decimal("0.12"),
        )
        d = result.to_dict()
        assert d["paper_id"] == "p1"
        assert "difference" in d

    def test_negative_backtest_return(self):
        """测试负回测收益"""
        from ginkgo.trading.paper.models import PaperTradingResult

        result = PaperTradingResult(
            paper_id="p1",
            portfolio_id="pf1",
            paper_return=Decimal("-0.05"),
            backtest_return=Decimal("-0.08"),
        )
        # Paper performed better (lost less)
        assert result.difference == Decimal("0.03")
