# Upstream: ginkgo.data.models.model_portfolio
# Downstream: -
# Role: MPortfolio.slippage 列测试 (Epic #6851 / ADR-037 D3)

"""MPortfolio.slippage 字段测试 (ADR-037 D3): 模拟盘长驻滑点参数, 与回测 slippage_rate 同语义。"""

from ginkgo.data.models.model_portfolio import MPortfolio


class TestMPortfolioSlippage:
    """MPortfolio.slippage 列 (ADR-037 D3 模拟盘存储)"""

    def test_slippage_field_exists(self):
        """MPortfolio 表含 slippage 列 (模拟盘长驻滑点参数, 百分比小数默认 0.0001)"""
        assert "slippage" in MPortfolio.__table__.columns

    def test_update_sets_slippage(self):
        """update(str, slippage=...) 设置 slippage 字段 (与 initial_capital 等同范式, 赋 float)"""
        p = MPortfolio()
        p.update("test-portfolio", slippage=0.001)
        assert p.slippage is not None
        assert abs(float(p.slippage) - 0.001) < 1e-9
