# Upstream: ginkgo.trading.brokers.fill_price_model (B1 产出), ginkgo.trading.paper.slippage_models
# Downstream: -
# Role: FillPriceModel 成交价模型契约测试 (Epic #6851 / ADR-037 D1)

"""
FillPriceModel 成交价模型测试

验证两个实现的契约:
- DeterministicSlippage: 包装 SlippageModel, 成交价 = close ± slippage
- AttitudePricing: 移植 scipy 态度采样, 成交价 ∈ [low, high]

TDD vertical slices: 每个 test 一个行为, RED→GREEN 循环。
"""

from decimal import Decimal

import numpy as np
import pytest
from unittest.mock import MagicMock

from ginkgo.enums import DIRECTION_TYPES, ATTITUDE_TYPES, ORDER_TYPES
from ginkgo.trading.paper.slippage_models import (
    FixedSlippage,
    PercentageSlippage,
    NoSlippage,
)
from ginkgo.trading.brokers.fill_price_model import (
    DeterministicSlippage,
    AttitudePricing,
    build_fill_price_model,
)
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory


class TestDeterministicSlippageFixed:
    """DeterministicSlippage 委托 SlippageModel 算成交价 (tracer bullet)"""

    def test_fixed_slippage_long_raises_price_by_slippage(self):
        """FixedSlippage 买入: 成交价 = close + slippage (买入成本增加)"""
        model = DeterministicSlippage(FixedSlippage(slippage=Decimal("0.02")))
        fill = model.calculate_fill_price(
            direction=DIRECTION_TYPES.LONG,
            low=Decimal("9.00"),
            high=Decimal("11.00"),
            close=Decimal("10.00"),
            attitude=ATTITUDE_TYPES.RANDOM,
            rng=np.random.default_rng(42),
        )
        assert fill == Decimal("10.02")


class TestAttitudePricingLimitMove:
    """AttitudePricing 涨停/跌停 (high==low): 锁定价直接返回, 不采样 (移植回归)"""

    def test_limit_up_returns_locked_price(self):
        """一字板 high==low: 成交价 = round(high, 2), 不消耗 rng"""
        model = AttitudePricing()
        fill = model.calculate_fill_price(
            direction=DIRECTION_TYPES.LONG,
            low=Decimal("11.00"),
            high=Decimal("11.00"),
            close=Decimal("11.00"),
            attitude=ATTITUDE_TYPES.RANDOM,
            rng=np.random.default_rng(42),
        )
        assert fill == Decimal("11.00")


class TestAttitudePricingRandom:
    """AttitudePricing RANDOM: 正态采样移植回归 (同 seed 可复现 + clip 区间约束)"""

    def test_same_seed_produces_same_price(self):
        """同 seed 两个 Generator: 采样结果一致 (random_state 正确传递给 scipy)"""
        model = AttitudePricing()
        common = dict(
            direction=DIRECTION_TYPES.LONG,
            low=Decimal("10.00"), high=Decimal("11.00"), close=Decimal("10.50"),
            attitude=ATTITUDE_TYPES.RANDOM,
        )
        fill_a = model.calculate_fill_price(**common, rng=np.random.default_rng(42))
        fill_b = model.calculate_fill_price(**common, rng=np.random.default_rng(42))
        assert fill_a == fill_b

    def test_price_clipped_to_range_across_seeds(self):
        """成交价恒 ∈ [low, high] (clip 约束), 50 个 seed 全覆盖"""
        model = AttitudePricing()
        for seed in range(50):
            fill = model.calculate_fill_price(
                direction=DIRECTION_TYPES.LONG,
                low=Decimal("10.00"), high=Decimal("11.00"), close=Decimal("10.50"),
                attitude=ATTITUDE_TYPES.RANDOM,
                rng=np.random.default_rng(seed),
            )
            assert Decimal("10.00") <= fill <= Decimal("11.00")


class TestAttitudePricingParityWithSimBroker:
    """黄金零回归: AttitudePricing == sim_broker._get_random_transaction_price (同 seed 逐字节一致)"""

    @pytest.mark.parametrize("attitude", [
        ATTITUDE_TYPES.RANDOM,
        ATTITUDE_TYPES.OPTIMISTIC,
        ATTITUDE_TYPES.PESSIMISTIC,
    ])
    @pytest.mark.parametrize("direction", [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT])
    def test_parity_with_sim_broker(self, direction, attitude):
        """同 seed=42: AttitudePricing 输出 == sim_broker 原生采样 (移植无数值漂移)"""
        # sim_broker 用 self._rng = default_rng(42), 调一次产生首个采样
        broker = SimBroker(random_seed=42)
        sim_price = broker._get_random_transaction_price(
            direction, Decimal("10.00"), Decimal("11.00"), attitude
        )
        # AttitudePricing 用独立同 seed Generator, 亦调一次
        attitude_price = AttitudePricing().calculate_fill_price(
            direction=direction,
            low=Decimal("10.00"), high=Decimal("11.00"), close=Decimal("10.50"),
            attitude=attitude,
            rng=np.random.default_rng(42),
        )
        assert attitude_price == sim_price, (
            f"parity break: direction={direction.name} attitude={attitude.name} "
            f"attitude={attitude_price} vs sim={sim_price}"
        )


class TestDeterministicSlippageVariants:
    """DeterministicSlippage 委托各 SlippageModel + 方向 (回归锁定)"""

    def test_fixed_slippage_short_lowers_price(self):
        """FixedSlippage 卖出: 成交价 = close - slippage (卖出收入减少)"""
        model = DeterministicSlippage(FixedSlippage(slippage=Decimal("0.02")))
        fill = model.calculate_fill_price(
            direction=DIRECTION_TYPES.SHORT,
            low=Decimal("9.00"), high=Decimal("11.00"), close=Decimal("10.00"),
            attitude=ATTITUDE_TYPES.RANDOM,
            rng=np.random.default_rng(42),
        )
        assert fill == Decimal("9.98")

    def test_percentage_slippage_long(self):
        """PercentageSlippage 买入: 成交价 = close * (1 + pct), 10.00 + 0.1% = 10.01"""
        model = DeterministicSlippage(PercentageSlippage(percentage=Decimal("0.001")))
        fill = model.calculate_fill_price(
            direction=DIRECTION_TYPES.LONG,
            low=Decimal("9.00"), high=Decimal("11.00"), close=Decimal("10.00"),
            attitude=ATTITUDE_TYPES.RANDOM,
            rng=np.random.default_rng(42),
        )
        assert fill == Decimal("10.01")

    def test_no_slippage_returns_close(self):
        """NoSlippage: 成交价 = close (无滑点, 穿透)"""
        model = DeterministicSlippage(NoSlippage())
        fill = model.calculate_fill_price(
            direction=DIRECTION_TYPES.LONG,
            low=Decimal("9.00"), high=Decimal("11.00"), close=Decimal("10.00"),
            attitude=ATTITUDE_TYPES.RANDOM,
            rng=np.random.default_rng(42),
        )
        assert fill == Decimal("10.00")


class TestSimBrokerFillPriceModelWiring:
    """SimBroker 接线 fill_price_model (B1): _calculate_transaction_price 委托"""

    @staticmethod
    def _make_market_order(direction=DIRECTION_TYPES.LONG):
        order = MagicMock()
        order.direction = direction
        order.code = "TEST.SZ"
        order.volume = 100
        order.limit_price = None
        order.order_type = ORDER_TYPES.MARKETORDER
        order.portfolio_id = "p"
        order.frozen_money = 2000
        order.uuid = "u12345678"
        return order

    @staticmethod
    def _make_market_data(low=10.0, high=11.0, close=10.50):
        d = MagicMock()
        d.low = low
        d.high = high
        d.close = close
        d.open = 10.3
        d.volume = 1000000
        return d

    def test_default_fill_price_model_is_attitude_pricing(self):
        """SimBroker() 默认 fill_price_model = AttitudePricing (零回归)"""
        broker = SimBroker()
        assert isinstance(broker._fill_price_model, AttitudePricing)

    def test_custom_fill_price_model_injected(self):
        """SimBroker(fill_price_model=X) 注入 X"""
        model = DeterministicSlippage(FixedSlippage(slippage=Decimal("0.02")))
        broker = SimBroker(fill_price_model=model)
        assert broker._fill_price_model is model

    def test_market_order_uses_injected_fill_price_model(self):
        """市价单成交价 = fill_price_model 输出 (DeterministicSlippage: close+0.02)"""
        model = DeterministicSlippage(FixedSlippage(slippage=Decimal("0.02")))
        broker = SimBroker(fill_price_model=model, attitude=ATTITUDE_TYPES.RANDOM)
        price = broker._calculate_transaction_price(
            self._make_market_order(DIRECTION_TYPES.LONG),
            self._make_market_data(close=10.50),
        )
        assert price == Decimal("10.52")


class TestCreateBrokerFromConfigSlippage:
    """create_broker_from_config 接通 fill_price_policy → 成交价模型 (ADR-037 D2 + 方案B)"""

    def test_slippage_policy_injects_deterministic_slippage(self):
        """engine_data fill_price_policy='slippage' → DeterministicSlippage"""
        broker = InfrastructureFactory.create_broker_from_config({
            "broker": "backtest",
            "fill_price_policy": "slippage",
            "slippage_rate": 0.001,
        })
        assert isinstance(broker, SimBroker)
        assert isinstance(broker._fill_price_model, DeterministicSlippage)

    def test_default_policy_is_attitude_pricing(self):
        """engine_data 无 fill_price_policy → 默认 attitude → AttitudePricing (零回归)"""
        broker = InfrastructureFactory.create_broker_from_config({
            "broker": "backtest",
        })
        assert isinstance(broker._fill_price_model, AttitudePricing)

    def test_explicit_attitude_policy_overrides_slippage_rate(self):
        """policy='attitude' 显式 → AttitudePricing (即使有 slippage_rate; 方案B: policy 决定非数值)"""
        broker = InfrastructureFactory.create_broker_from_config({
            "broker": "backtest",
            "fill_price_policy": "attitude",
            "slippage_rate": 0.001,
        })
        assert isinstance(broker._fill_price_model, AttitudePricing)


class TestBuildFillPriceModel:
    """build_fill_price_model(policy, slippage_rate) 工厂 (ADR-037 D2 + 方案B 显式 policy)

    policy 显式选择成交价模型 (默认 attitude=零回归; slippage=接通确定性滑点)。
    """

    def test_default_policy_is_attitude(self):
        """build_fill_price_model() 默认 attitude → AttitudePricing (零回归)"""
        m = build_fill_price_model()
        assert isinstance(m, AttitudePricing)

    def test_attitude_policy_explicit(self):
        """policy='attitude' 显式 → AttitudePricing"""
        m = build_fill_price_model("attitude")
        assert isinstance(m, AttitudePricing)

    def test_slippage_policy_with_rate(self):
        """policy='slippage' + rate=0.001 → DeterministicSlippage"""
        m = build_fill_price_model("slippage", 0.001)
        assert isinstance(m, DeterministicSlippage)

    def test_slippage_policy_rate_defaults(self):
        """policy='slippage' 无 rate → DeterministicSlippage (默认 0.0001)"""
        m = build_fill_price_model("slippage")
        assert isinstance(m, DeterministicSlippage)
