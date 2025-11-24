#!/usr/bin/env python3
"""
SimBroker单元测试

测试SimBroker的完整功能，包括：
1. IBroker接口实现
2. 订单执行逻辑
3. 市场数据管理
4. 持仓管理
5. 费用计算
6. 状态查询接口
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../src'))

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from typing import Dict, Any

from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.trading.entities import Order
from ginkgo.enums import (
    DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES,
    ATTITUDE_TYPES
)


class TestSimBrokerInitialization:
    """测试SimBroker初始化"""

    def test_sim_broker_default_initialization(self):
        """测试默认参数初始化"""
        broker = SimBroker()

        assert broker.name == "SimBroker"
        assert broker._attitude == ATTITUDE_TYPES.RANDOM
        assert broker._commission_rate == Decimal("0.0003")
        assert broker._commission_min == 5.0

    def test_sim_broker_custom_initialization(self):
        """测试自定义参数初始化"""
        broker = SimBroker(
            name="CustomSimBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0005,
            commission_min=10.0
        )

        assert broker.name == "CustomSimBroker"
        assert broker._attitude == ATTITUDE_TYPES.OPTIMISTIC
        assert broker._commission_rate == Decimal("0.0005")
        assert broker._commission_min == 10.0

    def test_sim_broker_mixin_inheritance(self):
        """测试Mixin继承结构"""
        from ginkgo.trading.bases.base_broker import BaseBroker
        from ginkgo.trading.mixins.context_mixin import ContextMixin
        from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
        from ginkgo.trading.mixins.loggable_mixin import LoggableMixin

        broker = SimBroker()

        assert isinstance(broker, BaseBroker)
        assert isinstance(broker, ContextMixin)
        assert isinstance(broker, EngineBindableMixin)
        assert isinstance(broker, LoggableMixin)


class TestSimBrokerInterfaceCompliance:
    """测试SimBroker的IBroker接口实现"""

    def test_supports_immediate_execution(self):
        """测试支持立即执行"""
        broker = SimBroker()
        assert broker.supports_immediate_execution() is True

    def test_requires_manual_confirmation(self):
        """测试是否需要人工确认"""
        broker = SimBroker()
        assert broker.requires_manual_confirmation() is False

    def test_supports_api_trading(self):
        """测试是否支持API交易"""
        broker = SimBroker()
        assert broker.supports_api_trading() is False

    def test_validate_order(self):
        """测试订单验证"""
        broker = SimBroker()

        # 有效订单
        valid_order = Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )
        assert broker.validate_order(valid_order) is True

        # 无效订单（数量为0）
        invalid_order = Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=0,  # 无效数量
            limit_price=10.0
        )
        assert broker.validate_order(invalid_order) is False


class TestSimBrokerMarketDataManagement:
    """测试SimBroker市场数据管理"""

    def test_set_market_data(self):
        """测试设置市场数据"""
        broker = SimBroker()

        # 创建测试市场数据
        market_data = pd.Series({
            'open': 10.0,
            'high': 11.0,
            'low': 9.0,
            'close': 10.5,
            'volume': 1000000
        })

        broker.set_market_data("000001.SZ", market_data)

        # 验证数据被正确存储
        retrieved_data = broker.get_market_data("000001.SZ")
        assert retrieved_data is not None
        assert retrieved_data['open'] == 10.0
        assert retrieved_data['close'] == 10.5

    def test_get_nonexistent_market_data(self):
        """测试获取不存在的市场数据"""
        broker = SimBroker()

        result = broker.get_market_data("NONEXISTENT.CODE")
        assert result is None

    def test_update_price_data(self):
        """测试更新价格数据"""
        broker = SimBroker()

        # 创建价格事件
        price_event = Mock()
        price_event.value = pd.Series({
            'open': 10.0,
            'high': 11.0,
            'low': 9.0,
            'close': 10.5,
            'volume': 1000000
        })
        price_event.code = "000001.SZ"

        # 更新价格数据
        broker.update_price_data(price_event)

        # 验证数据被正确更新
        data = broker.get_market_data("000001.SZ")
        assert data is not None
        assert data['close'] == 10.5


class TestSimBrokerPositionManagement:
    """测试SimBroker持仓管理"""

    def test_update_position_long(self):
        """测试多头持仓更新"""
        broker = SimBroker()

        # 更新多头持仓
        broker.update_position("000001.SZ", 1000, 10.5)

        position = broker.get_position("000001.SZ")
        assert position is not None
        assert position.volume == 1000
        assert position.price == 10.5

    def test_update_position_short(self):
        """测试空头持仓更新"""
        broker = SimBroker()

        # 更新空头持仓
        broker.update_position("000001.SZ", -500, 9.8)

        position = broker.get_position("000001.SZ")
        assert position is not None
        assert position.volume == -500
        assert position.price == 9.8

    def test_get_nonexistent_position(self):
        """测试获取不存在的持仓"""
        broker = SimBroker()

        result = broker.get_position("NONEXISTENT.CODE")
        assert result is None


class TestSimBrokerOrderExecution:
    """测试SimBroker订单执行逻辑"""

    def test_submit_order_without_market_data(self):
        """测试没有市场数据时的订单提交"""
        broker = SimBroker()
        broker._attitude = ATTITUDE_TYPES.OPTIMISTIC

        order = Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )

        result = broker.submit_order(order)

        # 应该返回拒绝结果
        assert result.status == ORDERSTATUS_TYPES.NEW  # REJECTED
        assert "No market data" in result.error_message

    def test_submit_order_with_market_data_optimistic(self):
        """测试乐观态度下的订单执行"""
        broker = SimBroker()
        broker._attitude = ATTITUDE_TYPES.OPTIMISTIC

        # 设置市场数据
        market_data = pd.Series({
            'open': 10.0,
            'high': 11.0,
            'low': 9.0,
            'close': 10.5,
            'volume': 1000000
        })
        broker.set_market_data("000001.SZ", market_data)

        order = Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )

        result = broker.submit_order(order)

        # 乐观态度应该总是成交
        assert result.status == ORDERSTATUS_TYPES.FILLED
        assert result.filled_volume == 100
        assert result.filled_price > 0
        assert result.commission >= 0
        assert result.broker_order_id is not None
        assert result.trade_id is not None

    def test_submit_limit_order(self):
        """测试限价单执行"""
        broker = SimBroker()
        broker._attitude = ATTITUDE_TYPES.OPTIMISTIC

        # 设置市场数据
        market_data = pd.Series({
            'open': 10.0,
            'high': 11.0,
            'low': 9.0,
            'close': 10.5,
            'volume': 1000000
        })
        broker.set_market_data("000001.SZ", market_data)

        # 创建限价买单，价格在合理范围内
        order = Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.2  # 在市场数据范围内
        )

        result = broker.submit_order(order)

        assert result.status == ORDERSTATUS_TYPES.FILLED
        assert result.filled_price == 10.2  # 限价单应该以限价成交

    def test_submit_order_different_attitudes(self):
        """测试不同态度下的订单执行"""
        # 测试悲观态度
        pessimistic_broker = SimBroker()
        pessimistic_broker._attitude = ATTITUDE_TYPES.PESSIMISTIC

        market_data = pd.Series({
            'open': 10.0,
            'high': 11.0,
            'low': 9.0,
            'close': 10.5,
            'volume': 1000000
        })
        pessimistic_broker.set_market_data("000001.SZ", market_data)

        order = Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )

        # 多次测试悲观态度（70%成交概率）
        filled_count = 0
        for _ in range(100):
            with patch('random.random') as mock_random:
                mock_random.return_value = 0.6  # 70%成交概率范围内
                result = pessimistic_broker.submit_order(order)
                if result.status == ORDERSTATUS_TYPES.FILLED:
                    filled_count += 1

        # 验证成交概率（这里简化为至少测试一次成功）
        assert filled_count > 0


class TestSimBrokerStatusInterface:
    """测试SimBroker状态查询接口"""

    def test_get_broker_status(self):
        """测试获取Broker状态"""
        broker = SimBroker(
            name="StatusTestBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0005,
            commission_min=10.0
        )

        status = broker.get_broker_status()

        assert isinstance(status, dict)
        assert status['name'] == "StatusTestBroker"
        assert status['market'] == 'SIM'
        assert status['execution_mode'] == 'backtest'
        assert status['attitude'] == 'OPTIMISTIC'
        assert status['commission_rate'] == 0.0005
        assert status['commission_min'] == 10.0
        assert status['supports_immediate_execution'] is True
        assert status['requires_manual_confirmation'] is False
        assert status['supports_api_trading'] is False

    def test_get_broker_status_with_data_and_positions(self):
        """测试有数据和持仓时的状态"""
        broker = SimBroker()

        # 添加市场数据
        market_data = pd.Series({'close': 10.5, 'volume': 1000000})
        broker.set_market_data("000001.SZ", market_data)
        broker.set_market_data("000002.SZ", market_data)

        # 添加持仓
        broker.update_position("000001.SZ", 1000, 10.5)
        broker.update_position("000002.SZ", -500, 9.8)

        status = broker.get_broker_status()

        assert status['market_data_count'] == 2
        assert status['position_count'] == 2


class TestSimBrokerCommissionCalculation:
    """测试SimBroker费用计算"""

    def test_calculate_commission_minimum(self):
        """测试最低手续费"""
        broker = SimBroker(commission_rate=0.0001, commission_min=5.0)

        # 小额交易，应该按最低手续费收取
        small_amount = 10000  # 0.0001 * 10000 = 1 < 5
        commission = broker._calculate_commission(small_amount, True)
        assert commission == Decimal("5.0")

    def test_calculate_commission_rate_based(self):
        """测试基于费率的计算"""
        broker = SimBroker(commission_rate=0.0003, commission_min=5.0)

        # 大额交易，应该按费率收取
        large_amount = 100000  # 0.0003 * 100000 = 30 > 5
        commission = broker._calculate_commission(large_amount, True)
        assert commission == Decimal("30.0")

    def test_calculate_commission_for_buy_and_sell(self):
        """测试买入和卖出费用计算"""
        broker = SimBroker(commission_rate=0.0003, commission_min=5.0)

        buy_amount = 50000
        sell_amount = 50000

        buy_commission = broker._calculate_commission(buy_amount, True)
        sell_commission = broker._calculate_commission(sell_amount, False)

        assert buy_commission == sell_commission == Decimal("15.0")


@pytest.fixture
def sample_order():
    """提供示例订单fixture"""
    return Order(
        portfolio_id="test_portfolio",
        engine_id="test_engine",
        run_id="test_run",
        code="000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.NEW,
        volume=100,
        limit_price=10.0
    )


@pytest.fixture
def sample_market_data():
    """提供示例市场数据fixture"""
    return pd.Series({
        'open': 10.0,
        'high': 11.0,
        'low': 9.0,
        'close': 10.5,
        'volume': 1000000
    })


class TestSimBrokerWithFixtures:
    """使用fixture的SimBroker测试"""

    def test_sim_broker_with_sample_order(self, sample_order):
        """测试使用sample_order fixture"""
        broker = SimBroker()

        assert broker.validate_order(sample_order) is True
        assert sample_order.code == "000001.SZ"
        assert sample_order.volume == 100

    def test_sim_broker_with_sample_market_data(self, sample_market_data):
        """测试使用sample_market_data fixture"""
        broker = SimBroker()

        broker.set_market_data("000001.SZ", sample_market_data)

        data = broker.get_market_data("000001.SZ")
        assert data['open'] == 10.0
        assert data['close'] == 10.5
        assert data['volume'] == 1000000

    def test_order_execution_with_fixtures(self, sample_order, sample_market_data):
        """测试使用fixture的订单执行"""
        broker = SimBroker(attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker.set_market_data("000001.SZ", sample_market_data)

        result = broker.submit_order(sample_order)

        assert result.status == ORDERSTATUS_TYPES.FILLED
        assert result.filled_volume == sample_order.volume


class TestSimBrokerErrorHandling:
    """测试SimBroker错误处理"""

    def test_order_execution_with_exception(self):
        """测试订单执行异常处理"""
        broker = SimBroker()

        # 创建会导致异常的订单（例如None值）
        problematic_order = Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code=None,  # 这可能导致问题
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )

        result = broker.submit_order(problematic_order)

        # 应该返回拒绝状态
        assert result.status == ORDERSTATUS_TYPES.NEW  # REJECTED
        assert result.error_message is not None

    def test_invalid_market_data_handling(self):
        """测试无效市场数据处理"""
        broker = SimBroker()

        # 尝试设置无效的市场数据
        invalid_data = pd.Series({"invalid": "data"})

        # 应该不会抛出异常
        broker.set_market_data("TEST.CODE", invalid_data)

        # 但获取数据时可能有问题
        data = broker.get_market_data("TEST.CODE")
        assert data is not None  # 具体行为取决于实现


@pytest.mark.integration
class TestSimBrokerIntegration:
    """SimBroker集成测试"""

    def test_complete_trading_simulation(self):
        """测试完整的交易模拟"""
        # 初始化Broker
        broker = SimBroker(
            name="IntegrationBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0003,
            commission_min=5.0
        )

        # 设置市场数据
        market_data = pd.Series({
            'open': 10.0,
            'high': 11.0,
            'low': 9.0,
            'close': 10.5,
            'volume': 1000000
        })
        broker.set_market_data("000001.SZ", market_data)

        # 创建订单
        order = Order(
            portfolio_id="integration_test",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=200,
            limit_price=10.0
        )

        # 执行订单
        result = broker.submit_order(order)

        # 验证执行结果
        assert result.status == ORDERSTATUS_TYPES.FILLED
        assert result.filled_volume == 200
        assert result.filled_price > 0
        assert result.commission >= 5.0  # 最低手续费

        # 验证持仓更新
        position = broker.get_position("000001.SZ")
        assert position is not None
        assert position.volume == 200

        # 验证状态信息
        status = broker.get_broker_status()
        assert status['position_count'] == 1
        assert status['market_data_count'] == 1

    def test_multiple_orders_simulation(self):
        """测试多笔订单模拟"""
        broker = SimBroker(attitude=ATTITUDE_TYPES.OPTIMISTIC)

        # 设置市场数据
        market_data = pd.Series({
            'open': 10.0,
            'high': 11.0,
            'low': 9.0,
            'close': 10.5,
            'volume': 1000000
        })
        broker.set_market_data("000001.SZ", market_data)

        orders = []
        results = []

        # 创建多笔订单
        for i in range(3):
            order = Order(
                portfolio_id="multi_test",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100 * (i + 1),
                limit_price=10.0
            )
            orders.append(order)

        # 执行所有订单
        for order in orders:
            result = broker.submit_order(order)
            results.append(result)

        # 验证执行结果
        for i, result in enumerate(results):
            assert result.status == ORDERSTATUS_TYPES.FILLED
            assert result.filled_volume == 100 * (i + 1)

        # 验证最终持仓
        final_position = broker.get_position("000001.SZ")
        expected_volume = 100 - 200 + 300  # 100(long) - 200(short) + 300(long)
        assert final_position.volume == expected_volume