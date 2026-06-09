"""
TDD test for #5937: InfrastructureFactory.setup_engine_infrastructure
must respect skip_feeder parameter.

Bug: skip_feeder=True is accepted but ignored, causing double feeder
creation → first feeder misses selector codes → 0 trades.

Fix order: tracer bullet → verify skip_feeder behavior → commit.
"""
import pytest
from unittest.mock import MagicMock, patch

from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory


@pytest.mark.unit
class TestSetupEngineInfrastructureSkipFeeder:
    """setup_engine_infrastructure 的 skip_feeder 行为"""

    def test_skip_feeder_true_does_not_bind_feeder(self):
        """skip_feeder=True 时，不应向引擎绑定任何 feeder"""
        mock_engine = MagicMock()

        with patch("ginkgo.trading.services._assembly.infrastructure_factory.GLOG"):
            InfrastructureFactory.setup_engine_infrastructure(
                engine=mock_engine,
                logger=MagicMock(),
                engine_data={},
                skip_feeder=True,
            )

        # feeder 不应被绑定
        mock_engine.set_data_feeder.assert_not_called()
        mock_engine.bind_datafeeder.assert_not_called()

    def test_skip_feeder_false_binds_feeder(self):
        """skip_feeder=False（默认）时，应正常绑定 feeder"""
        mock_engine = MagicMock()

        with patch("ginkgo.trading.services._assembly.infrastructure_factory.GLOG"):
            InfrastructureFactory.setup_engine_infrastructure(
                engine=mock_engine,
                logger=MagicMock(),
                engine_data={},
                skip_feeder=False,
            )

        # feeder 应被绑定（set_data_feeder 或 bind_datafeeder 二选一）
        assert (mock_engine.set_data_feeder.called
                or mock_engine.bind_datafeeder.called)

    def test_skip_feeder_true_still_sets_up_gateway(self):
        """skip_feeder=True 时，broker 和 gateway 仍应正常设置"""
        mock_engine = MagicMock()

        with patch("ginkgo.trading.services._assembly.infrastructure_factory.GLOG"):
            InfrastructureFactory.setup_engine_infrastructure(
                engine=mock_engine,
                logger=MagicMock(),
                engine_data={"broker": "backtest"},
                skip_feeder=True,
            )

        # gateway（router）仍应被绑定
        mock_engine.bind_router.assert_called_once()
