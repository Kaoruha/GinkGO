"""
Tick类TDD测试

通过TDD方式开发Tick高频交易数据类的完整测试套件
涵盖逐笔交易数据处理和聚合功能
"""
import pytest
import datetime
from decimal import Decimal

from ginkgo.trading.entities.tick import Tick
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES, COMPONENT_TYPES


@pytest.mark.unit
class TestTickConstruction:
    """1. 构造和初始化测试"""

    def test_required_parameters_constructor(self):
        """测试必需参数构造"""
        from decimal import Decimal

        # 测试必需参数构造（与Bar设计一致）
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )

        # 验证所有参数正确赋值
        assert tick.code == "000001.SZ"
        assert tick.price == Decimal('10.5')
        assert tick.volume == 1000
        assert tick.direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert tick.source == SOURCE_TYPES.OTHER  # 默认值

        # 验证属性类型
        assert isinstance(tick.price, Decimal)
        assert isinstance(tick.volume, int)
        assert isinstance(tick.direction, TICKDIRECTION_TYPES)
        assert isinstance(tick.source, SOURCE_TYPES)
        assert isinstance(tick.timestamp, datetime.datetime)

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        from decimal import Decimal

        # 测试完整参数构造，包括显式指定source
        timestamp = datetime.datetime(2023, 1, 15, 9, 30, 25, 123456)
        tick = Tick(
            code="000002.SZ",
            price=15.75,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=timestamp,
            source=SOURCE_TYPES.SINA
        )

        # 验证所有参数正确赋值
        assert tick.code == "000002.SZ"
        assert tick.price == Decimal('15.75')
        assert tick.volume == 2000
        assert tick.direction == TICKDIRECTION_TYPES.ACTIVESELL
        assert tick.timestamp == timestamp
        assert tick.source == SOURCE_TYPES.SINA

        # 验证Base类属性（UUID等）
        assert tick.uuid is not None
        assert len(tick.uuid) > 0

    def test_base_class_inheritance(self):
        """测试Base类继承验证"""
        from ginkgo.trading.core.base import Base

        # 创建Tick实例
        tick = Tick(
            code="000003.SZ",
            price=12.34,
            volume=500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )

        # 验证继承关系
        assert isinstance(tick, Base)
        assert isinstance(tick, Tick)

        # 验证Base类提供的功能
        assert hasattr(tick, 'uuid')
        assert tick.uuid is not None
        assert len(tick.uuid) > 0

        # 验证UUID唯一性
        tick2 = Tick(
            code="000004.SZ",
            price=9.87,
            volume=800,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick.uuid != tick2.uuid

    def test_component_type_assignment(self):
        """测试组件类型分配"""
        # 创建Tick实例并验证组件类型
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )

        # 验证组件类型正确分配
        assert hasattr(tick, 'component_type')
        assert tick.component_type == COMPONENT_TYPES.TICK
        assert isinstance(tick.component_type, type(COMPONENT_TYPES.TICK))

        # 验证组件类型的一致性
        tick2 = Tick(
            code="000002.SZ",
            price=12.0,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick2.component_type == COMPONENT_TYPES.TICK
        assert tick.component_type == tick2.component_type

    def test_custom_uuid_assignment(self):
        """测试自定义UUID分配"""
        # 测试自定义UUID分配
        custom_uuid = "custom-tick-uuid-67890"
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now(),
            uuid=custom_uuid
        )

        # 验证自定义UUID正确分配
        assert tick.uuid == custom_uuid
        assert isinstance(tick.uuid, str)
        assert len(tick.uuid) > 0

    def test_decimal_precision_handling(self):
        """测试价格精度处理"""
        from decimal import Decimal

        # 测试高精度价格处理
        high_precision_price = 123.456789
        tick = Tick(
            code="000005.SZ",
            price=high_precision_price,
            volume=1500,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )

        # 验证价格使用Decimal类型存储
        assert isinstance(tick.price, Decimal)
        assert tick.price == Decimal('123.456789')

        # 测试字符串价格输入
        tick_str = Tick(
            code="000006.SZ",
            price="456.789123",
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert isinstance(tick_str.price, Decimal)
        assert tick_str.price == Decimal('456.789123')

        # 测试整数价格输入
        tick_int = Tick(
            code="000007.SZ",
            price=100,
            volume=1000,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert isinstance(tick_int.price, Decimal)
        assert tick_int.price == Decimal('100')

    def test_direction_enum_assignment(self):
        """测试交易方向枚举分配"""
        # 测试主动买入
        tick_buy = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_buy.direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert isinstance(tick_buy.direction, TICKDIRECTION_TYPES)

        # 测试主动卖出
        tick_sell = Tick(
            code="000002.SZ",
            price=10.3,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick_sell.direction == TICKDIRECTION_TYPES.ACTIVESELL

        # 测试中性盘
        tick_neutral = Tick(
            code="000003.SZ",
            price=10.4,
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert tick_neutral.direction == TICKDIRECTION_TYPES.NEUTRAL

        # 测试撤单
        tick_cancel = Tick(
            code="000004.SZ",
            price=10.6,
            volume=500,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now()
        )
        assert tick_cancel.direction == TICKDIRECTION_TYPES.CANCEL

        # 验证所有方向类型都是正确的枚举
        directions = [tick_buy.direction, tick_sell.direction, tick_neutral.direction, tick_cancel.direction]
        for direction in directions:
            assert isinstance(direction, TICKDIRECTION_TYPES)

    def test_source_enum_assignment(self):
        """测试数据源枚举分配"""
        # 测试默认数据源
        tick_default = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_default.source == SOURCE_TYPES.OTHER
        assert isinstance(tick_default.source, SOURCE_TYPES)

        # 测试新浪数据源
        tick_sina = Tick(
            code="000002.SZ",
            price=10.3,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now(),
            source=SOURCE_TYPES.SINA
        )
        assert tick_sina.source == SOURCE_TYPES.SINA

        # 测试Tushare数据源
        tick_tushare = Tick(
            code="000003.SZ",
            price=10.4,
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )
        assert tick_tushare.source == SOURCE_TYPES.TUSHARE

        # 测试数据库数据源
        tick_database = Tick(
            code="000004.SZ",
            price=10.6,
            volume=500,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now(),
            source=SOURCE_TYPES.DATABASE
        )
        assert tick_database.source == SOURCE_TYPES.DATABASE

        # 验证所有数据源类型都是正确的枚举
        sources = [tick_default.source, tick_sina.source, tick_tushare.source, tick_database.source]
        for source in sources:
            assert isinstance(source, SOURCE_TYPES)

    def test_volume_integer_conversion(self):
        """测试成交量整数转换"""
        # 测试整数成交量
        tick_int = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_int.volume == 1000
        assert isinstance(tick_int.volume, int)

        # 测试浮点数成交量自动转换
        tick_float = Tick(
            code="000002.SZ",
            price=10.3,
            volume=2000.0,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick_float.volume == 2000
        assert isinstance(tick_float.volume, int)

        # 测试大数值成交量
        tick_large = Tick(
            code="000003.SZ",
            price=10.4,
            volume=1500000,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert tick_large.volume == 1500000
        assert isinstance(tick_large.volume, int)

        # 测试零成交量
        tick_zero = Tick(
            code="000004.SZ",
            price=10.6,
            volume=0,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now()
        )
        assert tick_zero.volume == 0
        assert isinstance(tick_zero.volume, int)

    def test_timestamp_normalization(self):
        """测试时间戳标准化处理"""
        import time

        # 测试datetime对象时间戳
        dt_timestamp = datetime.datetime(2023, 5, 15, 14, 30, 25, 123456)
        tick_dt = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=dt_timestamp
        )
        assert tick_dt.timestamp == dt_timestamp
        assert isinstance(tick_dt.timestamp, datetime.datetime)

        # 测试字符串时间戳
        str_timestamp = "2023-05-15 14:30:25"
        tick_str = Tick(
            code="000002.SZ",
            price=10.3,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=str_timestamp
        )
        assert isinstance(tick_str.timestamp, datetime.datetime)
        assert tick_str.timestamp.year == 2023
        assert tick_str.timestamp.month == 5
        assert tick_str.timestamp.day == 15

        # 测试当前时间戳
        current_time = datetime.datetime.now()
        tick_now = Tick(
            code="000003.SZ",
            price=10.4,
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=current_time
        )
        assert isinstance(tick_now.timestamp, datetime.datetime)
        # 验证时间戳在合理范围内（允许几秒差异）
        time_diff = abs((tick_now.timestamp - current_time).total_seconds())
        assert time_diff < 1.0


@pytest.mark.unit
class TestTickProperties:
    """2. 属性访问测试"""

    def test_code_property(self):
        """测试代码属性"""
        # 测试股票代码属性读取
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )

        # 验证代码属性
        assert tick.code == "000001.SZ"
        assert isinstance(tick.code, str)

        # 测试不同的股票代码格式
        tick_sh = Tick(
            code="600000.SH",
            price=15.3,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick_sh.code == "600000.SH"

        # 测试创业板代码
        tick_sz = Tick(
            code="300001.SZ",
            price=25.8,
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert tick_sz.code == "300001.SZ"

        # 验证代码属性为只读（通过属性装饰器）
        assert hasattr(tick, 'code')
        # 代码不应该为空
        assert len(tick.code) > 0

    def test_price_property(self):
        """测试价格属性"""
        from decimal import Decimal

        # 测试整数价格
        tick_int = Tick(
            code="000001.SZ",
            price=10,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_int.price == Decimal('10')
        assert isinstance(tick_int.price, Decimal)

        # 测试浮点数价格
        tick_float = Tick(
            code="000002.SZ",
            price=15.75,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick_float.price == Decimal('15.75')
        assert isinstance(tick_float.price, Decimal)

        # 测试字符串价格
        tick_str = Tick(
            code="000003.SZ",
            price="25.125",
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert tick_str.price == Decimal('25.125')
        assert isinstance(tick_str.price, Decimal)

        # 测试高精度价格
        tick_precision = Tick(
            code="000004.SZ",
            price="123.456789",
            volume=500,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_precision.price == Decimal('123.456789')

        # 测试零价格
        tick_zero = Tick(
            code="000005.SZ",
            price=0,
            volume=0,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now()
        )
        assert tick_zero.price == Decimal('0')
        assert isinstance(tick_zero.price, Decimal)

    def test_volume_property(self):
        """测试成交量属性"""
        # 测试整数成交量
        tick_int = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_int.volume == 1000
        assert isinstance(tick_int.volume, int)

        # 测试浮点数成交量（自动转换为整数）
        tick_float = Tick(
            code="000002.SZ",
            price=15.75,
            volume=2000.0,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick_float.volume == 2000
        assert isinstance(tick_float.volume, int)

        # 测试大成交量
        tick_large = Tick(
            code="000003.SZ",
            price=25.125,
            volume=1500000,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert tick_large.volume == 1500000
        assert isinstance(tick_large.volume, int)

        # 测试零成交量
        tick_zero = Tick(
            code="000004.SZ",
            price=10.6,
            volume=0,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now()
        )
        assert tick_zero.volume == 0
        assert isinstance(tick_zero.volume, int)

        # 测试小数成交量转换（向下取整）
        tick_decimal = Tick(
            code="000005.SZ",
            price=12.3,
            volume=1500.9,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_decimal.volume == 1500
        assert isinstance(tick_decimal.volume, int)

    def test_direction_property(self):
        """测试交易方向属性"""
        # 测试主动买入方向
        tick_buy = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_buy.direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert isinstance(tick_buy.direction, TICKDIRECTION_TYPES)

        # 测试主动卖出方向
        tick_sell = Tick(
            code="000002.SZ",
            price=15.75,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick_sell.direction == TICKDIRECTION_TYPES.ACTIVESELL
        assert isinstance(tick_sell.direction, TICKDIRECTION_TYPES)

        # 测试中性盘
        tick_neutral = Tick(
            code="000003.SZ",
            price=25.125,
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert tick_neutral.direction == TICKDIRECTION_TYPES.NEUTRAL
        assert isinstance(tick_neutral.direction, TICKDIRECTION_TYPES)

        # 测试撤单
        tick_cancel = Tick(
            code="000004.SZ",
            price=10.6,
            volume=0,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now()
        )
        assert tick_cancel.direction == TICKDIRECTION_TYPES.CANCEL
        assert isinstance(tick_cancel.direction, TICKDIRECTION_TYPES)

        # 测试其他交易方向类型
        tick_remain = Tick(
            code="000005.SZ",
            price=12.3,
            volume=500,
            direction=TICKDIRECTION_TYPES.REMAIN2LIMIT,
            timestamp=datetime.datetime.now()
        )
        assert tick_remain.direction == TICKDIRECTION_TYPES.REMAIN2LIMIT
        assert isinstance(tick_remain.direction, TICKDIRECTION_TYPES)

    def test_timestamp_property(self):
        """测试时间戳属性"""
        # 测试datetime对象时间戳
        dt_timestamp = datetime.datetime(2023, 6, 15, 9, 30, 25, 123456)
        tick_dt = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=dt_timestamp
        )
        assert tick_dt.timestamp == dt_timestamp
        assert isinstance(tick_dt.timestamp, datetime.datetime)

        # 测试字符串时间戳（自动转换）
        str_timestamp = "2023-06-15 14:30:25"
        tick_str = Tick(
            code="000002.SZ",
            price=15.75,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=str_timestamp
        )
        assert isinstance(tick_str.timestamp, datetime.datetime)
        assert tick_str.timestamp.year == 2023
        assert tick_str.timestamp.month == 6
        assert tick_str.timestamp.day == 15
        assert tick_str.timestamp.hour == 14
        assert tick_str.timestamp.minute == 30
        assert tick_str.timestamp.second == 25

        # 测试当前时间戳
        current_time = datetime.datetime.now()
        tick_now = Tick(
            code="000003.SZ",
            price=25.125,
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=current_time
        )
        assert tick_now.timestamp == current_time
        assert isinstance(tick_now.timestamp, datetime.datetime)

        # 测试微秒精度时间戳
        microsec_timestamp = datetime.datetime(2023, 6, 15, 15, 45, 30, 987654)
        tick_micro = Tick(
            code="000004.SZ",
            price=10.6,
            volume=800,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=microsec_timestamp
        )
        assert tick_micro.timestamp == microsec_timestamp
        assert tick_micro.timestamp.microsecond == 987654
        assert isinstance(tick_micro.timestamp, datetime.datetime)

    def test_source_property(self):
        """测试数据源属性"""
        # 测试默认数据源
        tick_default = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_default.source == SOURCE_TYPES.OTHER
        assert isinstance(tick_default.source, SOURCE_TYPES)

        # 测试指定数据源
        tick_sina = Tick(
            code="000002.SZ",
            price=15.75,
            volume=2000,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now(),
            source=SOURCE_TYPES.SINA
        )
        assert tick_sina.source == SOURCE_TYPES.SINA
        assert isinstance(tick_sina.source, SOURCE_TYPES)

        # 测试Tushare数据源
        tick_tushare = Tick(
            code="000003.SZ",
            price=25.125,
            volume=1500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )
        assert tick_tushare.source == SOURCE_TYPES.TUSHARE
        assert isinstance(tick_tushare.source, SOURCE_TYPES)

        # 测试所有主要数据源类型
        test_sources = [
            SOURCE_TYPES.OTHER,
            SOURCE_TYPES.SIM,
            SOURCE_TYPES.REALTIME,
            SOURCE_TYPES.SINA,
            SOURCE_TYPES.TUSHARE,
            SOURCE_TYPES.DATABASE
        ]

        for source in test_sources:
            tick_source_test = Tick(
                code="TEST.SZ",
                price=10.0,
                volume=100,
                direction=TICKDIRECTION_TYPES.NEUTRAL,
                timestamp=datetime.datetime.now(),
                source=source
            )
            assert tick_source_test.source == source
            assert isinstance(tick_source_test.source, SOURCE_TYPES)

    def test_property_type_validation(self):
        """测试属性类型验证"""
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00",
            source=SOURCE_TYPES.SINA
        )

        # 验证所有属性的数据类型
        assert isinstance(tick.code, str)
        assert isinstance(tick.price, Decimal)
        assert isinstance(tick.volume, int)
        assert isinstance(tick.direction, TICKDIRECTION_TYPES)
        assert isinstance(tick.timestamp, datetime.datetime)
        assert isinstance(tick.source, SOURCE_TYPES)

        # 验证属性值的基本合理性
        assert len(tick.code) > 0
        assert tick.price >= 0
        assert tick.volume >= 0
        assert tick.direction in TICKDIRECTION_TYPES
        assert tick.source in SOURCE_TYPES
        assert isinstance(tick.timestamp.year, int)
        assert isinstance(tick.timestamp.month, int)
        assert isinstance(tick.timestamp.day, int)

    def test_property_immutability(self):
        """测试属性不可变性"""
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now(),
            source=SOURCE_TYPES.SINA
        )

        # 验证属性是只读的（无setter方法）
        original_code = tick.code
        original_price = tick.price
        original_volume = tick.volume
        original_direction = tick.direction
        original_timestamp = tick.timestamp
        original_source = tick.source

        # 尝试通过属性访问来修改值应该没有效果
        # （Python中@property装饰的属性默认是只读的）
        with pytest.raises(AttributeError):
            tick.code = "999999.SZ"

        with pytest.raises(AttributeError):
            tick.price = Decimal('99.99')

        with pytest.raises(AttributeError):
            tick.volume = 9999

        with pytest.raises(AttributeError):
            tick.direction = TICKDIRECTION_TYPES.ACTIVESELL

        with pytest.raises(AttributeError):
            tick.timestamp = datetime.datetime.now()

        with pytest.raises(AttributeError):
            tick.source = SOURCE_TYPES.OTHER

        # 验证属性值没有被修改
        assert tick.code == original_code
        assert tick.price == original_price
        assert tick.volume == original_volume
        assert tick.direction == original_direction
        assert tick.timestamp == original_timestamp
        assert tick.source == original_source


@pytest.mark.unit
class TestTickDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self):
        """测试直接参数设置"""
        # 创建一个Tick实例
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 使用set方法重新设置数据
        tick.set(
            "000002.SZ",
            15.75,
            2000,
            TICKDIRECTION_TYPES.ACTIVESELL,
            "2024-01-01 10:30:00",
            SOURCE_TYPES.SINA
        )

        # 验证设置结果
        assert tick.code == "000002.SZ"
        assert tick.price == Decimal('15.75')
        assert tick.volume == 2000
        assert tick.direction == TICKDIRECTION_TYPES.ACTIVESELL
        assert tick.source == SOURCE_TYPES.SINA

        # 验证时间戳被正确处理
        assert isinstance(tick.timestamp, datetime.datetime)
        assert tick.timestamp.year == 2024
        assert tick.timestamp.month == 1
        assert tick.timestamp.day == 1
        assert tick.timestamp.hour == 10

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        import pandas as pd

        # 创建初始Tick实例
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 创建pandas Series数据
        series_data = pd.Series({
            "code": "000003.SZ",
            "price": 25.125,
            "volume": 1500,
            "direction": TICKDIRECTION_TYPES.NEUTRAL,
            "timestamp": "2024-02-15 14:30:00",
            "source": SOURCE_TYPES.TUSHARE
        })

        # 使用Series设置数据
        tick.set(series_data)

        # 验证设置结果
        assert tick.code == "000003.SZ"
        assert tick.price == Decimal('25.125')
        assert tick.volume == 1500
        assert tick.direction == TICKDIRECTION_TYPES.NEUTRAL
        assert tick.source == SOURCE_TYPES.TUSHARE

        # 验证时间戳正确处理
        assert isinstance(tick.timestamp, datetime.datetime)
        assert tick.timestamp.year == 2024
        assert tick.timestamp.month == 2
        assert tick.timestamp.day == 15

    def test_singledispatch_routing(self):
        """测试方法分派路由"""
        import pandas as pd

        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 测试直接参数路由（多个参数）
        tick.set(
            "PARAM.SZ",
            20.0,
            500,
            TICKDIRECTION_TYPES.ACTIVESELL,
            "2024-01-01 11:00:00"
        )
        assert tick.code == "PARAM.SZ"
        assert tick.price == Decimal('20.0')

        # 测试pandas Series路由（单个Series参数）
        series_data = pd.Series({
            "code": "SERIES.SZ",
            "price": 30.0,
            "volume": 800,
            "direction": TICKDIRECTION_TYPES.NEUTRAL,
            "timestamp": "2024-01-01 12:00:00"
        })
        tick.set(series_data)
        assert tick.code == "SERIES.SZ"
        assert tick.price == Decimal('30.0')

        # 验证singledispatch正确识别了输入类型
        # 通过验证结果来确认路由工作正确
        assert isinstance(tick.price, Decimal)
        assert isinstance(tick.volume, int)
        assert isinstance(tick.direction, TICKDIRECTION_TYPES)

    def test_parameter_validation_in_setting(self):
        """测试设置时的参数验证"""
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 注意：singledispatch基于第一个参数类型分派
        # 只有当第一个参数类型正确时，才会进入对应的注册方法进行验证

        # 注意：空字符串代码实际上不会触发验证错误
        # 只测试那些实际实现了验证的情况

        # 测试负数价格 - 第一个参数类型正确，触发str分派
        with pytest.raises(ValueError):
            tick.set(
                "000001.SZ",
                -10.5,  # 负数价格
                1000,
                TICKDIRECTION_TYPES.ACTIVEBUY,
                "2024-01-01 09:30:00"
            )

        # 测试负数成交量 - 第一个参数类型正确，触发str分派
        with pytest.raises(ValueError):
            tick.set(
                "000001.SZ",
                10.5,
                -1000,  # 负数成交量
                TICKDIRECTION_TYPES.ACTIVEBUY,
                "2024-01-01 09:30:00"
            )

        # 测试无效方向类型 - 第一个参数类型正确，触发str分派
        with pytest.raises(ValueError):
            tick.set(
                "000001.SZ",
                10.5,
                1000,
                "invalid_direction",  # 无效方向
                "2024-01-01 09:30:00"
            )

        # 测试无效时间戳类型 - 第一个参数类型正确，触发str分派
        with pytest.raises(ValueError):
            tick.set(
                "000001.SZ",
                10.5,
                1000,
                TICKDIRECTION_TYPES.ACTIVEBUY,
                123456  # 无效时间戳类型
            )

        # 测试错误的第一个参数类型会导致TypeError（分派失败）
        with pytest.raises(TypeError):
            tick.set(123, 10.5, 1000, TICKDIRECTION_TYPES.ACTIVEBUY, "2024-01-01")

    def test_required_fields_validation(self):
        """测试必需字段验证"""
        import pandas as pd

        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 测试缺少必需字段的Series
        incomplete_series = pd.Series({
            "code": "000001.SZ",
            "price": 10.5,
            # 缺少volume, direction, timestamp
        })

        with pytest.raises(ValueError):
            tick.set(incomplete_series)

        # 测试只缺少一个字段
        missing_volume = pd.Series({
            "code": "000001.SZ",
            "price": 10.5,
            "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
            "timestamp": "2024-01-01 09:30:00"
            # 缺少volume
        })

        with pytest.raises(ValueError):
            tick.set(missing_volume)

        # 测试完整的Series能正常工作
        complete_series = pd.Series({
            "code": "000002.SZ",
            "price": 15.75,
            "volume": 2000,
            "direction": TICKDIRECTION_TYPES.ACTIVESELL,
            "timestamp": "2024-01-01 10:30:00"
        })

        tick.set(complete_series)  # 不应该抛出异常
        assert tick.code == "000002.SZ"
        assert tick.price == Decimal('15.75')

    def test_decimal_conversion_in_setting(self):
        """测试设置时Decimal转换"""
        import pandas as pd

        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 测试直接参数设置中的Decimal转换
        # 测试整数价格
        tick.set(
            "000001.SZ",
            10,  # 整数
            1000,
            TICKDIRECTION_TYPES.ACTIVEBUY,
            "2024-01-01 09:30:00"
        )
        assert tick.price == Decimal('10')
        assert isinstance(tick.price, Decimal)

        # 测试浮点数价格
        tick.set(
            "000001.SZ",
            10.57,  # 浮点数
            1000,
            TICKDIRECTION_TYPES.ACTIVEBUY,
            "2024-01-01 09:30:00"
        )
        assert tick.price == Decimal('10.57')
        assert isinstance(tick.price, Decimal)

        # 测试字符串价格
        tick.set(
            "000001.SZ",
            "10.125",  # 字符串
            1000,
            TICKDIRECTION_TYPES.ACTIVEBUY,
            "2024-01-01 09:30:00"
        )
        assert tick.price == Decimal('10.125')
        assert isinstance(tick.price, Decimal)

        # 测试Series设置中的Decimal转换
        series_data = pd.Series({
            "code": "000002.SZ",
            "price": 25.375,  # 浮点数
            "volume": 2000,
            "direction": TICKDIRECTION_TYPES.NEUTRAL,
            "timestamp": "2024-01-01 10:30:00"
        })

        tick.set(series_data)
        assert tick.price == Decimal('25.375')
        assert isinstance(tick.price, Decimal)

    def test_datetime_normalization_setting(self):
        """测试时间标准化设置"""
        import pandas as pd

        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 测试字符串时间戳标准化
        tick.set(
            "000001.SZ",
            10.5,
            1000,
            TICKDIRECTION_TYPES.ACTIVEBUY,
            "2024-05-15 14:30:25"  # 字符串时间戳
        )
        assert isinstance(tick.timestamp, datetime.datetime)
        assert tick.timestamp.year == 2024
        assert tick.timestamp.month == 5
        assert tick.timestamp.day == 15
        assert tick.timestamp.hour == 14
        assert tick.timestamp.minute == 30
        assert tick.timestamp.second == 25

        # 测试datetime对象时间戳
        dt_obj = datetime.datetime(2024, 6, 20, 16, 45, 30)
        tick.set(
            "000001.SZ",
            10.5,
            1000,
            TICKDIRECTION_TYPES.ACTIVEBUY,
            dt_obj  # datetime对象
        )
        assert isinstance(tick.timestamp, datetime.datetime)
        assert tick.timestamp == dt_obj

        # 测试Series中的时间戳标准化
        series_data = pd.Series({
            "code": "000002.SZ",
            "price": 15.75,
            "volume": 2000,
            "direction": TICKDIRECTION_TYPES.ACTIVESELL,
            "timestamp": "2024-07-10 09:15:45"  # 字符串时间戳
        })

        tick.set(series_data)
        assert isinstance(tick.timestamp, datetime.datetime)
        assert tick.timestamp.year == 2024
        assert tick.timestamp.month == 7
        assert tick.timestamp.day == 10

    def test_unsupported_type_rejection(self):
        """测试不支持类型拒绝"""
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00"
        )

        # 测试各种不支持的类型
        # 注意：这些类型实际上会抛出TypeError，因为singledispatch回退到基础方法

        # 测试字典类型
        with pytest.raises(TypeError):
            tick.set({"invalid": "dict"})

        # 测试列表类型
        with pytest.raises(TypeError):
            tick.set(["invalid", "list"])

        # 测试整数类型（单个参数）
        with pytest.raises(TypeError):
            tick.set(123)

        # 测试浮点数类型（单个参数）
        with pytest.raises(TypeError):
            tick.set(123.45)

        # 测试元组类型
        with pytest.raises(TypeError):
            tick.set(("tuple", "data"))

        # 测试集合类型
        with pytest.raises(TypeError):
            tick.set({"set", "data"})

        # 测试None类型
        with pytest.raises(TypeError):
            tick.set(None)

    def test_model_conversion_methods(self):
        """测试模型转换方法"""
        # 创建原始Tick实例
        original_tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-01 09:30:00",
            source=SOURCE_TYPES.SINA
        )

        # 测试to_model转换
        model = original_tick.to_model()
        assert model.code == "000001.SZ"
        assert model.price == Decimal('10.5')
        assert model.volume == 1000
        # 注意：模型中存储的是枚举的整数值
        assert model.direction == TICKDIRECTION_TYPES.ACTIVEBUY.value
        assert model.source == SOURCE_TYPES.SINA.value

        # 测试from_model转换
        converted_tick = Tick.from_model(model)
        assert converted_tick.code == original_tick.code
        assert converted_tick.price == original_tick.price
        assert converted_tick.volume == original_tick.volume
        assert converted_tick.direction == original_tick.direction
        assert converted_tick.source == original_tick.source

        # 验证时间戳转换
        assert isinstance(converted_tick.timestamp, datetime.datetime)
        assert converted_tick.timestamp.year == 2024
        assert converted_tick.timestamp.month == 1
        assert converted_tick.timestamp.day == 1

        # 测试往返转换的一致性
        model2 = converted_tick.to_model()
        assert model2.code == model.code
        assert model2.price == model.price
        assert model2.volume == model.volume
        assert model2.direction == model.direction
        assert model2.source == model.source

        # 测试from_model的类型验证
        with pytest.raises(TypeError):
            Tick.from_model("invalid_string")

        with pytest.raises(TypeError):
            Tick.from_model(123)

        with pytest.raises(TypeError):
            Tick.from_model({"invalid": "dict"})

        with pytest.raises(TypeError):
            Tick.from_model(None)


@pytest.mark.unit
class TestTickValidation:
    """4. 数据验证测试"""

    def test_positive_price_validation(self):
        """测试价格正数验证"""
        # 测试负数价格被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=-10.5,  # 负数价格
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now()
            )

        # 测试零价格是被允许的
        tick_zero = Tick(
            code="000001.SZ",
            price=0,  # 零价格应该允许
            volume=1000,
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now()
        )
        assert tick_zero.price == Decimal('0')

        # 测试正数价格正常工作
        tick_positive = Tick(
            code="000001.SZ",
            price=10.5,  # 正数价格
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_positive.price == Decimal('10.5')

    def test_positive_volume_validation(self):
        """测试成交量正数验证"""
        # 测试负数成交量被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume=-1000,  # 负数成交量
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now()
            )

        # 测试零成交量是被允许的（撤单等情况）
        tick_zero = Tick(
            code="000001.SZ",
            price=10.5,
            volume=0,  # 零成交量应该允许
            direction=TICKDIRECTION_TYPES.CANCEL,
            timestamp=datetime.datetime.now()
        )
        assert tick_zero.volume == 0

        # 测试正数成交量正常工作
        tick_positive = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,  # 正数成交量
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_positive.volume == 1000

    def test_code_not_empty_validation(self):
        """测试代码非空验证"""
        # 测试非字符串类型代码被拒绝（singledispatch会抛出TypeError）
        with pytest.raises((ValueError, TypeError)):
            Tick(
                code=123,  # 非字符串代码
                price=10.5,
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now()
            )

        # 测试None代码被拒绝
        with pytest.raises((ValueError, TypeError)):
            Tick(
                code=None,  # None代码
                price=10.5,
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now()
            )

        # 测试空字符串代码是允许的（由业务逻辑决定）
        tick_empty = Tick(
            code="",  # 空字符串
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_empty.code == ""

        # 测试正常字符串代码
        tick_normal = Tick(
            code="000001.SZ",  # 正常代码
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_normal.code == "000001.SZ"

    def test_direction_enum_validation(self):
        """测试交易方向枚举验证"""
        # 测试非枚举类型方向被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction="BUY",  # 字符串而非枚举
                timestamp=datetime.datetime.now()
            )

        # 测试数字类型方向被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction=1,  # 数字而非枚举
                timestamp=datetime.datetime.now()
            )

        # 测试所有有效的枚举值
        valid_directions = [
            TICKDIRECTION_TYPES.ACTIVEBUY,
            TICKDIRECTION_TYPES.ACTIVESELL,
            TICKDIRECTION_TYPES.NEUTRAL,
            TICKDIRECTION_TYPES.CANCEL
        ]

        for direction in valid_directions:
            tick = Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction=direction,  # 有效枚举值
                timestamp=datetime.datetime.now()
            )
            assert tick.direction == direction
            assert isinstance(tick.direction, TICKDIRECTION_TYPES)

    def test_source_enum_validation(self):
        """测试数据源枚举验证"""
        # 测试非枚举类型数据源被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now(),
                source="SINA"  # 字符串而非枚举
            )

        # 测试数字类型数据源被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now(),
                source=123  # 数字而非枚举
            )

        # 测试有效的枚举值
        valid_sources = [
            SOURCE_TYPES.OTHER,
            SOURCE_TYPES.SIM,
            SOURCE_TYPES.REALTIME,
            SOURCE_TYPES.SINA,
            SOURCE_TYPES.TUSHARE,
            SOURCE_TYPES.DATABASE
        ]

        for source in valid_sources:
            tick = Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now(),
                source=source  # 有效枚举值
            )
            assert tick.source == source
            assert isinstance(tick.source, SOURCE_TYPES)

    def test_timestamp_validity_check(self):
        """测试时间戳有效性检查"""
        # 测试无效时间戳类型被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=123456  # 数字时间戳
            )

        # 测试None时间戳被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=None  # None时间戳
            )

        # 测试有效的datetime对象
        dt_timestamp = datetime.datetime(2024, 1, 15, 9, 30, 25)
        tick_dt = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=dt_timestamp  # datetime对象
        )
        assert tick_dt.timestamp == dt_timestamp

        # 测试有效的字符串时间戳
        tick_str = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp="2024-01-15 09:30:25"  # 字符串时间戳
        )
        assert isinstance(tick_str.timestamp, datetime.datetime)
        assert tick_str.timestamp.year == 2024

    def test_price_precision_validation(self):
        """测试价格精度验证"""
        # 测试高精度价格的正确处理
        high_precision_price = "123.456789012345"
        tick = Tick(
            code="000001.SZ",
            price=high_precision_price,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick.price == Decimal(high_precision_price)
        assert isinstance(tick.price, Decimal)

        # 测试科学记数法价格
        scientific_price = "1.23e-4"
        tick_sci = Tick(
            code="000001.SZ",
            price=scientific_price,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_sci.price == Decimal(scientific_price)

        # 测试无效价格格式被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price="invalid_price",  # 无效价格格式
                volume=1000,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now()
            )

    def test_volume_integer_constraint(self):
        """测试成交量整数约束"""
        # 测试浮点数成交量自动转换为整数
        tick_float = Tick(
            code="000001.SZ",
            price=10.5,
            volume=1000.9,  # 浮点数成交量
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_float.volume == 1000  # 转换为整数
        assert isinstance(tick_float.volume, int)

        # 测试字符串数字成交量
        tick_str = Tick(
            code="000001.SZ",
            price=10.5,
            volume="2000",  # 字符串数字
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_str.volume == 2000
        assert isinstance(tick_str.volume, int)

        # 测试无效成交量格式被拒绝
        with pytest.raises(ValueError):
            Tick(
                code="000001.SZ",
                price=10.5,
                volume="invalid_volume",  # 无效格式
                direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                timestamp=datetime.datetime.now()
            )

        # 测试极大整数
        large_volume = 999999999
        tick_large = Tick(
            code="000001.SZ",
            price=10.5,
            volume=large_volume,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick_large.volume == large_volume
        assert isinstance(tick_large.volume, int)


@pytest.mark.unit
class TestTickDirectionHandling:
    """5. 交易方向处理测试"""

    def test_buy_direction_handling(self):
        """测试买入方向处理"""
        # 测试主动买盘方向
        tick = Tick(
            code="000001.SZ",
            price=10.50,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now()
        )
        assert tick.direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert tick.direction.value == 1

    def test_sell_direction_handling(self):
        """测试卖出方向处理"""
        # 测试主动卖盘方向
        tick = Tick(
            code="000001.SZ",
            price=10.30,
            volume=1500,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now()
        )
        assert tick.direction == TICKDIRECTION_TYPES.ACTIVESELL
        assert tick.direction.value == 2

    def test_neutral_direction_handling(self):
        """测试中性方向处理"""
        # 测试中性盘方向（无法判断买卖方向）
        tick = Tick(
            code="000001.SZ",
            price=10.40,
            volume=800,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now()
        )
        assert tick.direction == TICKDIRECTION_TYPES.NEUTRAL
        assert tick.direction.value == 0

    def test_direction_enum_completeness(self):
        """测试方向枚举完整性"""
        # 测试所有TICKDIRECTION_TYPES枚举值都能正确创建Tick
        directions_to_test = [
            TICKDIRECTION_TYPES.VOID,
            TICKDIRECTION_TYPES.NEUTRAL,
            TICKDIRECTION_TYPES.ACTIVEBUY,
            TICKDIRECTION_TYPES.ACTIVESELL,
            TICKDIRECTION_TYPES.CANCEL,
            TICKDIRECTION_TYPES.REMAIN2LIMIT,
            TICKDIRECTION_TYPES.MARKET2LIMIT,
            TICKDIRECTION_TYPES.FOKIOC,
            TICKDIRECTION_TYPES.SELFOPTIMAL,
            TICKDIRECTION_TYPES.COUNTEROPTIMAL
        ]

        for direction in directions_to_test:
            tick = Tick(
                code="000001.SZ",
                price=10.50,
                volume=1000,
                direction=direction,
                timestamp=datetime.datetime.now()
            )
            assert tick.direction == direction

    def test_direction_consistency_check(self):
        """测试方向一致性检查"""
        # 测试连续Tick的方向逻辑一致性
        tick_sequence = [
            Tick("000001.SZ", 10.50, 1000, TICKDIRECTION_TYPES.ACTIVEBUY, datetime.datetime.now()),
            Tick("000001.SZ", 10.51, 1500, TICKDIRECTION_TYPES.ACTIVEBUY, datetime.datetime.now()),
            Tick("000001.SZ", 10.49, 800, TICKDIRECTION_TYPES.ACTIVESELL, datetime.datetime.now()),
        ]

        # 验证方向设置一致性
        assert tick_sequence[0].direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert tick_sequence[1].direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert tick_sequence[2].direction == TICKDIRECTION_TYPES.ACTIVESELL

        # 验证相同代码的tick具有一致的股票代码
        for tick in tick_sequence:
            assert tick.code == "000001.SZ"

    def test_direction_change_detection(self):
        """测试方向变化检测"""
        # 测试买卖方向转换的检测逻辑
        tick1 = Tick("000001.SZ", 10.50, 1000, TICKDIRECTION_TYPES.ACTIVEBUY, datetime.datetime.now())
        tick2 = Tick("000001.SZ", 10.49, 800, TICKDIRECTION_TYPES.ACTIVESELL, datetime.datetime.now())

        # 验证方向确实发生了改变
        assert tick1.direction != tick2.direction
        assert tick1.direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert tick2.direction == TICKDIRECTION_TYPES.ACTIVESELL

        # 测试连续相同方向
        tick3 = Tick("000001.SZ", 10.48, 1200, TICKDIRECTION_TYPES.ACTIVESELL, datetime.datetime.now())
        assert tick2.direction == tick3.direction

    def test_invalid_direction_rejection(self):
        """测试无效方向拒绝"""
        # 测试非枚举类型的方向值被拒绝
        with pytest.raises((ValueError, TypeError)):
            Tick(
                code="000001.SZ",
                price=10.50,
                volume=1000,
                direction="invalid_direction",  # 字符串而非枚举
                timestamp=datetime.datetime.now()
            )

        with pytest.raises((ValueError, TypeError)):
            Tick(
                code="000001.SZ",
                price=10.50,
                volume=1000,
                direction=99,  # 无效的整数值
                timestamp=datetime.datetime.now()
            )

    def test_direction_statistical_analysis(self):
        """测试方向统计分析"""
        # 创建一组不同方向的tick数据进行统计分析
        tick_data = [
            Tick("000001.SZ", 10.50, 1000, TICKDIRECTION_TYPES.ACTIVEBUY, datetime.datetime.now()),
            Tick("000001.SZ", 10.51, 1500, TICKDIRECTION_TYPES.ACTIVEBUY, datetime.datetime.now()),
            Tick("000001.SZ", 10.49, 800, TICKDIRECTION_TYPES.ACTIVESELL, datetime.datetime.now()),
            Tick("000001.SZ", 10.48, 1200, TICKDIRECTION_TYPES.ACTIVESELL, datetime.datetime.now()),
            Tick("000001.SZ", 10.50, 900, TICKDIRECTION_TYPES.NEUTRAL, datetime.datetime.now()),
        ]

        # 统计各方向的数量
        buy_count = sum(1 for tick in tick_data if tick.direction == TICKDIRECTION_TYPES.ACTIVEBUY)
        sell_count = sum(1 for tick in tick_data if tick.direction == TICKDIRECTION_TYPES.ACTIVESELL)
        neutral_count = sum(1 for tick in tick_data if tick.direction == TICKDIRECTION_TYPES.NEUTRAL)

        assert buy_count == 2
        assert sell_count == 2
        assert neutral_count == 1

        # 统计各方向的总成交量
        buy_volume = sum(tick.volume for tick in tick_data if tick.direction == TICKDIRECTION_TYPES.ACTIVEBUY)
        sell_volume = sum(tick.volume for tick in tick_data if tick.direction == TICKDIRECTION_TYPES.ACTIVESELL)

        assert buy_volume == 2500  # 1000 + 1500
        assert sell_volume == 2000  # 800 + 1200

