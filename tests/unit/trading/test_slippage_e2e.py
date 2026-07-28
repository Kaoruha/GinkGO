# Upstream: ginkgo.workers.backtest_worker.task_helpers, models, InfrastructureFactory, fill_price_model
# Downstream: -
# Role: slippage_rate 端到端链路测试 (Epic #6851 / ADR-037 B3)

"""slippage_rate 端到端链路测试 (ADR-037 B3)。

验证 BacktestConfig.slippage_rate → build_engine_data → create_broker_from_config
→ SimBroker._fill_price_model 完整链路 (回测侧 slippage 接通的端到端证据)。
"""

from ginkgo.workers.backtest_worker.models import BacktestConfig
from ginkgo.workers.backtest_worker.task_helpers import build_engine_data
from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory
from ginkgo.trading.brokers.fill_price_model import DeterministicSlippage
from ginkgo.trading.brokers.sim_broker import SimBroker


def _make_config(slippage_rate: float) -> BacktestConfig:
    """构造最小合法 BacktestConfig (11 字段必填, 仅 slippage_rate 变化)"""
    return BacktestConfig(
        start_date="2025-01-01",
        end_date="2025-06-01",
        initial_cash=100000.0,
        commission_rate=0.0003,
        slippage_rate=slippage_rate,
        benchmark_return=0.0,
        max_position_ratio=1.0,
        stop_loss_ratio=0.1,
        take_profit_ratio=0.2,
        frequency="1d",
        analyzers=[],
    )


class TestSlippageEndToEnd:
    """slippage_rate 端到端: BacktestConfig → engine_data → broker (ADR-037 B3)"""

    def test_build_engine_data_carries_slippage_rate(self):
        """build_engine_data 灌入 config.slippage_rate → engine_data (B2 通路确认)"""
        cfg = _make_config(slippage_rate=0.002)
        engine_data = build_engine_data(cfg)
        assert engine_data["slippage_rate"] == 0.002

    def test_slippage_rate_flows_to_deterministic_broker(self):
        """BacktestConfig.slippage_rate=0.002 → broker._fill_price_model=DeterministicSlippage"""
        cfg = _make_config(slippage_rate=0.002)
        engine_data = build_engine_data(cfg)
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert isinstance(broker, SimBroker)
        assert isinstance(broker._fill_price_model, DeterministicSlippage)

    def test_default_rate_still_deterministic(self):
        """默认 0.0001 (schema/DTO 默认) → DeterministicSlippage (Epic 目标: 默认接通)"""
        cfg = _make_config(slippage_rate=0.0001)
        engine_data = build_engine_data(cfg)
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert isinstance(broker._fill_price_model, DeterministicSlippage)
