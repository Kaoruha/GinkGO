"""
Order类TDD测试

通过TDD方式开发Order交易订单类的完整测试套件
涵盖订单生命周期管理、交易执行状态跟踪和量化交易扩展功能
"""
import pytest
import datetime
from typing import List

# 导入Order类和相关枚举
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestOrderConstruction:
    """1. 构造和初始化测试"""

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


@pytest.mark.unit
class TestOrderProperties:
    """2. 属性访问测试"""

    def test_portfolio_id_type_validation(self):
        """测试portfolio_id类型验证"""
        # 测试portfolio_id必须是str类型
        with pytest.raises(Exception):  # 构造函数包装了原始异常
            order = Order(
                portfolio_id=123,  # 应该是str不是int
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

        # 测试portfolio_id不能为空字符串
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="",  # 空字符串应该失败
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

    def test_engine_id_type_validation(self):
        """测试engine_id类型验证"""
        # 测试engine_id必须是str类型
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id=456,  # 应该是str不是int
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试engine_id不能为空字符串
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="",  # 空字符串应该失败
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

    def test_run_id_type_validation(self):
        """测试run_id类型验证"""
        # 测试run_id必须是str类型
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id=789,  # 应该是str不是int
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试run_id不能为空字符串
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="",  # 空字符串应该失败
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

    def test_code_type_validation(self):
        """测试code类型验证"""
        # 测试code必须是str类型
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code=123456,  # 应该是str不是int
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试code不能为空字符串
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="",  # 空字符串应该失败
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

    # 移除重复测试：direction枚举验证已在TestOrderEnumConstraints.test_direction_types_validation()中更详细实现

    # 移除重复测试：order_type枚举验证已在TestOrderEnumConstraints.test_order_types_validation()中更详细实现

    # 移除重复测试：status枚举验证已在TestOrderEnumConstraints.test_order_status_validation()中更详细实现

    def test_volume_type_validation(self):
        """测试volume类型验证"""
        # 测试volume必须是int类型
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume="invalid_volume",
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试volume不能为负值
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=-100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试volume浮点数会被转换为整数
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100.5,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        assert order.volume == 100  # 浮点数100.5被转换为整数100

    def test_limit_price_type_validation(self):
        """测试limit_price类型验证"""
        # 测试limit_price不能为字符串
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price="invalid_price",
                timestamp="2023-01-01 10:00:00"
            )

        # 根据实体实现，limit_price允许负值（支持期货等场景）
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=-15.50,  # 负价格被允许
            timestamp="2023-01-01 10:00:00"
        )
        from decimal import Decimal
        assert order.limit_price == Decimal('-15.50')

        # 测试limit_price不能为无效类型
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=None,
                timestamp="2023-01-01 10:00:00"
            )

    def test_decimal_fields_type_validation(self):
        """测试Decimal字段类型验证"""
        from decimal import Decimal

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

        # 验证财务字段都是Decimal类型（修正属性名）
        assert isinstance(order.limit_price, Decimal)
        assert isinstance(order.frozen_money, Decimal)  # 修正：frozen -> frozen_money
        assert isinstance(order.transaction_price, Decimal)
        assert isinstance(order.fee, Decimal)


@pytest.mark.unit
class TestOrderDataSetting:
    """3. 数据设置测试"""

    def test_set_parameter_type_validation(self):
        """测试set方法参数类型验证"""
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

        # 测试set方法的严格类型检查 - portfolio_id（需要提供所有必需参数）
        with pytest.raises(Exception):
            order.set(
                portfolio_id=123,  # 错误类型
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,  # 必需参数
                limit_price=15.50  # 必需参数
            )

        # 测试set方法的严格类型检查 - direction
        with pytest.raises(Exception):
            order.set(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction="invalid_direction",  # 错误类型
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,  # 必需参数
                limit_price=15.50  # 必需参数
            )

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        import pandas as pd
        from datetime import datetime

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

        # 创建测试Series数据（修正字段名）
        test_data = pd.Series({
            'portfolio_id': 'SERIES_PORTFOLIO',
            'engine_id': 'SERIES_ENGINE',
            'run_id': 'SERIES_RUN',
            'code': '000002.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'order_type': ORDER_TYPES.LIMITORDER.value,
            'status': ORDERSTATUS_TYPES.SUBMITTED.value,
            'volume': 2000,
            'limit_price': 25.75,
            'frozen_money': 51500.0,  # 修正：frozen -> frozen_money
            'transaction_price': 25.80,
            'transaction_volume': 1500,
            'remain': 12900.0,
            'fee': 10.25,
            'timestamp': datetime(2024, 6, 15, 14, 30, 0)
        })

        # 使用Series设置订单
        order.set(test_data)

        # 验证设置结果
        assert order.portfolio_id == 'SERIES_PORTFOLIO'
        assert order.code == '000002.SZ'
        assert order.direction == DIRECTION_TYPES.SHORT
        assert order.volume == 2000

    def test_singledispatch_method_routing(self):
        """测试多重分派路由"""
        import pandas as pd
        from datetime import datetime

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

        # 测试参数路由（需要提供所有必需参数）
        order.set(
            "PARAM_PORTFOLIO",
            "PARAM_ENGINE",
            "PARAM_RUN",
            "PARAM_CODE",
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.MARKETORDER,
            ORDERSTATUS_TYPES.NEW,
            100,  # volume
            15.50  # limit_price
        )
        assert order.portfolio_id == "PARAM_PORTFOLIO"

        # 测试Series路由（需要包含所有必需字段）
        series_data = pd.Series({
            'portfolio_id': 'SERIES_PORTFOLIO',
            'engine_id': 'SERIES_ENGINE',
            'run_id': 'SERIES_RUN',
            'code': 'SERIES_CODE',
            'direction': DIRECTION_TYPES.SHORT.value,
            'order_type': ORDER_TYPES.LIMITORDER.value,
            'status': ORDERSTATUS_TYPES.SUBMITTED.value,
            'volume': 200,  # 必需字段
            'limit_price': 20.0  # 必需字段
        })
        order.set(series_data)
        assert order.portfolio_id == "SERIES_PORTFOLIO"

        # 测试DataFrame路由（需要包含所有必需字段）
        df_data = pd.DataFrame([{
            'portfolio_id': 'DF_PORTFOLIO',
            'engine_id': 'DF_ENGINE',
            'run_id': 'DF_RUN',
            'code': 'DF_CODE',
            'direction': DIRECTION_TYPES.LONG.value,
            'order_type': ORDER_TYPES.MARKETORDER.value,
            'status': ORDERSTATUS_TYPES.NEW.value,
            'volume': 300,  # 必需字段
            'limit_price': 25.0  # 必需字段
        }])
        order.set(df_data)
        assert order.portfolio_id == "DF_PORTFOLIO"

    def test_partial_parameter_update(self):
        """测试部分参数更新"""
        from datetime import datetime

        # 创建初始订单
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

        # 记录初始值
        initial_code = order.code
        initial_volume = order.volume

        # 部分更新 - 只更新portfolio_id和engine_id
        order.set(
            "updated_portfolio",
            "updated_engine",
            "updated_run",
            "updated_code",
            DIRECTION_TYPES.SHORT,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.SUBMITTED,
            2000,  # 新的volume
            20.75  # 新的limit_price
        )

        # 验证更新后的值
        assert order.portfolio_id == "updated_portfolio"
        assert order.engine_id == "updated_engine"
        assert order.code == "updated_code"
        assert order.volume == 2000
        assert order.direction == DIRECTION_TYPES.SHORT

    def test_invalid_parameter_combination(self):
        """测试无效参数组合"""
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

        # 根据实体实现，负价格是被允许的（支持期货等场景）
        # 测试负价格应该成功
        order.set(
            "test_portfolio",
            "test_engine",
            "test_run",
            "000001.SZ",
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.NEW,
            1000,
            -10.50  # 负价格应该被允许
        )
        from decimal import Decimal
        assert order.limit_price == Decimal('-10.50')

        # 测试负数量（应该被拒绝）
        with pytest.raises(Exception):
            order.set(
                "test_portfolio",
                "test_engine",
                "test_run",
                "000001.SZ",
                DIRECTION_TYPES.LONG,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                -1000,  # 负数量
                10.50  # 必需的limit_price
            )

        # 测试空字符串组合
        with pytest.raises(Exception):
            order.set(
                "",  # 空portfolio_id
                "test_engine",
                "test_run",
                "000001.SZ",
                DIRECTION_TYPES.LONG,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                100,  # 必需的volume
                10.50  # 必需的limit_price
            )

    def test_parameter_type_conversion(self):
        """测试参数类型转换"""
        from decimal import Decimal

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

        # 测试枚举类型的整数转换
        order.set(
            "test_portfolio",
            "test_engine",
            "test_run",
            "000001.SZ",
            DIRECTION_TYPES.LONG.value,  # 传入整数值
            ORDER_TYPES.LIMITORDER.value,  # 传入整数值
            ORDERSTATUS_TYPES.NEW.value,  # 传入整数值
            1000,
            15.75
        )

        # 验证枚举转换成功
        assert order.direction == DIRECTION_TYPES.LONG
        assert order.order_type == ORDER_TYPES.LIMITORDER
        assert order.status == ORDERSTATUS_TYPES.NEW

        # 验证Decimal类型转换
        assert isinstance(order.limit_price, Decimal)
        assert order.limit_price == Decimal('15.75')

    def test_empty_parameter_handling(self):
        """测试空参数处理"""
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

        # 测试None值拒绝（需要包含所有必需参数）
        with pytest.raises(Exception):
            order.set(
                None,  # None portfolio_id
                "test_engine",
                "test_run",
                "000001.SZ",
                DIRECTION_TYPES.LONG,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                100,  # 必需的volume
                15.50  # 必需的limit_price
            )

        # 测试direction为None
        with pytest.raises(Exception):
            order.set(
                "test_portfolio",
                "test_engine",
                "test_run",
                "000001.SZ",
                None,  # None direction
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                100,  # 必需的volume
                15.50  # 必需的limit_price
            )

        # 测试order_type为None
        with pytest.raises(Exception):
            order.set(
                "test_portfolio",
                "test_engine",
                "test_run",
                "000001.SZ",
                DIRECTION_TYPES.LONG,
                None,  # None order_type
                ORDERSTATUS_TYPES.NEW,
                100,  # 必需的volume
                15.50  # 必需的limit_price
            )

        # 测试status为None
        with pytest.raises(Exception):
            order.set(
                "test_portfolio",
                "test_engine",
                "test_run",
                "000001.SZ",
                DIRECTION_TYPES.LONG,
                ORDER_TYPES.MARKETORDER,
                None,  # None status
                100,  # 必需的volume
                15.50  # 必需的limit_price
            )


@pytest.mark.unit
class TestOrderStatusManagement:
    """4. 订单状态管理测试"""

    def test_initial_status_assignment(self):
        """测试初始状态分配"""
        # 测试默认状态
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
        assert order.status == ORDERSTATUS_TYPES.NEW

        # 测试显式指定状态
        order_submitted = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 显式指定为SUBMITTED
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        assert order_submitted.status == ORDERSTATUS_TYPES.SUBMITTED

    def test_status_transition_validation(self):
        """测试状态转换验证"""
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,  # 使用限价单以便测试fill
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 测试NEW -> SUBMITTED转换
        order.submit()
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

        # 测试SUBMITTED -> FILLED转换（限价单不需要价格参数）
        order.fill()
        assert order.status == ORDERSTATUS_TYPES.FILLED

        # 测试取消操作（创建新订单）
        order_cancel = Order(
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
        order_cancel.cancel()
        assert order_cancel.status == ORDERSTATUS_TYPES.CANCELED

    # 移除重复测试：更完整的无效状态转换测试已在TestOrderPriceVolumeValidation.test_invalid_status_transitions()中实现

    def test_status_readonly_property(self):
        """测试状态只读属性"""
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

        # 验证status属性可以读取
        current_status = order.status
        assert current_status == ORDERSTATUS_TYPES.NEW

        # 根据实体实现，status属性没有setter，只能通过业务方法修改
        # 尝试直接设置属性会失败
        with pytest.raises(AttributeError):
            order.status = ORDERSTATUS_TYPES.FILLED

    def test_status_business_rules(self):
        """测试状态业务规则"""
        # NEW状态的订单可以提交
        new_order = Order(
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
        new_order.submit()
        assert new_order.status == ORDERSTATUS_TYPES.SUBMITTED

        # SUBMITTED状态的订单可以成交
        submitted_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,  # 使用限价单
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 直接创建为SUBMITTED状态
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        submitted_order.fill()
        assert submitted_order.status == ORDERSTATUS_TYPES.FILLED

        # NEW状态的订单可以取消
        cancel_order = Order(
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
        cancel_order.cancel()
        assert cancel_order.status == ORDERSTATUS_TYPES.CANCELED

    def test_status_enum_constraint(self):
        """测试状态枚举约束"""
        # 测试正确的枚举值
        for status in ORDERSTATUS_TYPES:
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=status,  # 使用循环变量
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )
            assert order.status == status

        # 测试无效的状态值（字符串）
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status="INVALID_STATUS",  # 无效字符串状态
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试无效的数字状态
        with pytest.raises(Exception):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=999,  # 无效数字状态
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )


@pytest.mark.unit
class TestOrderTradeExecution:
    """5. 交易执行状态测试"""

    def test_partial_fill_calculation(self):
        """测试部分成交计算"""
        from decimal import Decimal

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态才能部分成交
            volume=1000,  # 订单量1000
            limit_price=15.00,
            timestamp="2023-01-01 10:00:00"
        )

        # 执行部分成交
        order.partial_fill(600, 15.10, 5.0)

        # 验证部分成交的数据
        assert order.volume == 1000
        assert order.transaction_volume == 600
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        # 验证剩余金额计算：剩余数量(400) * 限价(15.00)
        assert order.remain == Decimal('6000.00')

        # 测试成交量不能超过订单量的逻辑
        assert order.transaction_volume <= order.volume

    def test_complete_fill_processing(self):
        """测试完全成交处理"""
        from decimal import Decimal

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态
            volume=1000,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 完全成交后调用fill方法（限价单不需要价格参数）
        order.fill()

        # 验证状态更新
        assert order.status == ORDERSTATUS_TYPES.FILLED
        assert order.transaction_volume == order.volume
        assert order.remain == Decimal('0.00')

    def test_transaction_volume_tracking(self):
        """测试成交量跟踪"""
        from decimal import Decimal

        # 测试限价单
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态
            volume=1000,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 初始状态
        assert order.transaction_volume == 0

        # 第一次部分成交
        order.partial_fill(300, 15.10, 2.5)
        assert order.transaction_volume == 300
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        assert order.transaction_price == Decimal('15.10')

        # 第二次部分成交（测试加权平均价格）
        order.partial_fill(400, 15.20, 3.0)
        assert order.transaction_volume == 700
        expected_price = (Decimal('300') * Decimal('15.10') + Decimal('400') * Decimal('15.20')) / Decimal('700')
        assert order.transaction_price == expected_price

        # 完全成交剩余部分（使用fill方法并传入价格）
        order.fill(15.30, 2.0)
        assert order.transaction_volume == 1000
        assert order.status == ORDERSTATUS_TYPES.FILLED
        assert order.remain == Decimal('0')

    def test_transaction_price_recording(self):
        """测试成交价格记录"""
        from decimal import Decimal

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态
            volume=600,  # 调整数量以匹配测试
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 第一次成交
        order.partial_fill(200, 15.75)
        assert order.transaction_price == Decimal('15.75')
        assert isinstance(order.transaction_price, Decimal)

        # 第二次成交，验证加权平均
        order.partial_fill(300, 16.25)
        # 加权平均: (200 * 15.75 + 300 * 16.25) / 500 = 16.05
        expected_avg = (Decimal('200') * Decimal('15.75') + Decimal('300') * Decimal('16.25')) / Decimal('500')
        assert order.transaction_price == expected_avg

        # 测试价格精度保持
        order.partial_fill(100, 15.9999)
        assert isinstance(order.transaction_price, Decimal)

    def test_remain_amount_calculation(self):
        """测试剩余金额计算"""
        from decimal import Decimal

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态
            volume=1000,
            limit_price=15.00,
            timestamp="2023-01-01 10:00:00"
        )

        # 根据实体实现，初始状态remain为0，只有在部分成交后才计算
        assert order.remain == Decimal('0')

        # 部分成交后剩余金额更新
        order.partial_fill(400, 15.10, 5.0)
        # 剩余数量: 1000 - 400 = 600
        # 剩余金额: 600 * 15.00 = 9000.00
        assert order.remain == Decimal('9000.00')

        # 继续部分成交
        order.partial_fill(300, 15.20, 3.0)
        # 剩余数量: 600 - 300 = 300
        # 剩余金额: 300 * 15.00 = 4500.00
        assert order.remain == Decimal('4500.00')

        # 完全成交
        order.fill(15.30, 2.0)
        assert order.remain == Decimal('0')
        assert isinstance(order.remain, Decimal)

    def test_multiple_partial_fills(self):
        """测试多次部分成交"""
        from decimal import Decimal

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态
            volume=1000,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 第一次部分成交
        order.partial_fill(200, 15.00, 1.0)
        assert order.transaction_volume == 200
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        assert order.fee == Decimal('1.0')

        # 第二次部分成交
        order.partial_fill(300, 15.10, 1.5)
        assert order.transaction_volume == 500
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        assert order.fee == Decimal('2.5')  # 累积费用

        # 第三次部分成交
        order.partial_fill(250, 15.20, 1.2)
        assert order.transaction_volume == 750
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        assert order.fee == Decimal('3.7')

        # 最后成交剩余部分
        order.partial_fill(250, 15.30, 1.3)
        assert order.transaction_volume == 1000
        assert order.status == ORDERSTATUS_TYPES.FILLED
        assert order.fee == Decimal('5.0')

    def test_overfill_prevention(self):
        """测试超额成交预防"""
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态
            volume=1000,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 测试正常成交
        order.partial_fill(600, 15.00)
        assert order.transaction_volume == 600
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

        # 测试超额成交预防（在PARTIAL_FILLED状态下尝试超过剩余数量）
        # 剩余可成交数量: 1000 - 600 = 400，尝试成交500应该被拒绝
        with pytest.raises(ValueError, match="Overfill detected"):
            order.partial_fill(500, 15.20)  # 尝试超过剩余订单量

        # 验证订单状态未被破坏
        assert order.transaction_volume == 600  # 保持原有成交量
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED  # 保持部分成交状态

        # 测试边界成交（成交剩余的400股）
        order.partial_fill(400, 15.10)
        assert order.transaction_volume == 1000
        assert order.status == ORDERSTATUS_TYPES.FILLED

    def test_execution_fee_accumulation(self):
        """测试执行费用累积"""
        from decimal import Decimal

        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,  # 需要SUBMITTED状态
            volume=1000,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 初始费用为0
        assert order.fee == Decimal('0')

        # 第一次成交费用
        order.partial_fill(300, 15.00, 2.5)
        assert order.fee == Decimal('2.5')

        # 第二次成交费用累积
        order.partial_fill(400, 15.10, 3.75)
        assert order.fee == Decimal('6.25')  # 2.5 + 3.75

        # 第三次成交费用累积
        order.partial_fill(300, 15.20, 1.25)
        assert order.fee == Decimal('7.5')  # 6.25 + 1.25
        assert isinstance(order.fee, Decimal)

        # 验证费用精度
        order2 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        order2.partial_fill(100, 15.00, 0.123456789)
        assert isinstance(order2.fee, Decimal)


@pytest.mark.unit
class TestOrderPriceVolumeValidation:
    """6. 价格数量验证测试"""

    def test_limit_price_validation(self):
        """测试限价验证"""
        from ginkgo.trading.entities.order import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
        import datetime

        # 测试正常正价（常见情况）
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
        from decimal import Decimal
        assert order.limit_price == Decimal('15.50'), "正价格应该被正确设置"

        # 测试零价格（某些特殊情况）
        zero_price_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=0.0,  # 零价格
            timestamp="2023-01-01 10:00:00"
        )
        assert zero_price_order.limit_price == Decimal('0.0'), "零价格应该被允许"

        # 测试负价格（期货等衍生品可能出现）
        negative_price_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=-37.63,  # 负价格
            timestamp="2023-01-01 10:00:00"
        )
        from decimal import Decimal
        assert negative_price_order.limit_price == Decimal('-37.63'), "负价格应该被允许（期货等情况）"

        # 测试高精度价格
        precise_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=42356.789123,  # 高精度价格
            timestamp="2023-01-01 10:00:00"
        )
        assert precise_order.limit_price == Decimal('42356.789123'), "高精度价格应该被保持"

    def test_volume_range_checking(self):
        """测试数量范围检查"""
        from ginkgo.trading.entities.order import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
        import datetime

        # 测试正常数量（正整数）
        normal_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=1000,  # 正常数量
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        assert normal_order.volume == 1000, "正常数量应该被正确设置"
        assert isinstance(normal_order.volume, int), "volume应该是整数类型"

        # 测试最小交易单位（A股通常是100股的整数倍）
        valid_lots = [100, 200, 500, 1000, 1500, 10000]
        for lot in valid_lots:
            lot_order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=lot,  # 使用循环变量
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )
            assert lot_order.volume == lot, f"{lot}股数量应该被正确设置"
            assert lot_order.volume % 100 == 0, f"{lot}股应该是100的整数倍"

        # 测试零数量被拒绝（因为业务规则改为volume必须是正数）
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=0,  # 零数量应该被拒绝
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试负数量（应该被Order类验证拒绝）
        with pytest.raises(Exception) as exc_info:
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=-500,  # 负数量应该被拒绝
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )
        # 只需要验证异常被抛出，不依赖特定错误消息

    def test_frozen_amount_management(self):
        """测试冻结金额和数量管理"""
        from decimal import Decimal

        # 测试买单 - 使用frozen_money（冻结资金）
        buy_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=700,
            limit_price=15.50,
            frozen_money=10500.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证买单的frozen_money
        assert buy_order.frozen_money == Decimal('10500.0')
        assert buy_order.frozen_volume == 0  # 买单不冻结股票数量

        # 测试卖单 - 使用frozen_volume（冻结股票数量）
        sell_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.SHORT,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=500,
            limit_price=15.50,
            frozen_volume=500,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证卖单的frozen_volume
        assert sell_order.frozen_volume == 500
        assert sell_order.frozen_money == Decimal('0')  # 卖单不冻结资金

        # 测试frozen_money的类型转换
        buy_order.frozen_money = 15000  # int输入
        assert buy_order.frozen_money == Decimal('15000')

        buy_order.frozen_money = 15500.75  # float输入
        assert buy_order.frozen_money == Decimal('15500.75')

        buy_order.frozen_money = "16000"  # 字符串输入
        assert buy_order.frozen_money == Decimal('16000')

        # 测试frozen_volume的类型转换
        sell_order.frozen_volume = 1000.0  # float输入转为int
        assert sell_order.frozen_volume == 1000
        assert isinstance(sell_order.frozen_volume, int)

        # 测试frozen_volume的类型验证
        with pytest.raises((TypeError, ValueError)):
            sell_order.frozen_volume = "invalid"

    def test_negative_values_rejection(self):
        """测试负值拒绝"""
        # 注意：价格字段支持负值，主要测试数量类字段不能为负

        # 测试负volume被拒绝
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=-100,  # 负volume
                limit_price=15.50
            )

        # 测试frozen_volume不能为负（通过setter）
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

        with pytest.raises((TypeError, ValueError)):
            order.frozen_volume = -50

        # 验证价格字段支持负值
        future_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=-37.63,  # 负价格
            transaction_price=-35.20,  # 负成交价
            timestamp="2023-01-01 10:00:00"
        )

        from decimal import Decimal
        assert future_order.limit_price == Decimal('-37.63')
        assert future_order.transaction_price == Decimal('-35.20')

    def test_zero_values_handling(self):
        """测试零值处理"""
        from decimal import Decimal

        # 测试零价格订单（市价单场景）
        market_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=0.0,  # 零价格
            timestamp="2023-01-01 10:00:00"
        )
        assert market_order.limit_price == Decimal('0')

        # 测试零数量订单被拒绝
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=0,  # 零数量
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )

        # 测试零冻结金额（默认值）
        zero_frozen_order = Order(
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
        assert zero_frozen_order.frozen_money == Decimal('0')

        # 测试零冻结数量（默认值）
        assert zero_frozen_order.frozen_volume == 0

        # 测试零成交价格（默认值）
        assert zero_frozen_order.transaction_price == Decimal('0')

        # 测试零成交数量（默认值）
        assert zero_frozen_order.transaction_volume == 0

        # 测试零剩余金额（默认值）
        assert zero_frozen_order.remain == Decimal('0')

        # 测试零费用（默认值）
        assert zero_frozen_order.fee == Decimal('0')

    # 移除重复测试：业务状态转换已在TestOrderStatusManagement.test_status_transition_validation()中覆盖

    def test_invalid_status_transitions(self):
        """测试无效状态转换"""
        # 测试已成交订单不能再操作
        filled_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        filled_order.submit()
        filled_order.fill()

        # 已成交订单不能取消
        with pytest.raises(ValueError):
            filled_order.cancel()

        # 已成交订单不能再成交
        with pytest.raises(ValueError):
            filled_order.partial_fill(50, 10.0)

        # 测试已取消订单不能再操作
        canceled_order = Order(
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
        canceled_order.submit()
        canceled_order.cancel()

        # 已取消订单不能成交
        with pytest.raises(ValueError):
            canceled_order.fill(10.0)

    def test_decimal_precision_preservation(self):
        """测试精度保持"""
        from decimal import Decimal

        # 测试高精度价格的保持
        high_precision_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=12.345678,
            frozen_money=1234.5678,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证Decimal精度保持
        assert high_precision_order.limit_price == Decimal('12.345678')
        assert high_precision_order.frozen_money == Decimal('1234.5678')

        # 测试部分成交时精度保持
        high_precision_order.submit()
        high_precision_order.partial_fill(30, 12.346789, 1.23)  # 不同精度的成交价格

        # 验证加权平均价格精度
        expected_avg_price = Decimal('12.346789')  # 只有一次成交
        assert high_precision_order.transaction_price == expected_avg_price

        # 验证费用精度
        assert high_precision_order.fee == Decimal('1.23')

        # 测试多次成交的精度累积
        high_precision_order.partial_fill(20, 12.344567, 0.89)

        # 验证加权平均精度：(30*12.346789 + 20*12.344567) / 50
        expected_weighted_avg = (Decimal('30') * Decimal('12.346789') +
                               Decimal('20') * Decimal('12.344567')) / Decimal('50')
        assert high_precision_order.transaction_price == expected_weighted_avg

        # 验证费用累积精度
        assert high_precision_order.fee == Decimal('1.23') + Decimal('0.89')

        # 测试负价格精度保持（期货场景）
        negative_price_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=-37.125456,
            timestamp="2023-01-01 10:00:00"
        )

        assert negative_price_order.limit_price == Decimal('-37.125456')

    def test_price_volume_consistency(self):
        """测试价格数量一致性"""
        from decimal import Decimal

        # 测试冻结金额与价格数量的一致性
        consistent_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=1000,
            limit_price=10.5,
            frozen_money=10500.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证冻结金额与订单金额的一致性
        expected_frozen = Decimal('1000') * Decimal('10.5')
        assert consistent_order.frozen_money == Decimal('10500.0')

        # 测试剩余金额的计算一致性
        consistent_order.submit()
        consistent_order.partial_fill(300, 10.8, 15.0)

        # 剩余数量应该等于订单数量减去成交数量
        remaining_volume = consistent_order.volume - consistent_order.transaction_volume
        assert remaining_volume == 700

        # 成交比例应该等于成交数量除以订单数量
        fill_ratio = consistent_order.transaction_volume / consistent_order.volume
        expected_ratio = 300.0 / 1000.0
        assert abs(fill_ratio - expected_ratio) < 0.0001

        # 测试完全成交后的一致性
        consistent_order.fill(11.0, 20.0)
        assert consistent_order.transaction_volume == consistent_order.volume

        # 测试负价格时的一致性（期货场景）
        future_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=-20.0,
            timestamp="2023-01-01 10:00:00"
        )

        future_order.submit()
        future_order.fill(-18.5, 5.0)

        # 验证即使价格为负，成交比例仍然正确
        fill_ratio = future_order.transaction_volume / future_order.volume
        assert fill_ratio == 1.0
        assert future_order.transaction_price == Decimal('-18.5')

        # 测试零价格的一致性（市价单场景）
        market_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=0.0,
            timestamp="2023-01-01 10:00:00"
        )

        market_order.submit()
        market_order.fill(15.25, 7.5)  # 市价成交

        fill_ratio = market_order.transaction_volume / market_order.volume
        assert fill_ratio == 1.0
        assert market_order.transaction_price == Decimal('15.25')


@pytest.mark.unit
class TestOrderEnumConstraints:
    """7. 枚举类型约束测试"""

    def test_direction_types_validation(self):
        """测试交易方向验证"""
        # 测试有效的方向枚举值
        for direction in [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT]:
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=direction,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )
            assert order.direction == direction

        # 测试整数值自动转换为枚举
        long_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG.value,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        assert long_order.direction == DIRECTION_TYPES.LONG

        # 测试None值被拒绝
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=None,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50
            )

        # 测试无效类型被拒绝
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction="INVALID",
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50
            )

    def test_order_types_validation(self):
        """测试订单类型验证"""
        # 测试有效的订单类型枚举值
        for order_type in [ORDER_TYPES.MARKETORDER, ORDER_TYPES.LIMITORDER]:
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=order_type,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )
            assert order.order_type == order_type

        # 测试整数值自动转换为枚举
        market_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER.value,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        assert market_order.order_type == ORDER_TYPES.MARKETORDER

        # 测试None值被拒绝
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=None,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50
            )

    def test_order_status_validation(self):
        """测试订单状态验证"""
        # 测试有效的订单状态枚举值
        valid_statuses = [
            ORDERSTATUS_TYPES.NEW,
            ORDERSTATUS_TYPES.SUBMITTED,
            ORDERSTATUS_TYPES.PARTIAL_FILLED,
            ORDERSTATUS_TYPES.FILLED,
            ORDERSTATUS_TYPES.CANCELED
        ]

        for status in valid_statuses:
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=status,
                volume=100,
                limit_price=15.50,
                timestamp="2023-01-01 10:00:00"
            )
            assert order.status == status

        # 测试整数值自动转换为枚举
        new_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW.value,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )
        assert new_order.status == ORDERSTATUS_TYPES.NEW

        # 测试None值被拒绝
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=None,
                volume=100,
                limit_price=15.50
            )

    def test_source_types_validation(self):
        """测试来源类型验证"""
        # 创建订单后检查默认source
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
        # 验证Order在初始化时设置了默认source
        assert order.source == SOURCE_TYPES.OTHER

        # 测试通过set_source设置有效的source类型
        valid_sources = [
            SOURCE_TYPES.SIM,
            SOURCE_TYPES.REALTIME,
            SOURCE_TYPES.BACKTEST,
            SOURCE_TYPES.STRATEGY
        ]

        for source in valid_sources:
            order.set_source(source)
            assert order.source == source

        # 测试通过属性setter设置source
        order.source = SOURCE_TYPES.DATABASE
        assert order.source == SOURCE_TYPES.DATABASE

        # 测试无效source类型会被Base类拒绝
        with pytest.raises(Exception):
            order.source = "INVALID_SOURCE"

        with pytest.raises(Exception):
            order.source = None

        with pytest.raises(Exception):
            order.source = 999  # 无效的枚举值

    def test_invalid_enum_rejection(self):
        """测试无效枚举拒绝"""
        # 测试无效的direction值
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=999,  # 无效枚举值
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50
            )

        # 测试无效的order_type值
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=888,  # 无效枚举值
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50
            )

        # 测试无效的status值
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=777,  # 无效枚举值
                volume=100,
                limit_price=15.50
            )

        # 测试字符串类型（不被接受）
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction="INVALID_STRING",
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50
            )

        # 测试浮点数类型（不被接受）
        with pytest.raises(Exception):
            Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code="000001.SZ",
                direction=1.5,  # 浮点数不被接受
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=15.50
            )

    def test_enum_type_safety(self):
        """测试枚举类型安全"""
        # 创建订单验证枚举类型安全
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证枚举类型被正确存储
        assert isinstance(order.direction, DIRECTION_TYPES)
        assert isinstance(order.order_type, ORDER_TYPES)
        assert isinstance(order.status, ORDERSTATUS_TYPES)

        # 验证枚举值的比较安全性
        assert order.direction == DIRECTION_TYPES.LONG
        assert order.direction != DIRECTION_TYPES.SHORT
        assert order.order_type == ORDER_TYPES.LIMITORDER
        assert order.status == ORDERSTATUS_TYPES.NEW

        # 测试整数值转换后的类型安全
        int_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG.value,
            order_type=ORDER_TYPES.LIMITORDER.value,
            status=ORDERSTATUS_TYPES.NEW.value,
            volume=100,
            limit_price=15.50,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证整数值被正确转换为枚举类型
        assert isinstance(int_order.direction, DIRECTION_TYPES)
        assert isinstance(int_order.order_type, ORDER_TYPES)
        assert isinstance(int_order.status, ORDERSTATUS_TYPES)
        assert int_order.direction == DIRECTION_TYPES.LONG
        assert int_order.order_type == ORDER_TYPES.LIMITORDER
        assert int_order.status == ORDERSTATUS_TYPES.NEW

        # 验证枚举类型可以用于逻辑判断
        assert order.direction == DIRECTION_TYPES.LONG

        # 验证枚举类型可以用于集合操作
        long_orders = [order, int_order]
        assert all(o.direction == DIRECTION_TYPES.LONG for o in long_orders)





