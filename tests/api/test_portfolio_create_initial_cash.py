# #5407 #5380 — Portfolio 创建时 initial_cash 被忽略（默认 1000000）/ 缩水 10 倍
"""
验证 POST /api/v1/portfolios/ 创建组合时，请求体的 initial_cash 被正确传递：
1. Saga 工厂 create_portfolio_saga 接受 initial_cash，并在 create 步骤里
   以 initial_capital=<值> 转发给 portfolio_service.add。
2. 端点 create_portfolio 把 data.initial_cash 传给 Saga 工厂。

同根因：create_portfolio_saga (api/services/saga_transaction.py) 此前根本不接收
initial_cash，create 步骤只调 portfolio_service.add(name, mode)，导致 service
回退到默认 1000000.0。update 路径正确（update_portfolio_saga 已转发 initial_cash）。
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from models.portfolio import PortfolioCreate


def _mock_saga(uuid: str = "portfolio-uuid"):
    """构造一个执行成功的 mock saga（镜像 test_portfolio_create_mode 用法）。"""
    saga = Mock()
    saga.execute = AsyncMock(return_value=True)
    step = Mock()
    step.result = {"uuid": uuid}
    saga.steps = [step]
    saga.error = None
    return saga


class TestCreateSagaForwardsInitialCash:
    """create_portfolio_saga 应把 initial_cash 以 initial_capital 转发给 add()"""

    def test_initial_cash_forwarded_to_add(self):
        from services.saga_transaction import PortfolioSagaFactory

        portfolio_service = Mock()
        portfolio_result = Mock()
        portfolio_result.is_success.return_value = True
        portfolio_result.data.uuid = "portfolio-uuid"
        portfolio_service.add.return_value = portfolio_result

        mock_container = Mock()
        mock_container.portfolio_service.return_value = portfolio_service
        mock_container.portfolio_mapping_service.return_value = Mock()

        # container 是 dependency_injector 单例；saga 函数体内
        # `from ginkgo.data.containers import container` 在调用时读取该模块属性，
        # 故替换模块属性 container 即可拦截（参考 tests/unit/services 多处用法）。
        with patch("ginkgo.data.containers.container", mock_container):
            saga = PortfolioSagaFactory.create_portfolio_saga(
                name="t",
                mode=0,
                initial_cash=200000,
                selectors=[],
                strategies=[],
                risk_managers=[],
                analyzers=[],
            )

            # 只执行 create 步骤（steps[0] 恒为 create_portfolio）
            saga.steps[0].execute()

        portfolio_service.add.assert_called_once_with(
            name="t", mode=0, initial_capital=200000
        )


class TestEndpointPassesInitialCash:
    """create_portfolio 端点应把 data.initial_cash 传给 Saga 工厂"""

    @pytest.mark.asyncio
    @patch("api.portfolio.get_portfolio", new_callable=AsyncMock)
    @patch("services.saga_transaction.PortfolioSagaFactory")
    async def test_endpoint_passes_initial_cash(self, mock_factory, mock_get_portfolio):
        from api.portfolio import create_portfolio

        mock_factory.create_portfolio_saga.return_value = _mock_saga()
        mock_get_portfolio.return_value = {"uuid": "portfolio-uuid", "initial_cash": 200000}

        data = PortfolioCreate(name="test_cash", initial_cash=200000)
        await create_portfolio(data)

        _, kwargs = mock_factory.create_portfolio_saga.call_args
        assert kwargs.get("initial_cash") == 200000, (
            f"initial_cash 应为 200000，实际为 {kwargs.get('initial_cash')}"
        )
