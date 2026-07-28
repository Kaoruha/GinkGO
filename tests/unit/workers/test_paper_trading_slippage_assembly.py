# Upstream: ginkgo.workers.paper_trading_worker, ginkgo.data.models.model_portfolio
# Downstream: -
# Role: 模拟盘 assemble_engine slippage 注入测试 (Epic #6851 / ADR-037 D2 模拟侧)

"""模拟盘 assemble_engine slippage 注入测试 (ADR-037 D2)。

验证共享 broker 从 PAPER portfolios 读取 slippage 的解析逻辑。
assemble_engine 重依赖 container, 故提取 _resolve_slippage_from_portfolios 为纯静态方法单测;
注入正确性 (build_fill_price_model) 由 test_fill_price_model.py 覆盖。
"""

from ginkgo.data.models.model_portfolio import MPortfolio


class TestResolveSlippageFromPortfolios:
    """_resolve_slippage_from_portfolios: 共享 broker 从 PAPER portfolios 读 slippage (ADR-037 D2)"""

    def test_first_portfolio_slippage_returned(self):
        """首个 portfolio.slippage=0.002 → 返回 0.002 (共享 broker 取首)"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        p = MPortfolio()
        p.slippage = 0.002
        rate = PaperTradingWorker._resolve_slippage_from_portfolios([p])
        assert rate is not None
        assert abs(rate - 0.002) < 1e-9

    def test_empty_returns_none(self):
        """空列表 → None (assemble_engine 此前已 return, 防御)"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        assert PaperTradingWorker._resolve_slippage_from_portfolios([]) is None

    def test_none_slippage_returns_none(self):
        """portfolio.slippage=None → None (回退 AttitudePricing 默认)"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        p = MPortfolio()
        p.slippage = None
        assert PaperTradingWorker._resolve_slippage_from_portfolios([p]) is None
