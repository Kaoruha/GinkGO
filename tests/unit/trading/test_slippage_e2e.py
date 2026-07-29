# Upstream: ginkgo.workers.backtest_worker.task_helpers, models, InfrastructureFactory, fill_price_model
# Downstream: -
# Role: fill_price_policy 端到端链路测试 (Epic #6851 / ADR-037 D2 + 方案B B3)

"""fill_price_policy 端到端链路测试 (ADR-037 D2 + 方案B B3)。

验证 BacktestConfig.fill_price_policy → build_engine_data → create_broker_from_config
→ SimBroker._fill_price_model 完整链路。

方案B 核心: policy 决定成交价模型 (非 slippage_rate 数值):
- policy='attitude' (默认): AttitudePricing → 回测零回归
- policy='slippage': DeterministicSlippage → 接通 --slippage 死参数
"""

from ginkgo.workers.backtest_worker.models import BacktestConfig
from ginkgo.workers.backtest_worker.task_helpers import build_engine_data
from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory
from ginkgo.trading.brokers.fill_price_model import DeterministicSlippage, AttitudePricing
from ginkgo.trading.brokers.sim_broker import SimBroker


def _make_config(slippage_rate: float = 0.0001, fill_price_policy: str = "attitude") -> BacktestConfig:
    """构造最小合法 BacktestConfig (12 字段必填, 仅 fill_price_policy/slippage_rate 变化)"""
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
        fill_price_policy=fill_price_policy,
        analyzers=[],
    )


class TestFillPricePolicyEndToEnd:
    """fill_price_policy 端到端: BacktestConfig → engine_data → broker (ADR-037 D2 + 方案B B3)"""

    def test_build_engine_data_carries_slippage_rate(self):
        """build_engine_data 灌入 config.slippage_rate → engine_data (B2 通路保留)"""
        cfg = _make_config(slippage_rate=0.002)
        engine_data = build_engine_data(cfg)
        assert engine_data["slippage_rate"] == 0.002

    def test_build_engine_data_carries_fill_price_policy(self):
        """build_engine_data 灌入 config.fill_price_policy → engine_data (方案B 通路)"""
        cfg = _make_config(fill_price_policy="slippage")
        engine_data = build_engine_data(cfg)
        assert engine_data["fill_price_policy"] == "slippage"

    def test_default_policy_is_attitude_pricing(self):
        """默认 policy=attitude → AttitudePricing (零回归; 即使有 slippage_rate 也不接通)"""
        cfg = _make_config(slippage_rate=0.002)  # 默认 attitude policy
        engine_data = build_engine_data(cfg)
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert isinstance(broker, SimBroker)
        assert isinstance(broker._fill_price_model, AttitudePricing)

    def test_slippage_policy_flows_to_deterministic(self):
        """policy=slippage + rate=0.002 → DeterministicSlippage (接通 --slippage 死参数)"""
        cfg = _make_config(slippage_rate=0.002, fill_price_policy="slippage")
        engine_data = build_engine_data(cfg)
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert isinstance(broker._fill_price_model, DeterministicSlippage)

    def test_explicit_attitude_overrides_slippage_rate(self):
        """policy=attitude 显式 → AttitudePricing (即使 slippage_rate=0.002; 方案B: policy 决定非数值)"""
        cfg = _make_config(slippage_rate=0.002, fill_price_policy="attitude")
        engine_data = build_engine_data(cfg)
        broker = InfrastructureFactory.create_broker_from_config(engine_data)
        assert isinstance(broker._fill_price_model, AttitudePricing)
