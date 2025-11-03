"""
Order实体基础测试 - 仅包含基本构造函数测试

这是一个临时的测试文件，用于验证Order类的基本功能，
避免完整测试文件中的语法错误问题。
"""

import pytest
import datetime

from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


@pytest.mark.unit
class TestOrderConstruction:
    """1. Order构造函数测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        # 默认构造应该失败，因为需要必需参数
        with pytest.raises(Exception):
            Order()

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        test_time = datetime.datetime(2024, 1, 1, 10, 30, 0)

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.SHORT,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,
            volume=1000,
            limit_price=15.50,
            frozen_money=15500.0,
            timestamp=test_time,
            uuid="test-uuid-123"
        )

        # 验证核心字段
        assert order.portfolio_id == "test_portfolio"
        assert order.code == "000001.SZ"
        assert order.direction == DIRECTION_TYPES.SHORT
        assert order.uuid == "test-uuid-123"

    def test_base_class_inheritance(self):
        """测试Base类继承验证"""
        from ginkgo.trading.core.base import Base

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        assert isinstance(order, Base)
        assert hasattr(order, 'uuid')
        assert hasattr(order, 'component_type')

    def test_component_type_assignment(self):
        """测试组件类型分配"""
        from ginkgo.enums import COMPONENT_TYPES

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        assert order.component_type == COMPONENT_TYPES.ORDER

    def test_uuid_generation(self):
        """测试UUID生成"""
        # 测试自动生成UUID
        order1 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        order2 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证UUID唯一性
        assert order1.uuid != order2.uuid

        # 测试自定义UUID
        custom_uuid = "custom-order-uuid-123"
        order3 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            uuid=custom_uuid,
            timestamp="2023-01-01 10:00:00"
        )
        assert order3.uuid == custom_uuid
