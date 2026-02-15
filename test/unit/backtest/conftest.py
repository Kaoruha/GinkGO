"""
Backtest 模块共享 fixtures

提供 backtest 模块测试所需的共享资源。
"""

import pytest
import random
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES, DIRECTION_TYPES


@pytest.fixture
def random_bar_data():
    """生成随机Bar数据"""
    return {
        "code": "TEST001",
        "open": Decimal(str(round(random.uniform(0, 100), 2))),
        "high": Decimal(str(round(random.uniform(0, 100), 3))),
        "low": Decimal(str(round(random.uniform(0, 100), 2))),
        "close": Decimal(str(round(random.uniform(0, 100), 2))),
        "volume": random.randint(0, 1000),
        "amount": Decimal(str(round(random.uniform(0, 100), 2))),
        "frequency": random.choice([i for i in FREQUENCY_TYPES]),
        "timestamp": datetime.now(),
        "source": random.choice([i for i in SOURCE_TYPES]),
    }


@pytest.fixture
def standard_bar_data():
    """标准Bar数据"""
    return {
        "code": "000001.SZ",
        "open": Decimal("10.0"),
        "high": Decimal("10.8"),
        "low": Decimal("9.8"),
        "close": Decimal("10.5"),
        "volume": 1000000,
        "amount": Decimal("10500000.0"),
        "frequency": FREQUENCY_TYPES.DAY,
        "timestamp": datetime(2024, 1, 15, 9, 30, 0),
        "source": SOURCE_TYPES.TUSHARE
    }


@pytest.fixture
def standard_order_data():
    """标准订单数据"""
    return {
        "code": "000001.SZ",
        "direction": DIRECTION_TYPES.LONG,
        "order_type": "LIMIT",
        "status": "NEW",
        "volume": 100,
        "limit_price": 50.0,
        "frozen": 10.0,
        "transaction_price": 45.0,
        "transaction_volume": 50,
        "remain": 50.0,
        "fee": 1.0,
        "timestamp": datetime(2024, 1, 15, 9, 30, 0),
        "order_id": "order123",
        "portfolio_id": "portfolio1",
        "engine_id": "engine1",
    }


@pytest.fixture
def standard_position_data():
    """标准持仓数据"""
    return {
        "portfolio_id": "test_portfolio",
        "engine_id": "test_engine",
        "code": "000001.SZ",
        "cost": Decimal("10.0"),
        "volume": 1000,
        "frozen_volume": 0,
        "frozen_money": Decimal("0.0"),
        "price": Decimal("10.5"),
        "fee": Decimal("10.0"),
        "uuid": "test_uuid",
    }


@pytest.fixture
def random_position_data():
    """随机持仓数据"""
    cost = random.uniform(1, 100)
    price = random.uniform(1, 100)
    volume = random.randint(1, 1000)
    frozen_volume = random.randint(0, volume)
    frozen_money = frozen_volume * price
    fee = random.uniform(0, 10)

    return {
        "portfolio_id": f"portfolio_{random.randint(1, 100)}",
        "engine_id": f"engine_{random.randint(1, 100)}",
        "code": f"00000{random.randint(1, 999)}",
        "cost": cost,
        "volume": volume,
        "frozen_volume": frozen_volume,
        "frozen_money": frozen_money,
        "price": price,
        "fee": fee,
        "uuid": f"uuid_{random.randint(1, 1000)}",
    }


@pytest.fixture
def bar_sequence_10days():
    """生成10天连续的Bar数据"""
    bars = []
    base_price = Decimal("10.0")
    base_date = datetime(2024, 1, 1, 9, 30, 0)

    for i in range(10):
        bar = Bar()
        bar.code = "000001.SZ"
        bar.timestamp = base_date + timedelta(days=i)
        bar.open = base_price + Decimal(str(i * 0.1))
        bar.high = base_price + Decimal(str(i * 0.1 + 0.5))
        bar.low = base_price + Decimal(str(i * 0.1 - 0.3))
        bar.close = base_price + Decimal(str(i * 0.1 + 0.2))
        bar.volume = 1000000 + i * 10000
        bar.amount = bar.close * bar.volume
        bar.frequency = FREQUENCY_TYPES.DAY
        bar.source = SOURCE_TYPES.TUSHARE
        bars.append(bar)

    return bars


@pytest.fixture
def price_update_sequence():
    """价格更新序列"""
    base_price = Decimal("10.0")
    base_time = datetime(2024, 1, 1, 9, 30, 0)
    prices = []

    for i in range(10):
        price_data = {
            "code": "000001.SZ",
            "price": base_price + Decimal(str(i * 0.1)),
            "timestamp": base_time + timedelta(minutes=i)
        }
        prices.append(price_data)

    return prices


# ===== 辅助函数 Fixtures =====

@pytest.fixture
def create_bar():
    """创建Bar的工厂函数"""
    def _create(code="000001.SZ", price=Decimal("10.0"),
                timestamp=None, frequency=FREQUENCY_TYPES.DAY):
        bar = Bar()
        bar.code = code
        bar.open = price
        bar.high = price * Decimal("1.02")
        bar.low = price * Decimal("0.98")
        bar.close = price * Decimal("1.01")
        bar.volume = 1000000
        bar.amount = bar.close * bar.volume
        bar.frequency = frequency
        bar.timestamp = timestamp or datetime.now()
        bar.source = SOURCE_TYPES.TUSHARE
        return bar

    return _create


@pytest.fixture
def create_test_order():
    """创建测试订单的工厂函数"""
    def _create(code="000001.SZ", volume=100, direction=DIRECTION_TYPES.LONG):
        order = Order()
        order.code = code
        order.volume = volume
        order.direction = direction
        order.status = "NEW"
        order.order_type = "LIMIT"
        return order

    return _create


@pytest.fixture
def create_test_position():
    """创建测试持仓的工厂函数"""
    def _create(code="000001.SZ", volume=1000,
                 cost=Decimal("10.0"), price=Decimal("10.5")):
        pos = Position()
        pos.code = code
        pos.volume = volume
        pos.cost = cost
        pos.price = price
        pos.frozen_volume = 0
        pos.frozen_money = Decimal("0.0")
        pos.fee = Decimal("10.0")
        return pos

    return _create
