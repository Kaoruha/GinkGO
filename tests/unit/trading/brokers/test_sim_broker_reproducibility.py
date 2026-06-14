"""模拟经纪商 SimBroker 可复现性单元测试。"""
import sys
import os
_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import DIRECTION_TYPES, ATTITUDE_TYPES, ORDER_TYPES


class TestSeedReproducibility:
    """SimBroker 随机种子可复现性测试"""

    def test_same_seed_same_price_sequence(self):
        """相同 seed 产生完全相同的成交价序列"""
        seed = 42
        prices1 = []
        prices2 = []

        for _ in range(10):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            price = broker._get_random_transaction_price(
                DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.RANDOM
            )
            prices1.append(float(price))

        for _ in range(10):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            price = broker._get_random_transaction_price(
                DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.RANDOM
            )
            prices2.append(float(price))

        assert prices1 == prices2

    def test_different_seed_different_price(self):
        """不同 seed 产生不同成交价"""
        broker1 = SimBroker(random_seed=42, attitude=ATTITUDE_TYPES.RANDOM)
        broker2 = SimBroker(random_seed=99, attitude=ATTITUDE_TYPES.RANDOM)

        p1 = float(broker1._get_random_transaction_price(
            DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.RANDOM
        ))
        p2 = float(broker2._get_random_transaction_price(
            DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.RANDOM
        ))

        assert p1 != p2

    def test_no_seed_produces_random_results(self):
        """不传 seed 每次结果不同"""
        prices = set()
        for _ in range(10):
            broker = SimBroker(attitude=ATTITUDE_TYPES.RANDOM)
            price = float(broker._get_random_transaction_price(
                DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.RANDOM
            ))
            prices.add(price)

        assert len(prices) > 1

    def test_optimistic_attitude_reproducible(self):
        """OPTIMISTIC 态度下成交价也可复现"""
        seed = 42
        broker1 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker2 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)

        p1 = float(broker1._get_random_transaction_price(
            DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.OPTIMISTIC
        ))
        p2 = float(broker2._get_random_transaction_price(
            DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.OPTIMISTIC
        ))

        assert p1 == p2

    def test_pessimistic_attitude_reproducible(self):
        """PESSIMISTIC 态度下成交价也可复现"""
        seed = 42
        broker1 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)
        broker2 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)

        p1 = float(broker1._get_random_transaction_price(
            DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.PESSIMISTIC
        ))
        p2 = float(broker2._get_random_transaction_price(
            DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.PESSIMISTIC
        ))

        assert p1 == p2

    def test_sell_direction_reproducible(self):
        """卖出方向也可复现"""
        seed = 42
        broker1 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker2 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)

        p1 = float(broker1._get_random_transaction_price(
            DIRECTION_TYPES.SHORT, 10.0, 11.0, ATTITUDE_TYPES.OPTIMISTIC
        ))
        p2 = float(broker2._get_random_transaction_price(
            DIRECTION_TYPES.SHORT, 10.0, 11.0, ATTITUDE_TYPES.OPTIMISTIC
        ))

        assert p1 == p2


class TestFillProbabilityReproducibility:
    """限价单成交概率可复现性测试"""

    def _make_limit_order(self, direction=DIRECTION_TYPES.LONG):
        order = MagicMock()
        order.direction = direction
        order.code = "000001.SZ"
        order.volume = 100
        order.limit_price = 10.5
        order.order_type = ORDER_TYPES.LIMITORDER
        order.portfolio_id = "test-portfolio"
        order.frozen_money = 2000
        order.uuid = "test-uuid-12345678"
        return order

    def _make_market_data(self, low=10.0, high=11.0, close=10.5):
        data = MagicMock()
        data.low = low
        data.high = high
        data.close = close
        data.open = 10.3
        data.volume = 1000000
        return data

    def test_pessimistic_fill_probability_reproducible(self):
        """PESSIMISTIC 态度下成交概率可复现"""
        results1 = []
        results2 = []
        seed = 42

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)
            broker.set_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results1.append(broker._can_order_be_filled(order, self._make_market_data()))

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)
            broker.set_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results2.append(broker._can_order_be_filled(order, self._make_market_data()))

        assert results1 == results2

    def test_random_fill_probability_reproducible(self):
        """RANDOM 态度下成交概率可复现"""
        results1 = []
        results2 = []
        seed = 42

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            broker.set_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results1.append(broker._can_order_be_filled(order, self._make_market_data()))

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            broker.set_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results2.append(broker._can_order_be_filled(order, self._make_market_data()))

        assert results1 == results2
