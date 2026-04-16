"""
EngineAssemblyService PAPER模式装配测试

验证 assemble_backtest_engine() 在不同 execution_mode 下的装配行为：
- BACKTEST: BacktestFeeder + SimBroker (现有行为不变)
- PAPER:   OKXDataFeeder + SimBroker
- LIVE:    OKXDataFeeder + OKXBroker (如果可用)
"""
import pytest
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.enums import EXECUTION_MODE
from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory
from ginkgo.data.services.base_service import ServiceResult


def _make_engine_data(execution_mode=None):
    """构造最小化的 engine_data 字典"""
    data: Dict[str, Any] = {
        "name": "test_engine",
        "uuid": "engine-001",
        "backtest_start_date": "2024-01-01",
        "backtest_end_date": "2024-06-01",
    }
    if execution_mode is not None:
        data["execution_mode"] = execution_mode
    return data


@pytest.mark.unit
class TestExecutionModeResolution:
    """验证 execution_mode 从 engine_data 正确解析"""

    def test_default_mode_is_backtest(self):
        """engine_data 无 execution_mode 时默认为 BACKTEST"""
        mode = InfrastructureFactory.resolve_execution_mode(_make_engine_data())
        assert mode == EXECUTION_MODE.BACKTEST

    def test_paper_mode_resolved(self):
        """engine_data.execution_mode=2 解析为 EXECUTION_MODE.PAPER"""
        mode = InfrastructureFactory.resolve_execution_mode(_make_engine_data(execution_mode=2))
        assert mode == EXECUTION_MODE.PAPER

    def test_paper_string_resolved(self):
        """engine_data.execution_mode='paper' 解析为 EXECUTION_MODE.PAPER"""
        mode = InfrastructureFactory.resolve_execution_mode(_make_engine_data(execution_mode="paper"))
        assert mode == EXECUTION_MODE.PAPER

    def test_live_mode_resolved(self):
        """engine_data.execution_mode=1 解析为 EXECUTION_MODE.LIVE"""
        mode = InfrastructureFactory.resolve_execution_mode(_make_engine_data(execution_mode=1))
        assert mode == EXECUTION_MODE.LIVE

    def test_backtest_explicit(self):
        """engine_data.execution_mode=0 显式设置 BACKTEST"""
        mode = InfrastructureFactory.resolve_execution_mode(_make_engine_data(execution_mode=0))
        assert mode == EXECUTION_MODE.BACKTEST


@pytest.mark.unit
class TestFeederSelection:
    """验证根据 execution_mode 选择正确的 DataFeeder"""

    def test_backtest_creates_backtest_feeder(self):
        """BACKTEST 模式创建 BacktestFeeder"""
        from ginkgo.trading.feeders import BacktestFeeder
        feeder = InfrastructureFactory.create_feeder_for_mode(EXECUTION_MODE.BACKTEST)
        assert isinstance(feeder, BacktestFeeder)

    def test_paper_creates_okx_data_feeder(self):
        """PAPER 模式创建 OKXDataFeeder"""
        from ginkgo.trading.feeders import OKXDataFeeder
        feeder = InfrastructureFactory.create_feeder_for_mode(EXECUTION_MODE.PAPER)
        assert isinstance(feeder, OKXDataFeeder)

    def test_live_creates_okx_data_feeder(self):
        """LIVE 模式创建 OKXDataFeeder"""
        from ginkgo.trading.feeders import OKXDataFeeder
        feeder = InfrastructureFactory.create_feeder_for_mode(EXECUTION_MODE.LIVE)
        assert isinstance(feeder, OKXDataFeeder)


@pytest.mark.unit
class TestBrokerSelectionForPaper:
    """验证 PAPER 模式下的 Broker 选择"""

    def test_paper_mode_uses_sim_broker(self):
        """PAPER 模式使用 SimBroker"""
        from ginkgo.trading.brokers.sim_broker import SimBroker
        broker = InfrastructureFactory.create_broker_from_config(_make_engine_data(execution_mode="paper"))
        assert isinstance(broker, SimBroker)

    def test_paper_mode_fallback_to_sim(self):
        """PAPER 模式即使配置了 broker_config 也回退到 SimBroker"""
        from ginkgo.trading.brokers.sim_broker import SimBroker
        engine_data = _make_engine_data(execution_mode="paper")
        engine_data["broker_config"] = {"type": "okx"}
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert isinstance(broker, SimBroker)

    def test_broker_config_passes_attitude(self):
        """broker_attitude 正确传递给 SimBroker"""
        from ginkgo.trading.brokers.sim_broker import SimBroker
        from ginkgo.enums import ATTITUDE_TYPES
        engine_data = _make_engine_data(execution_mode="backtest")
        engine_data["broker_attitude"] = 1  # PESSIMISTIC
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert isinstance(broker, SimBroker)
        assert broker._attitude == ATTITUDE_TYPES.PESSIMISTIC

    def test_broker_config_merges_user_settings(self):
        """broker_config 中的自定义配置合并到 SimBroker"""
        from ginkgo.trading.brokers.sim_broker import SimBroker
        engine_data = _make_engine_data(execution_mode="backtest")
        engine_data["broker_config"] = {"commission_rate": 0.001, "commission_min": 10}
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert broker._commission_rate == Decimal("0.001")
        assert broker._commission_min == Decimal("10")


@pytest.mark.unit
class TestBrokerSelectionForLive:
    """验证 LIVE 模式下的 Broker 选择"""

    @patch("ginkgo.trading.services._assembly.infrastructure_factory.OkxBroker", None)
    def test_live_mode_without_okx_fallback_to_sim(self):
        """LIVE 模式下 OkxBroker 不可用时回退到 SimBroker"""
        from ginkgo.trading.brokers.sim_broker import SimBroker
        broker = InfrastructureFactory.create_broker_from_config(_make_engine_data(execution_mode="live"))
        assert isinstance(broker, SimBroker)


@pytest.mark.unit
class TestBaseEngineModeSetting:
    """验证 _create_base_engine 根据 execution_mode 设置正确的 engine mode"""

    def test_backtest_engine_mode(self):
        """BACKTEST engine_data 创建 BACKTEST 模式引擎"""
        engine = InfrastructureFactory.create_base_engine(
            _make_engine_data(execution_mode="backtest"),
            "test-engine",
            MagicMock(),
        )
        assert engine.mode == EXECUTION_MODE.BACKTEST

    def test_paper_engine_mode(self):
        """PAPER engine_data 创建 PAPER 模式引擎"""
        engine = InfrastructureFactory.create_base_engine(
            _make_engine_data(execution_mode="paper"),
            "test-engine",
            MagicMock(),
        )
        assert engine.mode == EXECUTION_MODE.PAPER


@pytest.mark.unit
class TestSetupDataFeederForEngine:
    """验证 setup_data_feeder_for_engine 集成装配流程"""

    def test_backtest_setup_binds_backtest_feeder(self):
        """BACKTEST 模式正确绑定 BacktestFeeder 到引擎"""
        from ginkgo.trading.feeders import BacktestFeeder
        engine = InfrastructureFactory.create_base_engine(
            _make_engine_data(execution_mode="backtest"),
            "test-engine",
            MagicMock(),
        )
        logger = MagicMock()
        result = InfrastructureFactory.setup_data_feeder_for_engine(
            engine, logger, _make_engine_data(execution_mode="backtest")
        )
        assert result is True
        assert isinstance(engine._datafeeder, BacktestFeeder)

    def test_feeder_event_publisher_bound(self):
        """feeder 的 set_event_publisher 被调用并传入 engine.put"""
        engine = InfrastructureFactory.create_base_engine(
            _make_engine_data(execution_mode="backtest"),
            "test-engine",
            MagicMock(),
        )
        logger = MagicMock()
        result = InfrastructureFactory.setup_data_feeder_for_engine(
            engine, logger, _make_engine_data(execution_mode="backtest")
        )
        assert result is True
        # BacktestFeeder 应该已经通过 set_event_publisher 绑定了 engine.put
        assert engine._datafeeder.event_publisher is not None
