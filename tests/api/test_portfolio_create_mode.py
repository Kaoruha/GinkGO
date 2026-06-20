# #5622 #5859 — Portfolio 创建 mode 被忽略，硬编码为 BACKTEST
"""
验证 POST /api/v1/portfolios/ 创建组合时，请求体的 mode 字段
（BACKTEST/PAPER/LIVE）被正确传递给 Saga，而非硬编码为 BACKTEST(0)。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.portfolio import PortfolioCreate, PortfolioMode


def _mock_saga(uuid: str = "portfolio-uuid"):
    """构造一个执行成功的 mock saga。"""
    saga = MagicMock()
    saga.execute = AsyncMock(return_value=True)
    step = MagicMock()
    step.result = {"uuid": uuid}
    saga.steps = [step]
    saga.error = None
    return saga


class TestCreatePortfolioPassesMode:
    """create_portfolio 应把请求的 mode 传给 Saga（不硬编码）"""

    @pytest.mark.asyncio
    @patch("api.portfolio.get_portfolio", new_callable=AsyncMock)
    @patch("services.saga_transaction.PortfolioSagaFactory")
    async def test_paper_mode_passed_to_saga(self, mock_factory, mock_get_portfolio):
        from api.portfolio import create_portfolio

        mock_factory.create_portfolio_saga.return_value = _mock_saga()
        mock_get_portfolio.return_value = {"uuid": "portfolio-uuid", "mode": "PAPER"}

        data = PortfolioCreate(name="test_paper", initial_cash=100000, mode=PortfolioMode.PAPER)
        await create_portfolio(data)

        _, kwargs = mock_factory.create_portfolio_saga.call_args
        assert kwargs["mode"] == 1, f"PAPER 应映射为 1，实际为 {kwargs['mode']}"

    @pytest.mark.asyncio
    @patch("api.portfolio.get_portfolio", new_callable=AsyncMock)
    @patch("services.saga_transaction.PortfolioSagaFactory")
    async def test_live_mode_passed_to_saga(self, mock_factory, mock_get_portfolio):
        from api.portfolio import create_portfolio

        mock_factory.create_portfolio_saga.return_value = _mock_saga()
        mock_get_portfolio.return_value = {"uuid": "portfolio-uuid", "mode": "LIVE"}

        data = PortfolioCreate(name="test_live", initial_cash=100000, mode=PortfolioMode.LIVE)
        await create_portfolio(data)

        _, kwargs = mock_factory.create_portfolio_saga.call_args
        assert kwargs["mode"] == 2, f"LIVE 应映射为 2，实际为 {kwargs['mode']}"

    @pytest.mark.asyncio
    @patch("api.portfolio.get_portfolio", new_callable=AsyncMock)
    @patch("services.saga_transaction.PortfolioSagaFactory")
    async def test_default_mode_is_backtest(self, mock_factory, mock_get_portfolio):
        """不传 mode 时默认 BACKTEST(0)"""
        from api.portfolio import create_portfolio

        mock_factory.create_portfolio_saga.return_value = _mock_saga()
        mock_get_portfolio.return_value = {"uuid": "portfolio-uuid", "mode": "BACKTEST"}

        data = PortfolioCreate(name="test_default", initial_cash=100000)
        await create_portfolio(data)

        _, kwargs = mock_factory.create_portfolio_saga.call_args
        assert kwargs["mode"] == 0, f"默认应映射为 0(BACKTEST)，实际为 {kwargs['mode']}"
