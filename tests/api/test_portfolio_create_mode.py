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


# #5840 — POST /portfolios/ 创建成功但 message 为 "retrieved successfully"
class TestCreatePortfolioReturnsCreatedMessage:
    """create_portfolio 应返回 created 语义的 message，而非透传 get_portfolio 的 retrieved。

    根因: create_portfolio 末尾 `return await get_portfolio(uuid)` 复用了 get 的完整
    response dict（含 message="Portfolio retrieved successfully"），未覆盖语义字段。
    """

    @pytest.mark.asyncio
    @patch("api.portfolio.get_portfolio", new_callable=AsyncMock)
    @patch("services.saga_transaction.PortfolioSagaFactory")
    async def test_create_returns_created_message(self, mock_factory, mock_get_portfolio):
        from api.portfolio import create_portfolio

        mock_factory.create_portfolio_saga.return_value = _mock_saga()
        # 模拟真实 get_portfolio 返回（含 retrieved message，即 bug 现场）
        mock_get_portfolio.return_value = {
            "code": 0,
            "data": {"uuid": "portfolio-uuid", "mode": "BACKTEST"},
            "message": "Portfolio retrieved successfully",
            "trace_id": "t-1",
        }

        data = PortfolioCreate(name="test_msg", initial_cash=100000)
        response = await create_portfolio(data)

        assert response["message"] == "Portfolio created successfully", (
            f"创建应返回 created 语义，实际为 {response['message']!r}"
        )
        # data 应保留（复用 get 的数据组装，不破坏）
        assert response["data"]["uuid"] == "portfolio-uuid"
