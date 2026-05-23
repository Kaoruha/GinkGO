"""
#3866 TDD: EngineAssemblyService.assemble_live_portfolio

验证组件装配逻辑从 data 层迁移到 trading 层后的行为：
- 给定 portfolio_id + data 层提供的基础设施，装配出完整的 PortfolioLive
- Data 层不再了解 trading 层具体组件
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.base_service import ServiceResult


def _make_portfolio_model(uuid="test-pf-001", name="测试组合", initial_capital=1000000.0):
    """构造模拟的 portfolio model 对象"""
    model = SimpleNamespace(
        uuid=uuid,
        name=name,
        initial_capital=initial_capital,
    )
    return model


def _make_service_result(data=None, success=True, error=""):
    result = ServiceResult(success=success)
    result.data = data
    result.error = error
    return result


@pytest.mark.unit
class TestAssembleLivePortfolioBasic:
    """assemble_live_portfolio 基本行为测试"""

    def test_returns_portfolio_live_with_correct_identity(self):
        """给定有效 portfolio_id，返回具有正确 uuid/name/capital 的 PortfolioLive"""
        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService

        portfolio_model = _make_portfolio_model(
            uuid="pf-abc-123", name="我的实盘", initial_capital=500000.0
        )
        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get.return_value = _make_service_result(data=portfolio_model)
        mock_portfolio_service.get_components.return_value = _make_service_result(data=[])

        service = EngineAssemblyService(portfolio_service=mock_portfolio_service)
        mock_position_writer = MagicMock()
        mock_redis_writer = MagicMock()

        result = service.assemble_live_portfolio(
            portfolio_id="pf-abc-123",
            position_writer=mock_position_writer,
            redis_writer=mock_redis_writer,
        )

        assert result.is_success(), f"Expected success, got error: {result.error}"
        portfolio = result.data
        from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
        assert isinstance(portfolio, PortfolioLive)
        assert portfolio.uuid == "pf-abc-123"
        assert portfolio.name == "我的实盘"

    def test_returns_error_for_nonexistent_portfolio(self):
        """给定不存在的 portfolio_id，返回 ServiceResult.error"""
        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService

        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get.return_value = _make_service_result(
            success=False, error="Portfolio不存在"
        )

        service = EngineAssemblyService(portfolio_service=mock_portfolio_service)
        result = service.assemble_live_portfolio(
            portfolio_id="nonexistent-id",
            position_writer=MagicMock(),
            redis_writer=MagicMock(),
        )

        assert not result.is_success()
        assert "不存在" in result.error or "nonexistent" in result.error

    def test_binds_default_components_when_no_components_configured(self):
        """无组件配置时，使用默认组件（RandomSignalStrategy/CNAllSelector/FixedSizer/PositionRatioRisk）"""
        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService

        portfolio_model = _make_portfolio_model()
        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get.return_value = _make_service_result(data=portfolio_model)
        mock_portfolio_service.get_components.return_value = _make_service_result(data=[])

        service = EngineAssemblyService(portfolio_service=mock_portfolio_service)
        result = service.assemble_live_portfolio(
            portfolio_id="test-pf-001",
            position_writer=MagicMock(),
            redis_writer=MagicMock(),
        )

        assert result.is_success()
        portfolio = result.data
        # 验证默认组件已绑定
        assert len(portfolio.strategies) >= 1
        assert len(portfolio.selectors) >= 1
        assert portfolio.sizer is not None
        assert len(portfolio.risk_managers) >= 1

    def test_sets_engine_context_on_portfolio(self):
        """装配后 portfolio 应持有正确的 PortfolioContext"""
        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService

        portfolio_model = _make_portfolio_model(uuid="ctx-test-001")
        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get.return_value = _make_service_result(data=portfolio_model)
        mock_portfolio_service.get_components.return_value = _make_service_result(data=[])

        service = EngineAssemblyService(portfolio_service=mock_portfolio_service)
        result = service.assemble_live_portfolio(
            portfolio_id="ctx-test-001",
            position_writer=MagicMock(),
            redis_writer=MagicMock(),
        )

        assert result.is_success()
        portfolio = result.data
        assert hasattr(portfolio, '_context')
        assert portfolio._context is not None
        assert portfolio._context.portfolio_id == "ctx-test-001"

    def test_passes_position_and_redis_writers_to_portfolio(self):
        """position_writer 和 redis_writer 应正确传递给 PortfolioLive"""
        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService

        portfolio_model = _make_portfolio_model()
        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get.return_value = _make_service_result(data=portfolio_model)
        mock_portfolio_service.get_components.return_value = _make_service_result(data=[])

        service = EngineAssemblyService(portfolio_service=mock_portfolio_service)
        mock_pw = MagicMock(name="position_writer")
        mock_rw = MagicMock(name="redis_writer")

        result = service.assemble_live_portfolio(
            portfolio_id="test-pf-001",
            position_writer=mock_pw,
            redis_writer=mock_rw,
        )

        assert result.is_success()
        portfolio = result.data
        assert portfolio._position_writer is mock_pw
        assert portfolio._redis_writer is mock_rw
