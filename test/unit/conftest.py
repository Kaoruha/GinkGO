"""
pytest 共享 fixtures 配置

为 unit tests 提供可复用的测试资源和配置。
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

# 导入 Ginkgo 核心组件
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES
)


# ===== 时间相关 Fixtures =====

@pytest.fixture
def test_timestamp():
    """标准测试时间戳"""
    return datetime(2024, 1, 15, 9, 30, 0)


@pytest.fixture
def test_date():
    """标准测试日期"""
    return datetime(2024, 1, 15).date()


@pytest.fixture
def test_time_range():
    """测试时间范围"""
    return (
        datetime(2024, 1, 1, 0, 0, 0),
        datetime(2024, 12, 31, 23, 59, 59)
    )


# ===== 股票代码 Fixtures =====

@pytest.fixture
def sample_stock_code():
    """标准测试股票代码"""
    return "000001.SZ"


@pytest.fixture
def sample_stock_codes():
    """多个测试股票代码"""
    return ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH"]


# ===== 核心实体 Fixtures =====

@pytest.fixture
def test_bar_data(sample_stock_code, test_timestamp):
    """标准测试Bar数据"""
    return {
        "code": sample_stock_code,
        "timestamp": test_timestamp,
        "open": Decimal("10.0"),
        "high": Decimal("10.8"),
        "low": Decimal("9.8"),
        "close": Decimal("10.5"),
        "volume": 1000000,
        "amount": Decimal("10500000.0"),
        "frequency": FREQUENCY_TYPES.DAY
    }


@pytest.fixture
def test_bar(test_bar_data):
    """创建标准测试Bar对象"""
    return Bar(**test_bar_data)


@pytest.fixture
def test_order_data(sample_stock_code, test_timestamp):
    """标准测试订单数据"""
    return {
        "portfolio_id": "test_portfolio",
        "engine_id": "test_engine",
        "run_id": "test_run",
        "code": sample_stock_code,
        "direction": DIRECTION_TYPES.LONG,
        "order_type": ORDER_TYPES.LIMITORDER,
        "status": ORDERSTATUS_TYPES.NEW,
        "volume": 1000,
        "limit_price": Decimal("10.50"),
        "timestamp": test_timestamp
    }


@pytest.fixture
def test_order(test_order_data):
    """创建标准测试订单对象"""
    return Order(**test_order_data)


@pytest.fixture
def test_position_data(sample_stock_code):
    """标准测试持仓数据"""
    return {
        "code": sample_stock_code,
        "volume": 1000,
        "frozen_volume": 0,
        "cost": Decimal("10.0"),
        "price": Decimal("10.5"),
        "fee": Decimal("10.0"),
        "worth": Decimal("10500.0"),
        "profit": Decimal("490.0")
    }


@pytest.fixture
def test_position(test_position_data):
    """创建标准测试持仓对象"""
    pos = Position()
    pos.code = test_position_data["code"]
    pos.volume = test_position_data["volume"]
    pos.frozen_volume = test_position_data["frozen_volume"]
    pos.cost = test_position_data["cost"]
    pos.price = test_position_data["price"]
    pos.fee = test_position_data["fee"]
    return pos


@pytest.fixture
def test_signal_data(sample_stock_code, test_timestamp):
    """标准测试信号数据"""
    return {
        "code": sample_stock_code,
        "direction": DIRECTION_TYPES.LONG,
        "timestamp": test_timestamp,
        "strength": 0.8,
        "reason": "测试信号"
    }


@pytest.fixture
def test_signal(test_signal_data):
    """创建标准测试信号对象"""
    signal = Signal()
    signal.code = test_signal_data["code"]
    signal.direction = test_signal_data["direction"]
    signal.timestamp = test_signal_data["timestamp"]
    signal.strength = test_signal_data["strength"]
    signal.reason = test_signal_data["reason"]
    return signal


@pytest.fixture
def price_update_event_data(sample_stock_code, test_timestamp):
    """价格更新事件数据"""
    return {
        "code": sample_stock_code,
        "open": Decimal("10.0"),
        "high": Decimal("10.8"),
        "low": Decimal("9.8"),
        "close": Decimal("10.5"),
        "volume": 100000,
        "timestamp": test_timestamp
    }


@pytest.fixture
def price_update_event(price_update_event_data):
    """创建价格更新事件对象"""
    event = EventPriceUpdate()
    event.code = price_update_event_data["code"]
    event.open = price_update_event_data["open"]
    event.high = price_update_event_data["high"]
    event.low = price_update_event_data["low"]
    event.close = price_update_event_data["close"]
    event.volume = price_update_event_data["volume"]
    event.timestamp = price_update_event_data["timestamp"]
    return event


# ===== 投资组合信息 Fixtures =====

@pytest.fixture
def base_portfolio_info():
    """基础投资组合信息"""
    return {
        "uuid": "test_portfolio",
        "portfolio_id": "test_portfolio",
        "cash": Decimal("100000.0"),
        "frozen": Decimal("0.0"),
        "total_value": Decimal("100000.0"),
        "positions": {}
    }


@pytest.fixture
def portfolio_with_position(base_portfolio_info, sample_stock_code):
    """带持仓的投资组合信息"""
    base_portfolio_info["positions"][sample_stock_code] = Mock(
        code=sample_stock_code,
        volume=1000,
        cost=Decimal("10.0"),
        price=Decimal("10.5")
    )
    base_portfolio_info["total_value"] = Decimal("110000.0")
    return base_portfolio_info


@pytest.fixture
def losing_portfolio_info(sample_stock_code):
    """亏损投资组合信息"""
    return {
        "uuid": "losing_portfolio",
        "cash": Decimal("100000.0"),
        "total_value": Decimal("98500.0"),
        "positions": {
            sample_stock_code: Mock(
                code=sample_stock_code,
                volume=1000,
                cost=Decimal("10.0"),
                price=Decimal("9.5")  # 亏损5%
            )
        }
    }


@pytest.fixture
def profitable_portfolio_info(sample_stock_code):
    """盈利投资组合信息"""
    return {
        "uuid": "profitable_portfolio",
        "cash": Decimal("100000.0"),
        "total_value": Decimal("115000.0"),
        "positions": {
            sample_stock_code: Mock(
                code=sample_stock_code,
                volume=1000,
                cost=Decimal("10.0"),
                price=Decimal("11.5")  # 盈利15%
            )
        }
    }


# ===== Mock 对象 Fixtures =====

@pytest.fixture
def mock_strategy():
    """创建模拟策略对象"""
    strategy = Mock()
    strategy.strategy_id = "test_strategy"
    strategy.name = "TestStrategy"
    strategy.cal = Mock(return_value=[])
    return strategy


@pytest.fixture
def mock_sizer():
    """创建模拟Sizer对象"""
    sizer = Mock()
    sizer.name = "TestSizer"
    sizer.volume = 100
    sizer.cal = Mock(return_value=None)
    return sizer


@pytest.fixture
def mock_risk_manager():
    """创建模拟风控管理器"""
    risk_manager = Mock()
    risk_manager.name = "TestRiskManager"
    risk_manager.cal = Mock(side_effect=lambda info, order: order)
    risk_manager.generate_signals = Mock(return_value=[])
    return risk_manager


@pytest.fixture
def mock_selector():
    """创建模拟选择器"""
    selector = Mock()
    selector.name = "TestSelector"
    selector.cal = Mock(return_value=["000001.SZ", "000002.SZ"])
    return selector


# ===== 测试数据生成器 Fixtures =====

@pytest.fixture
def bar_sequence_data(sample_stock_code):
    """生成连续的Bar数据序列"""
    base_price = Decimal("10.0")
    bars = []
    for i in range(10):
        bar_data = {
            "code": sample_stock_code,
            "timestamp": datetime(2024, 1, i+1, 9, 30, 0),
            "open": base_price + Decimal(str(i * 0.1)),
            "high": base_price + Decimal(str(i * 0.1 + 0.5)),
            "low": base_price + Decimal(str(i * 0.1 - 0.3)),
            "close": base_price + Decimal(str(i * 0.1 + 0.2)),
            "volume": 1000000 + i * 10000,
            "frequency": FREQUENCY_TYPES.DAY
        }
        bars.append(bar_data)
    return bars


@pytest.fixture
def price_scenarios():
    """价格场景测试数据"""
    return {
        "bull_market": [
            Decimal("10.0"), Decimal("10.2"), Decimal("10.5"),
            Decimal("10.8"), Decimal("11.0"), Decimal("11.3")
        ],
        "bear_market": [
            Decimal("11.0"), Decimal("10.8"), Decimal("10.5"),
            Decimal("10.2"), Decimal("10.0"), Decimal("9.8")
        ],
        "volatile_market": [
            Decimal("10.0"), Decimal("10.5"), Decimal("9.8"),
            Decimal("10.8"), Decimal("9.5"), Decimal("11.0")
        ],
        "sideways_market": [
            Decimal("10.0"), Decimal("10.1"), Decimal("9.9"),
            Decimal("10.0"), Decimal("10.1"), Decimal("9.9")
        ]
    }


# ===== 参数化测试数据 =====

@pytest.fixture
def order_volume_test_cases():
    """订单数量测试用例"""
    return [
        (100, 100, 10.0, 1100.0),  # volume, expected, price, cost
        (200, 200, 10.0, 2200.0),
        (0, 0, 10.0, 0.0),
        (1000, 1000, 10.0, 11000.0)
    ]


@pytest.fixture
def position_ratio_test_cases():
    """持仓比例测试用例"""
    return [
        (0.1, 10000.0, 10.0, 100),  # ratio, cash, price, expected_volume
        (0.2, 10000.0, 10.0, 200),
        (0.5, 10000.0, 10.0, 500),
        (1.0, 10000.0, 10.0, 909)  # 考虑10%费用
    ]


@pytest.fixture
def loss_limit_test_cases():
    """止损限制测试用例"""
    return [
        (10.0, 9.0, 10.0, True),  # limit, price, cost, should_trigger
        (10.0, 8.5, 10.0, True),
        (10.0, 9.5, 10.0, False),
        (5.0, 9.0, 10.0, True)
    ]


# ===== 辅助函数 Fixtures =====

@pytest.fixture
def assert_financial_precision():
    """金融精度断言函数工厂"""
    def _assert(actual, expected, places=4, msg=None):
        """断言金融数据精度"""
        diff = abs(actual - expected)
        tolerance = Decimal("0.1") ** places
        assert diff <= tolerance, (
            f"{msg or ''} 金融精度不匹配: {actual} != {expected} "
            f"(差异: {diff}, 容差: {tolerance})"
        )
    return _assert


@pytest.fixture
def create_test_order():
    """创建测试订单的工厂函数"""
    def _create(code="000001.SZ", volume=1000, price=Decimal("10.0"),
                direction=DIRECTION_TYPES.LONG):
        order = Order()
        order.code = code
        order.volume = volume
        order.limit_price = price
        order.direction = direction
        order.status = ORDERSTATUS_TYPES.NEW
        order.order_type = ORDER_TYPES.LIMITORDER
        return order
    return _create


@pytest.fixture
def create_test_position():
    """创建测试持仓的工厂函数"""
    def _create(code="000001.SZ", volume=1000, cost=Decimal("10.0"),
                 price=Decimal("10.5")):
        pos = Position()
        pos.code = code
        pos.volume = volume
        pos.cost = cost
        pos.price = price
        return pos
    return _create


# ===== 市场数据 Fixtures =====

@pytest.fixture
def market_data_base():
    """基础市场数据"""
    return {
        "index": {
            "000001.SH": Decimal("3200.5"),
            "399001.SZ": Decimal("10800.8")
        },
        "stocks": {
            "000001.SZ": {"price": Decimal("10.5"), "volume": 1000000},
            "000002.SZ": {"price": Decimal("20.8"), "volume": 500000},
            "600000.SH": {"price": Decimal("15.2"), "volume": 2000000}
        },
        "timestamp": datetime(2024, 1, 15, 9, 30, 0)
    }


@pytest.fixture
def market_data_bull(market_data_base):
    """牛市市场数据"""
    data = market_data_base.copy()
    data["trend"] = "up"
    data["stocks"]["000001.SZ"]["price"] = Decimal("11.5")
    data["stocks"]["000002.SZ"]["price"] = Decimal("22.0")
    return data


@pytest.fixture
def market_data_bear(market_data_base):
    """熊市市场数据"""
    data = market_data_base.copy()
    data["trend"] = "down"
    data["stocks"]["000001.SZ"]["price"] = Decimal("9.5")
    data["stocks"]["000002.SZ"]["price"] = Decimal("19.5")
    return data
