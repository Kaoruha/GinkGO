"""#6640: 装配失败错误透传——缺必需组件时 assemble_backtest_engine 返回的 error
含具体缺失组件名（非笼统 'No portfolios bound to engine'），便于 backtest cat /
API 回测详情向用户暴露真因（'No sizer found' 此前仅在 worker 日志，用户看不到）。

清单驱动：requirements.find_missing_required_components 检查分桶 portfolio_components，
缺失组件透传到 ServiceResult.error。
"""
import pytest
from unittest.mock import MagicMock, patch

from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory

_PORTFOLIO_ID = "pp11223344556677889900aabbccdd01"
_ENGINE_ID = "en11223344556677889900aabbccdd02"


def _make_portfolio_mapping(pid):
    m = MagicMock()
    m.portfolio_id = pid
    return m


class _StubInfraFactory:
    """InfrastructureFactory 静态方法的 no-op 替身，跳过真实 engine 构造。"""

    @staticmethod
    def create_base_engine(engine_data, engine_id, logger, progress_callback=None):
        engine = MagicMock()
        engine.status = "READY"
        engine.state = 0
        return engine

    @staticmethod
    def setup_engine_infrastructure(engine, logger, engine_data, skip_feeder=False):
        return True

    @staticmethod
    def setup_data_feeder_for_engine(engine, logger, engine_data):
        return True


def _patch_infra_factory():
    """patch InfrastructureFactory 的三个静态方法为 stub。"""
    return [
        patch.object(InfrastructureFactory, "create_base_engine", _StubInfraFactory.create_base_engine),
        patch.object(InfrastructureFactory, "setup_engine_infrastructure", _StubInfraFactory.setup_engine_infrastructure),
        patch.object(InfrastructureFactory, "setup_data_feeder_for_engine", _StubInfraFactory.setup_data_feeder_for_engine),
    ]


class TestAssemblyErrorPropagation:
    """#6640: 缺必需组件时装配错误含具体组件名（清单驱动透传）。"""

    @pytest.mark.unit
    def test_missing_sizer_error_names_component(self):
        """portfolio_components 缺 sizer + binding 失败 → error 含 'Sizer'。"""
        service = EngineAssemblyService()
        # 直接 mock binding 入口，聚焦错误透传逻辑（不依赖 portfolio 实例创建细节）
        service._bind_portfolio_to_engine_with_ids = MagicMock(return_value=False)

        engine_data = {"name": "test_engine", "task_id": _ENGINE_ID}
        portfolio_mappings = [_make_portfolio_mapping(_PORTFOLIO_ID)]
        portfolio_configs = {_PORTFOLIO_ID: {"uuid": _PORTFOLIO_ID, "cash": 100000}}
        portfolio_components = {
            _PORTFOLIO_ID: {
                "strategies": [{"file_id": "f1", "type": 6, "uuid": "m1"}],
                "selectors": [{"file_id": "f2", "type": 4, "uuid": "m2"}],
                "sizers": [],  # 缺 sizer
            }
        }

        patches = _patch_infra_factory()
        for p in patches:
            p.start()
        try:
            result = service.assemble_backtest_engine(
                engine_id=_ENGINE_ID,
                engine_data=engine_data,
                portfolio_mappings=portfolio_mappings,
                portfolio_configs=portfolio_configs,
                portfolio_components=portfolio_components,
            )
        finally:
            for p in patches:
                p.stop()

        assert not result.is_success(), "缺 sizer 装配应失败"
        assert "Sizer" in result.error, "error 应含具体缺失组件名 Sizer"
        # 不再是笼统信息（用户可见路径已透传真因）
        assert "No portfolios bound to engine" not in result.error

    @pytest.mark.unit
    def test_missing_strategy_and_selector_listed(self):
        """缺 strategy+selector（仅绑 sizer）→ error 含 Strategy 与 Selector。"""
        service = EngineAssemblyService()
        service._bind_portfolio_to_engine_with_ids = MagicMock(return_value=False)

        engine_data = {"name": "test_engine", "task_id": _ENGINE_ID}
        portfolio_mappings = [_make_portfolio_mapping(_PORTFOLIO_ID)]
        portfolio_configs = {_PORTFOLIO_ID: {"uuid": _PORTFOLIO_ID, "cash": 100000}}
        portfolio_components = {
            _PORTFOLIO_ID: {
                "strategies": [],
                "selectors": [],
                "sizers": [{"file_id": "f3", "type": 5, "uuid": "m3"}],
            }
        }

        patches = _patch_infra_factory()
        for p in patches:
            p.start()
        try:
            result = service.assemble_backtest_engine(
                engine_id=_ENGINE_ID,
                engine_data=engine_data,
                portfolio_mappings=portfolio_mappings,
                portfolio_configs=portfolio_configs,
                portfolio_components=portfolio_components,
            )
        finally:
            for p in patches:
                p.stop()

        assert not result.is_success()
        assert "Strategy" in result.error
        assert "Selector" in result.error

    @pytest.mark.unit
    def test_all_present_binding_success_does_not_raise(self):
        """回归保护：组件齐全 + binding 成功 → 不触发缺失组件错误路径。"""
        service = EngineAssemblyService()
        service._bind_portfolio_to_engine_with_ids = MagicMock(return_value=True)

        engine_data = {"name": "test_engine", "task_id": _ENGINE_ID}
        portfolio_mappings = [_make_portfolio_mapping(_PORTFOLIO_ID)]
        portfolio_configs = {_PORTFOLIO_ID: {"uuid": _PORTFOLIO_ID, "cash": 100000}}
        portfolio_components = {
            _PORTFOLIO_ID: {
                "strategies": [{"file_id": "f1", "type": 6, "uuid": "m1"}],
                "selectors": [{"file_id": "f2", "type": 4, "uuid": "m2"}],
                "sizers": [{"file_id": "f3", "type": 5, "uuid": "m3"}],
            }
        }

        patches = _patch_infra_factory()
        for p in patches:
            p.start()
        try:
            result = service.assemble_backtest_engine(
                engine_id=_ENGINE_ID,
                engine_data=engine_data,
                portfolio_mappings=portfolio_mappings,
                portfolio_configs=portfolio_configs,
                portfolio_components=portfolio_components,
            )
        finally:
            for p in patches:
                p.stop()

        assert result.is_success(), "组件齐全应装配成功"
