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


@pytest.mark.unit
class TestGroupComponentsByType:
    """#6098: group_components_by_type 形状转换测试

    把 assemble_live_portfolio 拿到的扁平组件 list（B 的输入格式）
    转成 ComponentLoader.perform_component_binding 期望的分桶 dict（A 的输入格式）。
    字段重命名: component_id→file_id, mount_id→mapping_uuid, component_type→type(int)
    """

    def test_buckets_and_renames_fields(self):
        """int / 数字串 / 枚举名 三种 component_type 都能正确分桶并重命名字段"""
        from ginkgo.trading.services.engine_assembly_service import group_components_by_type

        components = [
            {"component_type": 6, "component_id": "strat-file-1", "mount_id": "strat-mount-1"},
            {"component_type": "4", "component_id": "sel-file-1", "mount_id": "sel-mount-1"},
            {"component_type": "SELECTOR", "component_id": "sel-file-2"},
            {"component_type": 5, "component_id": "sizer-file-1", "mount_id": "sizer-mount-1"},
            {"component_type": "RISKMANAGER", "component_id": "risk-file-1", "mount_id": "risk-mount-1"},
            {"component_type": 1, "component_id": "analyzer-file-1", "mount_id": "an-mount-1"},
        ]

        grouped = group_components_by_type(components)

        # int 类型 + 字段重命名 + mount_id 透传
        assert grouped["strategies"] == [
            {"file_id": "strat-file-1", "type": 6, "mapping_uuid": "strat-mount-1"}
        ]
        # 数字串 "4" 与 枚举名 "SELECTOR" 都归入 selectors，第二个无 mount_id → None
        assert grouped["selectors"] == [
            {"file_id": "sel-file-1", "type": 4, "mapping_uuid": "sel-mount-1"},
            {"file_id": "sel-file-2", "type": 4, "mapping_uuid": None},
        ]
        assert grouped["sizers"] == [
            {"file_id": "sizer-file-1", "type": 5, "mapping_uuid": "sizer-mount-1"}
        ]
        # 枚举名 "RISKMANAGER" → FILE_TYPES.RISKMANAGER.value = 3
        assert grouped["risk_managers"] == [
            {"file_id": "risk-file-1", "type": 3, "mapping_uuid": "risk-mount-1"}
        ]
        assert grouped["analyzers"] == [
            {"file_id": "analyzer-file-1", "type": 1, "mapping_uuid": "an-mount-1"}
        ]

    def test_empty_input_returns_all_buckets_empty(self):
        """空 list → 五个桶都为空（A 的 perform_component_binding 对空桶走严格失败）"""
        from ginkgo.trading.services.engine_assembly_service import group_components_by_type

        grouped = group_components_by_type([])

        assert grouped == {
            "strategies": [],
            "selectors": [],
            "sizers": [],
            "risk_managers": [],
            "analyzers": [],
        }


@pytest.mark.unit
class TestAssembleLivePortfolioRoutesThroughLoader:
    """#6098: live 有组件配置时，统一走 ComponentLoader.perform_component_binding

    取代旧的 _bind_components_from_config（B 路径），消除与回测路径的复制后差异。
    """

    def _make_service_with_components(self, components):
        portfolio_model = _make_portfolio_model()
        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get.return_value = _make_service_result(data=portfolio_model)
        mock_portfolio_service.get_components.return_value = _make_service_result(data=components)

        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
        service = EngineAssemblyService(portfolio_service=mock_portfolio_service)
        # 替换真实 loader，隔离文件 I/O 与动态执行
        mock_loader = MagicMock()
        service._component_loader = mock_loader
        return service, mock_loader

    def test_routes_configured_components_through_component_loader(self):
        """有组件配置 → 用分桶 dict + PortfolioLive 调 loader，True 则成功返回 portfolio"""
        service, mock_loader = self._make_service_with_components([
            {"component_type": 6, "component_id": "strat-1", "mount_id": "m-strat"},
            {"component_type": 4, "component_id": "sel-1", "mount_id": "m-sel"},
            {"component_type": 5, "component_id": "sizer-1", "mount_id": "m-sizer"},
        ])
        mock_loader.perform_component_binding.return_value = True

        result = service.assemble_live_portfolio(
            portfolio_id="test-pf-001",
            position_writer=MagicMock(),
            redis_writer=MagicMock(),
        )

        assert result.is_success(), f"Expected success, got: {result.error}"
        mock_loader.perform_component_binding.assert_called_once()
        bound_portfolio, grouped = mock_loader.perform_component_binding.call_args.args[:2]
        from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
        assert isinstance(bound_portfolio, PortfolioLive)
        assert grouped["strategies"] == [{"file_id": "strat-1", "type": 6, "mapping_uuid": "m-strat"}]
        assert grouped["selectors"] == [{"file_id": "sel-1", "type": 4, "mapping_uuid": "m-sel"}]
        assert grouped["sizers"] == [{"file_id": "sizer-1", "type": 5, "mapping_uuid": "m-sizer"}]

    def test_returns_failure_when_loader_reports_binding_failed(self):
        """loader 返回 False（如缺必需组件）→ assemble_live_portfolio 返回失败，不再静默补默认"""
        service, mock_loader = self._make_service_with_components([
            {"component_type": 6, "component_id": "strat-1", "mount_id": "m-strat"},
            # 故意缺 selector/sizer，模拟部分配置 → loader 应判失败
        ])
        mock_loader.perform_component_binding.return_value = False

        result = service.assemble_live_portfolio(
            portfolio_id="test-pf-001",
            position_writer=MagicMock(),
            redis_writer=MagicMock(),
        )

        assert not result.is_success()
        mock_loader.perform_component_binding.assert_called_once()
