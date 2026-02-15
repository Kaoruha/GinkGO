"""
Order类测试 - Refactored

使用pytest最佳实践重构的Order测试套件
包括fixtures共享、参数化测试和清晰的测试分组
"""
import pytest
import datetime
from decimal import Decimal

from ginkgo.trading.entities.order import Order
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    COMPONENT_TYPES
)


@pytest.mark.unit
class TestOrderConstruction:
    """1. 构造和初始化测试"""

    def test_full_parameter_constructor(self, sample_order_data):
        """测试完整参数构造"""
        order = Order(**sample_order_data)

        assert order.portfolio_id == "test_portfolio"
        assert order.code == "000001.SZ"
        assert order.direction == DIRECTION_TYPES.LONG
        assert order.uuid is not None

    def test_base_class_inheritance(self, sample_order_data):
        """测试Base类继承验证"""
        from ginkgo.trading.core.base import Base

        order = Order(**sample_order_data)
        assert isinstance(order, Base)
        assert hasattr(order, 'uuid')
        assert hasattr(order, 'component_type')

    def test_component_type_assignment(self, sample_order_data):
        """测试组件类型分配"""
        order = Order(**sample_order_data)
        assert order.component_type == COMPONENT_TYPES.ORDER

    def test_uuid_generation(self, sample_order_data):
        """测试UUID生成和唯一性"""
        order1 = Order(**sample_order_data)
        order2 = Order(**sample_order_data)

        assert order1.uuid != order2.uuid
        assert len(order1.uuid) > 0
        assert len(order2.uuid) > 0

    def test_custom_uuid(self, sample_order_data):
        """测试自定义UUID"""
        custom_uuid = "custom-order-uuid-123"
        sample_order_data['uuid'] = custom_uuid

        order = Order(**sample_order_data)
        assert order.uuid == custom_uuid

    @pytest.mark.parametrize("direction", [
        DIRECTION_TYPES.LONG,
        DIRECTION_TYPES.SHORT
    ])
    def test_direction_types(self, sample_order_data, direction):
        """测试交易方向类型"""
        sample_order_data['direction'] = direction
        order = Order(**sample_order_data)
        assert order.direction == direction

    @pytest.mark.parametrize("order_type", [
        ORDER_TYPES.MARKETORDER,
        ORDER_TYPES.LIMITORDER
    ])
    def test_order_types(self, sample_order_data, order_type):
        """测试订单类型"""
        sample_order_data['order_type'] = order_type
        order = Order(**sample_order_data)
        assert order.order_type == order_type


@pytest.mark.unit
class TestOrderProperties:
    """2. 属性访问测试"""

    def test_portfolio_id_validation(self, sample_order_data):
        """测试portfolio_id验证"""
        # 有效ID
        order = Order(**sample_order_data)
        assert order.portfolio_id == "test_portfolio"
        assert isinstance(order.portfolio_id, str)

        # 无效类型
        sample_order_data['portfolio_id'] = 123
        with pytest.raises(Exception):
            Order(**sample_order_data)

        # 空字符串
        sample_order_data['portfolio_id'] = ""
        with pytest.raises(Exception):
            Order(**sample_order_data)

    def test_code_validation(self, sample_order_data):
        """测试code验证"""
        order = Order(**sample_order_data)
        assert order.code == "000001.SZ"
        assert isinstance(order.code, str)

    def test_volume_validation(self, sample_order_data):
        """测试volume验证"""
        # 有效整数值
        sample_order_data['volume'] = 1000
        order = Order(**sample_order_data)
        assert order.volume == 1000
        assert isinstance(order.volume, int)

        # 浮点数转换
        sample_order_data['volume'] = 100.5
        order = Order(**sample_order_data)
        assert order.volume == 100

        # 负数被拒绝
        sample_order_data['volume'] = -100
        with pytest.raises(Exception):
            Order(**sample_order_data)

    def test_limit_price_validation(self, sample_order_data):
        """测试limit_price验证"""
        # 正常价格
        order = Order(**sample_order_data)
        assert order.limit_price == Decimal('15.50')
        assert isinstance(order.limit_price, Decimal)

        # 负价格（期货场景）
        sample_order_data['limit_price'] = -15.50
        order = Order(**sample_order_data)
        assert order.limit_price == Decimal('-15.50')

        # 零价格（市价单）
        sample_order_data['limit_price'] = 0
        order = Order(**sample_order_data)
        assert order.limit_price == Decimal('0')

    def test_decimal_fields_type(self, sample_order_data):
        """测试Decimal字段类型"""
        order = Order(**sample_order_data)

        assert isinstance(order.limit_price, Decimal)
        assert isinstance(order.frozen_money, Decimal)
        assert isinstance(order.transaction_price, Decimal)
        assert isinstance(order.fee, Decimal)


@pytest.mark.unit
class TestOrderStatusManagement:
    """3. 订单状态管理测试"""

    def test_initial_status(self, sample_order_data):
        """测试初始状态"""
        sample_order_data['status'] = ORDERSTATUS_TYPES.NEW
        order = Order(**sample_order_data)
        assert order.status == ORDERSTATUS_TYPES.NEW

    @pytest.mark.parametrize("initial_status,action,final_status", [
        (ORDERSTATUS_TYPES.NEW, 'submit', ORDERSTATUS_TYPES.SUBMITTED),
        (ORDERSTATUS_TYPES.SUBMITTED, 'fill', ORDERSTATUS_TYPES.FILLED),
        (ORDERSTATUS_TYPES.NEW, 'cancel', ORDERSTATUS_TYPES.CANCELED),
    ])
    def test_status_transitions(self, sample_order_data, initial_status, action, final_status):
        """测试状态转换"""
        sample_order_data['status'] = initial_status
        order = Order(**sample_order_data)

        # 执行状态转换
        if action == 'submit':
            order.submit()
        elif action == 'fill':
            order.fill()
        elif action == 'cancel':
            order.cancel()

        assert order.status == final_status

    def test_status_readonly(self, sample_order_data):
        """测试status只读属性"""
        order = Order(**sample_order_data)

        # 尝试直接修改status应该失败
        with pytest.raises(AttributeError):
            order.status = ORDERSTATUS_TYPES.FILLED

    @pytest.mark.parametrize("status", [
        ORDERSTATUS_TYPES.NEW,
        ORDERSTATUS_TYPES.SUBMITTED,
        ORDERSTATUS_TYPES.PARTIAL_FILLED,
        ORDERSTATUS_TYPES.FILLED,
        ORDERSTATUS_TYPES.CANCELED
    ])
    def test_all_status_types(self, sample_order_data, status):
        """测试所有状态类型"""
        sample_order_data['status'] = status
        order = Order(**sample_order_data)
        assert order.status == status


@pytest.mark.unit
class TestOrderTradeExecution:
    """4. 交易执行状态测试"""

    def test_partial_fill(self, sample_order_data):
        """测试部分成交"""
        sample_order_data.update({
            'order_type': ORDER_TYPES.LIMITORDER,
            'status': ORDERSTATUS_TYPES.SUBMITTED,
            'volume': 1000
        })
        order = Order(**sample_order_data)

        # 部分成交
        order.partial_fill(600, Decimal('15.10'), Decimal('5.0'))

        assert order.volume == 1000
        assert order.transaction_volume == 600
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        assert order.transaction_price == Decimal('15.10')
        assert order.fee == Decimal('5.0')

    def test_complete_fill(self, sample_order_data):
        """测试完全成交"""
        sample_order_data.update({
            'order_type': ORDER_TYPES.LIMITORDER,
            'status': ORDERSTATUS_TYPES.SUBMITTED,
            'volume': 1000
        })
        order = Order(**sample_order_data)

        # 完全成交
        order.fill()

        assert order.status == ORDERSTATUS_TYPES.FILLED
        assert order.transaction_volume == order.volume
        assert order.remain == Decimal('0')

    @pytest.mark.parametrize("init_vol,fill1,fill2,fill3,expected", [
        (1000, 300, 400, 300, 1000),  # 完全成交
        (1000, 200, 300, 200, 700),   # 部分成交
        (1000, 500, 500, 0, 1000),    # 两次成交
    ])
    def test_multiple_fills(self, sample_order_data, init_vol, fill1, fill2, fill3, expected):
        """测试多次成交"""
        sample_order_data.update({
            'order_type': ORDER_TYPES.LIMITORDER,
            'status': ORDERSTATUS_TYPES.SUBMITTED,
            'volume': init_vol
        })
        order = Order(**sample_order_data)

        # 多次成交
        if fill1 > 0:
            order.partial_fill(fill1, Decimal('15.0'), Decimal('2.5'))
        if fill2 > 0:
            order.partial_fill(fill2, Decimal('15.1'), Decimal('3.0'))
        if fill3 > 0:
            order.partial_fill(fill3, Decimal('15.2'), Decimal('1.5'))

        assert order.transaction_volume == expected

    def test_overfill_prevention(self, sample_order_data):
        """测试超额成交预防"""
        sample_order_data.update({
            'order_type': ORDER_TYPES.LIMITORDER,
            'status': ORDERSTATUS_TYPES.SUBMITTED,
            'volume': 1000
        })
        order = Order(**sample_order_data)

        # 部分成交600
        order.partial_fill(600, Decimal('15.0'), Decimal('2.0'))

        # 尝试超额成交应该被拒绝
        with pytest.raises(ValueError, match="Overfill detected"):
            order.partial_fill(500, Decimal('15.1'), Decimal('1.0'))

        # 验证状态未被破坏
        assert order.transaction_volume == 600
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

    def test_fee_accumulation(self, sample_order_data):
        """测试费用累积"""
        sample_order_data.update({
            'order_type': ORDER_TYPES.LIMITORDER,
            'status': ORDERSTATUS_TYPES.SUBMITTED,
            'volume': 1000
        })
        order = Order(**sample_order_data)

        # 初始费用为0
        assert order.fee == Decimal('0')

        # 多次成交累积费用
        order.partial_fill(300, Decimal('15.0'), Decimal('2.5'))
        assert order.fee == Decimal('2.5')

        order.partial_fill(400, Decimal('15.1'), Decimal('3.75'))
        assert order.fee == Decimal('6.25')

        order.partial_fill(300, Decimal('15.2'), Decimal('1.25'))
        assert order.fee == Decimal('7.5')


@pytest.mark.unit
class TestOrderValidation:
    """5. 订单验证测试"""

    @pytest.mark.parametrize("price,expected", [
        (15.50, Decimal('15.50')),  # 正常价格
        (0.0, Decimal('0.0')),      # 零价格
        (-37.63, Decimal('-37.63')), # 负价格（期货）
        (123.456789, Decimal('123.456789')),  # 高精度
    ])
    def test_limit_price_range(self, sample_order_data, price, expected):
        """测试限价范围"""
        sample_order_data['limit_price'] = price
        order = Order(**sample_order_data)
        assert order.limit_price == expected

    @pytest.mark.parametrize("volume,should_pass", [
        (100, True),     # 正常数量
        (1000, True),    # 大数量
        (0, False),       # 零被拒绝
        (-100, False),    # 负数被拒绝
    ])
    def test_volume_range(self, sample_order_data, volume, should_pass):
        """测试数量范围"""
        sample_order_data['volume'] = volume
        if should_pass:
            order = Order(**sample_order_data)
            assert order.volume == volume
        else:
            with pytest.raises(Exception):
                Order(**sample_order_data)

    @pytest.mark.parametrize("direction", [
        DIRECTION_TYPES.LONG,
        DIRECTION_TYPES.SHORT
    ])
    def test_direction_enum(self, sample_order_data, direction):
        """测试方向枚举"""
        sample_order_data['direction'] = direction
        order = Order(**sample_order_data)
        assert order.direction == direction

    @pytest.mark.parametrize("order_type", [
        ORDER_TYPES.MARKETORDER,
        ORDER_TYPES.LIMITORDER
    ])
    def test_order_type_enum(self, sample_order_data, order_type):
        """测试订单类型枚举"""
        sample_order_data['order_type'] = order_type
        order = Order(**sample_order_data)
        assert order.order_type == order_type


@pytest.mark.unit
class TestOrderFrozenManagement:
    """6. 冻结金额和数量管理测试"""

    def test_buy_order_frozen_money(self, sample_order_data):
        """测试买单冻结金额"""
        sample_order_data.update({
            'direction': DIRECTION_TYPES.LONG,
            'order_type': ORDER_TYPES.LIMITORDER,
            'volume': 700,
            'limit_price': Decimal('15.50'),
            'frozen_money': Decimal('10500.0')
        })
        order = Order(**sample_order_data)

        assert order.frozen_money == Decimal('10500.0')
        assert order.frozen_volume == 0

    def test_sell_order_frozen_volume(self, sample_order_data):
        """测试卖单冻结数量"""
        sample_order_data.update({
            'direction': DIRECTION_TYPES.SHORT,
            'order_type': ORDER_TYPES.LIMITORDER,
            'volume': 500,
            'frozen_volume': 500
        })
        order = Order(**sample_order_data)

        assert order.frozen_volume == 500
        assert order.frozen_money == Decimal('0')

    @pytest.mark.parametrize("frozen_value,expected", [
        (15000, Decimal('15000')),    # int输入
        (15500.75, Decimal('15500.75')), # float输入
        ("16000", Decimal('16000')),  # string输入
    ])
    def test_frozen_money_conversion(self, sample_order_data, frozen_value, expected):
        """测试冻结金额类型转换"""
        sample_order_data['frozen_money'] = frozen_value
        order = Order(**sample_order_data)
        assert order.frozen_money == expected


@pytest.mark.unit
class TestOrderSourceManagement:
    """7. 数据源管理测试"""

    def test_default_source(self, sample_order_data):
        """测试默认数据源"""
        order = Order(**sample_order_data)
        assert order.source == SOURCE_TYPES.OTHER

    @pytest.mark.parametrize("source", [
        SOURCE_TYPES.SIM,
        SOURCE_TYPES.REALTIME,
        SOURCE_TYPES.BACKTEST,
        SOURCE_TYPES.STRATEGY,
        SOURCE_TYPES.DATABASE
    ])
    def test_various_sources(self, sample_order_data, source):
        """测试各种数据源"""
        sample_order_data['source'] = source
        order = Order(**sample_order_data)
        assert order.source == source

    def test_invalid_source(self, sample_order_data):
        """测试无效数据源"""
        sample_order_data['source'] = "INVALID_SOURCE"
        with pytest.raises(Exception):
            Order(**sample_order_data)


@pytest.mark.unit
class TestOrderDataSetting:
    """8. 数据设置测试"""

    def test_direct_parameter_setting(self, sample_order_data):
        """测试直接参数设置"""
        order = Order(**sample_order_data)

        # 重新设置
        order.set(
            "updated_portfolio",
            "updated_engine",
            "updated_run",
            "000002.SZ",
            DIRECTION_TYPES.SHORT,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.SUBMITTED,
            2000,
            Decimal('20.75')
        )

        assert order.portfolio_id == "updated_portfolio"
        assert order.code == "000002.SZ"
        assert order.volume == 2000
        assert order.direction == DIRECTION_TYPES.SHORT

    def test_pandas_series_setting(self, sample_order_data):
        """测试pandas.Series设置"""
        import pandas as pd

        order = Order(**sample_order_data)

        series_data = pd.Series({
            'portfolio_id': 'SERIES_PORTFOLIO',
            'engine_id': 'SERIES_ENGINE',
            'run_id': 'SERIES_RUN',
            'code': '000002.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'order_type': ORDER_TYPES.LIMITORDER.value,
            'status': ORDERSTATUS_TYPES.SUBMITTED.value,
            'volume': 2000,
            'limit_price': 25.75,
            'frozen_money': 51500.0
        })

        order.set(series_data)

        assert order.portfolio_id == 'SERIES_PORTFOLIO'
        assert order.code == '000002.SZ'
        assert order.volume == 2000


@pytest.mark.integration
class TestOrderDatabaseOperations:
    """9. 数据库操作测试"""

    def test_order_to_model(self, sample_order_data, ginkgo_config):
        """测试Order到Model的转换"""
        order = Order(**sample_order_data)
        model = order.to_model()

        assert model.portfolio_id == order.portfolio_id
        assert model.code == order.code
        assert model.volume == order.volume

    def test_order_from_model(self, sample_order_data, ginkgo_config):
        """测试Model到Order的转换"""
        order1 = Order(**sample_order_data)
        model = order1.to_model()
        order2 = Order.from_model(model)

        assert order2.portfolio_id == order1.portfolio_id
        assert order2.code == order1.code
        assert order2.volume == order1.volume
