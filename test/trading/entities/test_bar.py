"""
Bar类TDD测试

通过TDD方式开发Bar市场数据类的完整测试套件
涵盖OHLC数据处理和量化交易扩展功能
"""
import pytest
import datetime

# 导入Bar类和相关枚举 - Green阶段完成
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES, COMPONENT_TYPES


@pytest.mark.unit
class TestBarConstruction:
    """1. 构造和初始化测试"""

    def test_required_parameters_constructor(self):
        """测试必需参数构造"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 创建需要全参数的Bar
        bar = Bar(
            code="000001.SZ",
            open=10.50,
            high=11.20,
            low=10.30,
            close=11.00,
            volume=1000000,
            amount=10800000,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01 09:30:00"
        )

        # 验证所有参数正确赋值
        assert bar.code == "000001.SZ"
        assert bar.open == Decimal('10.50')
        assert bar.high == Decimal('11.20')
        assert bar.low == Decimal('10.30')
        assert bar.close == Decimal('11.00')
        assert bar.volume == 1000000
        assert bar.amount == Decimal('10800000')
        assert bar.frequency == FREQUENCY_TYPES.DAY
        assert isinstance(bar.uuid, str)
        assert len(bar.uuid) > 0

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 创建完整参数的Bar
        bar = Bar(
            code="000001.SZ",
            open=10.50,
            high=11.20,
            low=10.30,
            close=11.00,
            volume=1000000,
            amount=10800000,
            frequency=FREQUENCY_TYPES.MIN5,
            timestamp="2023-01-01 09:30:00"
        )

        # 验证所有参数正确赋值
        assert bar.code == "000001.SZ"
        assert bar.open == Decimal('10.50')
        assert bar.high == Decimal('11.20')
        assert bar.low == Decimal('10.30')
        assert bar.close == Decimal('11.00')
        assert bar.volume == 1000000
        assert bar.amount == Decimal('10800000')
        assert bar.frequency == FREQUENCY_TYPES.MIN5
        assert isinstance(bar.timestamp, datetime.datetime)
        assert bar.timestamp.year == 2023

    def test_base_class_inheritance(self):
        """测试Base类继承验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.trading.core.base import Base
        from ginkgo.enums import FREQUENCY_TYPES

        bar = Bar(
            code="000001.SZ",
            open=10.50,
            high=11.20,
            low=10.30,
            close=11.00,
            volume=1000000,
            amount=10800000,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01 09:30:00"
        )

        # 验证继承关系
        assert isinstance(bar, Base)
        # 验证UUID功能
        assert hasattr(bar, 'uuid')
        assert isinstance(bar.uuid, str)
        # 验证组件类型
        assert hasattr(bar, 'component_type')

    def test_decimal_precision_handling(self):
        """测试价格精度处理"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        bar = Bar(
            code="000001.SZ",
            open=10.123456789,
            high=11.987654321,
            low=9.555555555,
            close=10.777777777,
            volume=1000000,
            amount=10800000,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 验证价格使用Decimal类型
        assert isinstance(bar.open, Decimal)
        assert isinstance(bar.high, Decimal)
        assert isinstance(bar.low, Decimal)
        assert isinstance(bar.close, Decimal)
        # 验证精度保持
        assert bar.open == Decimal('10.123456789')

    def test_frequency_type_assignment(self):
        """测试频率类型分配"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 测试各种频率类型
        frequencies_to_test = [
            FREQUENCY_TYPES.DAY,
            FREQUENCY_TYPES.MIN1,
            FREQUENCY_TYPES.MIN5,
            FREQUENCY_TYPES.MIN15,
            FREQUENCY_TYPES.MIN30,
            FREQUENCY_TYPES.HOUR1,
            FREQUENCY_TYPES.WEEK,
            FREQUENCY_TYPES.MONTH
        ]

        for freq in frequencies_to_test:
            bar = Bar(
                code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
                volume=1000, amount=10500, frequency=freq,
                timestamp="2023-01-01"
            )
            assert bar.frequency == freq

    def test_volume_integer_conversion(self):
        """测试成交量整数转换"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 测试各种数值类型的成交量
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000.5, amount=10500, frequency=FREQUENCY_TYPES.DAY,  # 浮点数
            timestamp="2023-01-01"
        )
        assert isinstance(bar.volume, int)
        assert bar.volume == 1000

        bar2 = Bar(
            code="000002.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume="2000", amount=10500, frequency=FREQUENCY_TYPES.DAY,  # 字符串
            timestamp="2023-01-01"
        )
        assert isinstance(bar2.volume, int)
        assert bar2.volume == 2000

    def test_uuid_generation(self):
        """测试UUID生成"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 创建多个Bar，验证UUID唯一性
        bar1 = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )
        bar2 = Bar(
            code="000002.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert bar1.uuid != bar2.uuid
        assert len(bar1.uuid) > 0
        assert len(bar2.uuid) > 0
        assert isinstance(bar1.uuid, str)
        assert isinstance(bar2.uuid, str)

    def test_component_type_assignment(self):
        """测试组件类型分配"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES, COMPONENT_TYPES

        # 创建Bar实例并验证组件类型
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 验证组件类型正确分配
        assert hasattr(bar, 'component_type')
        assert bar.component_type == COMPONENT_TYPES.BAR
        assert isinstance(bar.component_type, type(COMPONENT_TYPES.BAR))

        # 验证组件类型的一致性
        bar2 = Bar(
            code="000002.SZ", open=12.0, high=13.0, low=11.0, close=12.5,
            volume=2000, amount=25000, frequency=FREQUENCY_TYPES.MIN5,
            timestamp="2023-01-01 09:30:00"
        )
        assert bar2.component_type == COMPONENT_TYPES.BAR
        assert bar.component_type == bar2.component_type

    def test_custom_uuid_assignment(self):
        """测试自定义UUID分配"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 测试自定义UUID分配
        custom_uuid = "custom-bar-uuid-12345"
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01", uuid=custom_uuid
        )

        # 验证自定义UUID正确分配
        assert bar.uuid == custom_uuid
        assert isinstance(bar.uuid, str)
        assert len(bar.uuid) > 0


@pytest.mark.unit
class TestBarProperties:
    """2. 属性访问测试"""

    def test_code_property(self):
        """测试代码属性"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert bar.code == "000001.SZ"
        assert isinstance(bar.code, str)

        # 测试不同代码格式
        bar2 = Bar(
            code="600000.SH", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )
        assert bar2.code == "600000.SH"

    def test_ohlc_properties(self):
        """测试OHLC价格属性"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        bar = Bar(
            code="000001.SZ", open=10.50, high=11.20, low=10.30, close=11.00,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 验证OHLC价格属性类型和值
        assert isinstance(bar.open, Decimal)
        assert isinstance(bar.high, Decimal)
        assert isinstance(bar.low, Decimal)
        assert isinstance(bar.close, Decimal)

        assert bar.open == Decimal('10.50')
        assert bar.high == Decimal('11.20')
        assert bar.low == Decimal('10.30')
        assert bar.close == Decimal('11.00')

        # 验证价格逻辑关系
        assert bar.high >= bar.open
        assert bar.high >= bar.close
        assert bar.low <= bar.open
        assert bar.low <= bar.close

    def test_volume_amount_properties(self):
        """测试成交量和成交额属性"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        bar = Bar(
            code="000001.SZ", open=10.50, high=11.20, low=10.30, close=11.00,
            volume=1000000, amount=10800000, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 验证成交量属性
        assert isinstance(bar.volume, int)
        assert bar.volume == 1000000

        # 验证成交额属性
        assert isinstance(bar.amount, Decimal)  # amount property now returns Decimal
        assert bar.amount == Decimal('10800000')

        # 验证成交量和成交额的合理性
        assert bar.volume > 0
        assert bar.amount > 0
        assert bar.amount >= bar.volume  # 成交额通常大于等于成交量

    def test_frequency_property(self):
        """测试频率属性"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 测试各种频率类型
        frequencies = [FREQUENCY_TYPES.DAY, FREQUENCY_TYPES.MIN5, FREQUENCY_TYPES.HOUR1]

        for freq in frequencies:
            bar = Bar(
                code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
                volume=1000, amount=10500, frequency=freq,
                timestamp="2023-01-01"
            )

            assert bar.frequency == freq
            assert isinstance(bar.frequency, FREQUENCY_TYPES)

    def test_timestamp_property(self):
        """测试时间戳属性"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        import datetime

        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01 09:30:00"
        )

        # 验证时间戳属性
        assert isinstance(bar.timestamp, datetime.datetime)
        assert bar.timestamp.year == 2023
        assert bar.timestamp.month == 1
        assert bar.timestamp.day == 1

        # 测试不同时间格式
        bar2 = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-12-31"
        )
        assert bar2.timestamp.year == 2023
        assert bar2.timestamp.month == 12

    def test_calculated_properties(self):
        """测试计算属性（涨跌幅、振幅）"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        bar = Bar(
            code="000001.SZ", open=10.0, high=11.5, low=9.5, close=10.8,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 测试涨跌额计算（close - open）
        expected_chg = Decimal('10.8') - Decimal('10.0')
        assert bar.chg == Decimal('0.8000')
        assert isinstance(bar.chg, Decimal)

        # 测试振幅计算（high - low）
        expected_amplitude = Decimal('11.5') - Decimal('9.5')
        assert bar.amplitude == Decimal('2.0000')
        assert isinstance(bar.amplitude, Decimal)

    def test_property_type_validation(self):
        """测试属性类型验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        bar = Bar(
            code="000001.SZ", open=10.5, high=11.2, low=10.3, close=11.0,
            volume=1000000, amount=10800000, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 验证所有属性的数据类型
        assert isinstance(bar.code, str)
        assert isinstance(bar.open, Decimal)
        assert isinstance(bar.high, Decimal)
        assert isinstance(bar.low, Decimal)
        assert isinstance(bar.close, Decimal)
        assert isinstance(bar.volume, int)
        assert isinstance(bar.amount, Decimal)
        assert isinstance(bar.frequency, FREQUENCY_TYPES)
        assert isinstance(bar.timestamp, datetime.datetime)
        assert isinstance(bar.chg, Decimal)
        assert isinstance(bar.amplitude, Decimal)

    def test_property_boundary_conditions(self):
        """测试属性边界条件"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 测试极小值
        bar_min = Bar(
            code="TEST", open=0.01, high=0.01, low=0.01, close=0.01,
            volume=1, amount=1, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )
        assert bar_min.open == Decimal('0.01')
        assert bar_min.volume == 1

        # 测试相同价格（无涨跌和振幅）
        assert bar_min.chg == Decimal('0.0000')
        assert bar_min.amplitude == Decimal('0.0000')


@pytest.mark.unit
class TestBarDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self):
        """测试直接参数设置"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 创建Bar后通过set方法设置参数
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 重新设置数据
        bar.set(
            "000002.SZ",  # code
            12.0,         # open
            13.0,         # high
            11.5,         # low
            12.8,         # close
            2000,         # volume
            25600,        # amount
            FREQUENCY_TYPES.MIN5,  # frequency
            "2023-01-02"  # timestamp
        )

        # 验证数据正确设置
        assert bar.code == "000002.SZ"
        assert bar.open == Decimal('12.0')
        assert bar.high == Decimal('13.0')
        assert bar.low == Decimal('11.5')
        assert bar.close == Decimal('12.8')
        assert bar.volume == 2000
        assert bar.amount == Decimal('25600')
        assert bar.frequency == FREQUENCY_TYPES.MIN5

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import pandas as pd

        # 创建pandas.Series数据
        series_data = pd.Series({
            "code": "000003.SZ",
            "open": 15.0,
            "high": 16.2,
            "low": 14.8,
            "close": 15.9,
            "volume": 3000,
            "amount": 47700,
            "frequency": FREQUENCY_TYPES.HOUR1,
            "timestamp": "2023-01-03 10:00:00"
        })

        # 创建Bar并通过Series设置
        bar = Bar(
            code="temp", open=0, high=0, low=0, close=0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="1990-01-01"
        )

        bar.set(series_data)

        # 验证从Series正确设置的数据
        assert bar.code == "000003.SZ"
        assert bar.open == Decimal('15.0')
        assert bar.high == Decimal('16.2')
        assert bar.low == Decimal('14.8')
        assert bar.close == Decimal('15.9')
        assert bar.volume == 3000
        assert bar.amount == Decimal('47700')
        assert bar.frequency == FREQUENCY_TYPES.HOUR1

    def test_singledispatch_routing(self):
        """测试方法分派路由"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        import pandas as pd

        bar = Bar(
            code="temp", open=0, high=0, low=0, close=0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="1990-01-01"
        )

        # 测试参数路由（第一个参数为str）
        bar.set("TEST1", 10.0, 11.0, 9.0, 10.5, 1000, 10500, FREQUENCY_TYPES.DAY, "2023-01-01")
        assert bar.code == "TEST1"

        # 测试Series路由
        series_data = pd.Series({
            "code": "TEST2", "open": 20.0, "high": 21.0, "low": 19.0, "close": 20.5,
            "volume": 2000, "amount": 41000, "frequency": FREQUENCY_TYPES.MIN5,
            "timestamp": "2023-01-02"
        })
        bar.set(series_data)
        assert bar.code == "TEST2"

        # 验证不同路由方式设置的数据类型一致
        assert isinstance(bar.open, type(bar.close))  # 都是Decimal
        assert isinstance(bar.volume, int)
        assert isinstance(bar.frequency, FREQUENCY_TYPES)

    def test_parameter_order_validation(self):
        """测试参数顺序验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        bar = Bar(
            code="temp", open=0, high=0, low=0, close=0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="1990-01-01"
        )

        # 测试正确的参数顺序
        bar.set("TEST", 10.0, 11.0, 9.0, 10.5, 1000, 10500, FREQUENCY_TYPES.DAY, "2023-01-01")

        assert bar.code == "TEST"
        assert bar.open.compare(bar.high) <= 0  # open <= high
        assert bar.low.compare(bar.close) <= 0  # low <= close

    def test_required_fields_validation(self):
        """测试必需字段验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        import pandas as pd

        # 测试完整字段的Series
        complete_series = pd.Series({
            "code": "000001.SZ", "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5,
            "volume": 1000, "amount": 10500, "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": "2023-01-01"
        })

        bar = Bar(
            code="temp", open=0, high=0, low=0, close=0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="1990-01-01"
        )

        bar.set(complete_series)
        assert bar.code == "000001.SZ"

    def test_decimal_conversion_accuracy(self):
        """测试Decimal转换精度"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        bar = Bar(
            code="temp", open=0, high=0, low=0, close=0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="1990-01-01"
        )

        # 测试高精度小数
        high_precision_price = 123.456789123
        bar.set("TEST", high_precision_price, high_precision_price, high_precision_price,
                high_precision_price, 1000, 123456, FREQUENCY_TYPES.DAY, "2023-01-01")

        # 验证Decimal精度保持
        assert isinstance(bar.open, Decimal)
        assert str(bar.open) == "123.456789123"

    def test_datetime_normalization_setting(self):
        """测试时间标准化设置"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        import datetime

        bar = Bar(
            code="temp", open=0, high=0, low=0, close=0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="1990-01-01"
        )

        # 测试不同时间格式的标准化
        time_formats = [
            "2023-01-01",
            "2023-01-01 09:30:00",
            datetime.datetime(2023, 1, 1, 9, 30, 0)
        ]

        for time_format in time_formats:
            bar.set("TEST", 10.0, 11.0, 9.0, 10.5, 1000, 10500, FREQUENCY_TYPES.DAY, time_format)
            assert isinstance(bar.timestamp, datetime.datetime)
            assert bar.timestamp.year == 2023

    def test_unsupported_type_rejection(self):
        """测试不支持类型拒绝"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        bar = Bar(
            code="temp", open=0, high=0, low=0, close=0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="1990-01-01"
        )

        # 测试不支持的类型（如字典）应该抛出异常
        unsupported_data = {"code": "TEST", "open": 10.0}

        try:
            bar.set(unsupported_data)
            assert False, "应该抛出NotImplementedError"
        except NotImplementedError:
            assert True  # 期望的异常


@pytest.mark.unit
class TestBarValidation:
    """4. 数据验证测试"""

    def test_ohlc_consistency_validation(self):
        """测试OHLC一致性验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 测试符合OHLC逻辑的数据
        valid_bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 验证OHLC关系
        assert valid_bar.high >= valid_bar.open    # high >= open
        assert valid_bar.high >= valid_bar.close   # high >= close
        assert valid_bar.low <= valid_bar.open     # low <= open
        assert valid_bar.low <= valid_bar.close    # low <= close
        assert valid_bar.high >= valid_bar.low     # high >= low

        # 测试边界情况：所有价格相同
        flat_bar = Bar(
            code="000002.SZ", open=10.0, high=10.0, low=10.0, close=10.0,
            volume=1000, amount=10000, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert flat_bar.high == flat_bar.low
        assert flat_bar.chg == Decimal('0.0000')
        assert flat_bar.amplitude == Decimal('0.0000')

    def test_non_negative_price_validation(self):
        """测试价格非负值验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 测试非负价格（包括0）
        zero_price_bar = Bar(
            code="000001.SZ", open=0.0, high=0.0, low=0.0, close=0.0,
            volume=0, amount=0, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert zero_price_bar.open >= Decimal('0')
        assert zero_price_bar.high >= Decimal('0')
        assert zero_price_bar.low >= Decimal('0')
        assert zero_price_bar.close >= Decimal('0')

        # 测试正常价格
        normal_bar = Bar(
            code="000002.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert all(price > Decimal('0') for price in [normal_bar.open, normal_bar.high, normal_bar.low, normal_bar.close])

    def test_volume_integer_validation(self):
        """测试成交量整数验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000.7, amount=10500, frequency=FREQUENCY_TYPES.DAY,  # 浮点数会被转换为整数
            timestamp="2023-01-01"
        )

        # 验证成交量自动转换为整数
        assert isinstance(bar.volume, int)
        assert bar.volume == 1000  # 浮点数截断

        # 验证成交量非负
        assert bar.volume >= 0

    def test_volume_amount_consistency(self):
        """测试成交量成交额基础一致性"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 测试基础数据一致性（成交额应该合理）
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # 基础验证：成交量和成交额都应该非负
        assert bar.volume >= 0
        assert bar.amount >= 0

        # 如果有成交量，通常应该有成交额（反之不一定）
        if bar.volume > 0:
            assert bar.amount >= 0

    def test_frequency_enum_validation(self):
        """测试频率枚举验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 测试有效的频率枚举
        valid_frequencies = [
            FREQUENCY_TYPES.DAY,
            FREQUENCY_TYPES.MIN5,
            FREQUENCY_TYPES.HOUR1,
            FREQUENCY_TYPES.WEEK
        ]

        for freq in valid_frequencies:
            bar = Bar(
                code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
                volume=1000, amount=10500, frequency=freq,
                timestamp="2023-01-01"
            )

            assert isinstance(bar.frequency, FREQUENCY_TYPES)
            assert bar.frequency == freq

    def test_timestamp_format_validation(self):
        """测试时间戳格式验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        import datetime

        # 测试有效的时间戳格式自动标准化
        time_formats = [
            "2023-01-01",
            "2023-01-01 09:30:00",
            datetime.datetime(2023, 1, 1, 9, 30, 0)
        ]

        for time_format in time_formats:
            bar = Bar(
                code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
                volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
                timestamp=time_format
            )

            # 验证时间戳统一转换为datetime对象
            assert isinstance(bar.timestamp, datetime.datetime)
            assert bar.timestamp.year == 2023
            assert bar.timestamp.month == 1

    def test_code_not_empty_validation(self):
        """测试代码基础验证"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES

        # 测试非空代码
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert isinstance(bar.code, str)
        assert len(bar.code) > 0
        assert bar.code == "000001.SZ"

        # 测试代码格式合理性
        valid_codes = ["000001.SZ", "600000.SH", "399001.SZ", "AAPL"]
        for code in valid_codes:
            bar = Bar(
                code=code, open=10.0, high=11.0, low=9.0, close=10.5,
                volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
                timestamp="2023-01-01"
            )
            assert bar.code == code

    def test_boundary_value_handling(self):
        """测试边界值处理"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 测试极小值
        min_bar = Bar(
            code="MIN_TEST", open=0.01, high=0.01, low=0.01, close=0.01,
            volume=1, amount=0.01, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert min_bar.open == Decimal('0.01')
        assert min_bar.volume == 1

        # 测试相对大的值
        max_bar = Bar(
            code="MAX_TEST", open=9999.99, high=9999.99, low=9999.99, close=9999.99,
            volume=999999999, amount=9999999999.99, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        assert max_bar.open == Decimal('9999.99')
        assert max_bar.volume == 999999999

        # 测试精度保持
        precision_bar = Bar(
            code="PRECISION_TEST", open=123.456789, high=123.456789,
            low=123.456789, close=123.456789, volume=1000, amount=123456.789,
            frequency=FREQUENCY_TYPES.DAY, timestamp="2023-01-01"
        )

        assert str(precision_bar.open) == "123.456789"


@pytest.mark.unit
class TestBarTechnicalCalculations:
    """5. 技术指标计算测试"""

    def test_change_calculation(self):
        """测试涨跌额计算"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 测试正常涨跌额计算
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.0, low=9.5, close=10.8,
            volume=1000, amount=10800, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # chg = close - open = 10.8 - 10.0 = 0.8
        expected_chg = Decimal('0.8000')
        assert bar.chg == expected_chg
        assert isinstance(bar.chg, Decimal)

        # 测试下跌情况
        down_bar = Bar(
            code="000002.SZ", open=10.0, high=10.2, low=9.0, close=9.5,
            volume=1000, amount=9500, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # chg = close - open = 9.5 - 10.0 = -0.5
        expected_down_chg = Decimal('-0.5000')
        assert down_bar.chg == expected_down_chg

        # 测试无变化情况
        flat_bar = Bar(
            code="000003.SZ", open=10.0, high=10.0, low=10.0, close=10.0,
            volume=1000, amount=10000, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # chg = close - open = 10.0 - 10.0 = 0.0
        assert flat_bar.chg == Decimal('0.0000')

    def test_amplitude_calculation(self):
        """测试振幅计算"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 测试正常振幅计算
        bar = Bar(
            code="000001.SZ", open=10.0, high=11.5, low=9.2, close=10.8,
            volume=1000, amount=10800, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # amplitude = high - low = 11.5 - 9.2 = 2.3
        expected_amplitude = Decimal('2.3000')
        assert bar.amplitude == expected_amplitude
        assert isinstance(bar.amplitude, Decimal)

        # 测试小振幅情况
        small_bar = Bar(
            code="000002.SZ", open=10.0, high=10.1, low=9.95, close=10.05,
            volume=1000, amount=10050, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # amplitude = high - low = 10.1 - 9.95 = 0.15
        expected_small_amplitude = Decimal('0.1500')
        assert small_bar.amplitude == expected_small_amplitude

        # 测试无振幅情况（一字板）
        flat_bar = Bar(
            code="000003.SZ", open=10.0, high=10.0, low=10.0, close=10.0,
            volume=1000, amount=10000, frequency=FREQUENCY_TYPES.DAY,
            timestamp="2023-01-01"
        )

        # amplitude = high - low = 10.0 - 10.0 = 0.0
        assert flat_bar.amplitude == Decimal('0.0000')

    def test_percentage_change_calculation(self):
        """测试涨跌幅计算"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常涨跌幅计算
        bar = Bar(
            code="000001.SZ", open=10, high=11, low=9, close=11,
            volume=1000, amount=10500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 测试涨幅：(11-10)/10 * 100 = 10%
        expected_pct_chg = (Decimal('11') - Decimal('10')) / Decimal('10') * 100
        assert bar.pct_chg == Decimal('10.0000')
        assert isinstance(bar.pct_chg, Decimal)

        # 测试跌幅：(9-10)/10 * 100 = -10%
        bar_down = Bar(
            code="000002.SZ", open=10, high=10.5, low=9, close=9,
            volume=1000, amount=9500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert bar_down.pct_chg == Decimal('-10.0000')

        # 测试开盘价为0的边界情况
        bar_zero_open = Bar(
            code="000003.SZ", open=0, high=1, low=0, close=1,
            volume=1000, amount=500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert bar_zero_open.pct_chg == Decimal('0')

        # 测试无变化情况：(10-10)/10 * 100 = 0%
        bar_no_change = Bar(
            code="000004.SZ", open=10, high=10.2, low=9.8, close=10,
            volume=1000, amount=10000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert bar_no_change.pct_chg == Decimal('0.0000')

    def test_middle_price_calculation(self):
        """测试中间价计算"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常中间价计算
        bar = Bar(
            code="000001.SZ", open=10, high=12, low=8, close=11,
            volume=1000, amount=10500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 测试中间价：(12 + 8) / 2 = 10
        expected_middle_price = (Decimal('12') + Decimal('8')) / 2
        assert bar.middle_price == Decimal('10.0000')
        assert isinstance(bar.middle_price, Decimal)

        # 测试小数中间价
        bar_decimal = Bar(
            code="000002.SZ", open=10.5, high=11.25, low=9.75, close=10.8,
            volume=1000, amount=10650,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (11.25 + 9.75) / 2 = 10.5
        assert bar_decimal.middle_price == Decimal('10.5000')

        # 测试高低价相等的情况
        bar_equal = Bar(
            code="000003.SZ", open=10, high=10, low=10, close=10,
            volume=1000, amount=10000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (10 + 10) / 2 = 10
        assert bar_equal.middle_price == Decimal('10.0000')

    def test_typical_price_calculation(self):
        """测试典型价计算"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常典型价计算
        bar = Bar(
            code="000001.SZ", open=10, high=12, low=9, close=11,
            volume=1000, amount=10500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 测试典型价：(12 + 9 + 11) / 3 = 32/3 = 10.6667
        expected_typical_price = (Decimal('12') + Decimal('9') + Decimal('11')) / 3
        assert bar.typical_price == Decimal('10.6667')
        assert isinstance(bar.typical_price, Decimal)

        # 测试整数典型价
        bar_integer = Bar(
            code="000002.SZ", open=10, high=15, low=6, close=9,
            volume=1000, amount=10000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (15 + 6 + 9) / 3 = 30/3 = 10
        assert bar_integer.typical_price == Decimal('10.0000')

        # 测试小数典型价
        bar_decimal = Bar(
            code="000003.SZ", open=10.5, high=11.5, low=9.5, close=10.2,
            volume=1000, amount=10350,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (11.5 + 9.5 + 10.2) / 3 = 31.2/3 = 10.4
        assert bar_decimal.typical_price == Decimal('10.4000')

        # 测试所有价格相等的情况
        bar_equal = Bar(
            code="000004.SZ", open=10, high=10, low=10, close=10,
            volume=1000, amount=10000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (10 + 10 + 10) / 3 = 10
        assert bar_equal.typical_price == Decimal('10.0000')

    def test_weighted_price_calculation(self):
        """测试加权价计算"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常加权价计算
        bar = Bar(
            code="000001.SZ", open=10, high=12, low=8, close=11,
            volume=1000, amount=10500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 测试加权价：(12 + 8 + 2*11) / 4 = (12 + 8 + 22) / 4 = 42/4 = 10.5
        expected_weighted_price = (Decimal('12') + Decimal('8') + 2 * Decimal('11')) / 4
        assert bar.weighted_price == Decimal('10.5000')
        assert isinstance(bar.weighted_price, Decimal)

        # 测试整数加权价
        bar_integer = Bar(
            code="000002.SZ", open=10, high=16, low=8, close=10,
            volume=1000, amount=10200,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (16 + 8 + 2*10) / 4 = (16 + 8 + 20) / 4 = 44/4 = 11
        assert bar_integer.weighted_price == Decimal('11.0000')

        # 测试小数加权价
        bar_decimal = Bar(
            code="000003.SZ", open=10.5, high=11.5, low=9.5, close=10.25,
            volume=1000, amount=10375,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (11.5 + 9.5 + 2*10.25) / 4 = (11.5 + 9.5 + 20.5) / 4 = 41.5/4 = 10.375
        assert bar_decimal.weighted_price == Decimal('10.3750')

        # 测试所有价格相等的情况
        bar_equal = Bar(
            code="000004.SZ", open=10, high=10, low=10, close=10,
            volume=1000, amount=10000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (10 + 10 + 2*10) / 4 = 40/4 = 10
        assert bar_equal.weighted_price == Decimal('10.0000')

        # 测试收盘价权重影响
        bar_close_impact = Bar(
            code="000005.SZ", open=10, high=12, low=8, close=9,
            volume=1000, amount=9750,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # (12 + 8 + 2*9) / 4 = (12 + 8 + 18) / 4 = 38/4 = 9.5
        # 注意：收盘价较低时，加权价比中间价低
        assert bar_close_impact.weighted_price == Decimal('9.5000')
        assert bar_close_impact.middle_price == Decimal('10.0000')  # (12+8)/2 = 10

    def test_calculation_precision_maintenance(self):
        """测试计算精度保持"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试精确的小数计算
        bar = Bar(
            code="000001.SZ", open=10.123, high=10.789, low=9.567, close=10.456,
            volume=1000000, amount=10456789.123,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证所有计算属性保持4位小数精度
        assert str(bar.chg).split('.')[-1] == '3330'  # 10.456 - 10.123 = 0.3330
        assert str(bar.amplitude).split('.')[-1] == '2220'  # 10.789 - 9.567 = 1.2220
        assert str(bar.middle_price).split('.')[-1] == '1780'  # (10.789 + 9.567) / 2 = 10.1780

        # 验证百分比计算精度（最多4位小数）
        pct_chg_str = str(bar.pct_chg)
        decimal_places = len(pct_chg_str.split('.')[-1]) if '.' in pct_chg_str else 0
        assert decimal_places <= 4, f"百分比涨跌幅精度应不超过4位小数，实际为{decimal_places}位"

        # 验证typical_price和weighted_price的精度
        typical_str = str(bar.typical_price)
        weighted_str = str(bar.weighted_price)
        typical_decimal = len(typical_str.split('.')[-1]) if '.' in typical_str else 0
        weighted_decimal = len(weighted_str.split('.')[-1]) if '.' in weighted_str else 0

        assert typical_decimal <= 4, f"典型价格精度应不超过4位小数，实际为{typical_decimal}位"
        assert weighted_decimal <= 4, f"加权价格精度应不超过4位小数，实际为{weighted_decimal}位"

    def test_zero_division_handling(self):
        """测试除零处理"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试开盘价为0的情况 - pct_chg应该返回0而不是抛出异常
        bar_zero_open = Bar(
            code="000001.SZ", open=0, high=5, low=0, close=3,
            volume=1000, amount=1500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 百分比涨跌幅：开盘价为0时应返回0
        assert bar_zero_open.pct_chg == Decimal('0')
        assert isinstance(bar_zero_open.pct_chg, Decimal)

        # 其他计算属性应该正常工作
        assert bar_zero_open.chg == Decimal('3.0000')  # close - open = 3 - 0 = 3
        assert bar_zero_open.amplitude == Decimal('5.0000')  # high - low = 5 - 0 = 5
        assert bar_zero_open.middle_price == Decimal('2.5000')  # (5 + 0) / 2 = 2.5
        assert bar_zero_open.typical_price == Decimal('2.6667')  # (5 + 0 + 3) / 3 = 8/3
        assert bar_zero_open.weighted_price == Decimal('2.7500')  # (5 + 0 + 2*3) / 4 = 11/4

        # 测试极小开盘价（接近但不等于0）
        bar_tiny_open = Bar(
            code="000002.SZ", open=0.0001, high=1, low=0.0001, close=0.5,
            volume=1000, amount=250,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 应该能正常计算百分比涨跌幅：(0.5 - 0.0001) / 0.0001 * 100 = 499900%
        expected_pct_chg = (Decimal('0.5') - Decimal('0.0001')) / Decimal('0.0001') * 100
        # 由于精度限制，验证其为非常大的正数
        assert bar_tiny_open.pct_chg > Decimal('400000')
        assert isinstance(bar_tiny_open.pct_chg, Decimal)

        # 测试开盘价和收盘价都为0的情况
        bar_both_zero = Bar(
            code="000003.SZ", open=0, high=1, low=0, close=0,
            volume=1000, amount=500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 百分比涨跌幅应该返回0（没有变化）
        assert bar_both_zero.pct_chg == Decimal('0')
        assert bar_both_zero.chg == Decimal('0.0000')  # 0 - 0 = 0

        # 验证不会抛出ZeroDivisionError异常
        try:
            _ = bar_zero_open.pct_chg
            _ = bar_both_zero.pct_chg
            division_error_occurred = False
        except ZeroDivisionError:
            division_error_occurred = True

        assert not division_error_occurred, "除零错误不应该发生，应该返回安全的默认值"

    def test_decimal_calculation_accuracy(self):
        """测试Decimal计算精度"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal, getcontext
        import datetime

        # 设置高精度上下文进行测试
        original_precision = getcontext().prec
        getcontext().prec = 28

        try:
            # 使用精确的Decimal值创建Bar
            bar = Bar(
                code="000001.SZ",
                open=Decimal('10.123456789'),
                high=Decimal('10.987654321'),
                low=Decimal('9.555555555'),
                close=Decimal('10.777777777'),
                volume=1000000,
                amount=Decimal('10777777.123456789'),
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime.datetime.now()
            )

            # 验证所有价格属性使用Decimal类型
            assert isinstance(bar.open, Decimal)
            assert isinstance(bar.high, Decimal)
            assert isinstance(bar.low, Decimal)
            assert isinstance(bar.close, Decimal)
            assert isinstance(bar.amount, Decimal)

            # 验证计算属性也使用Decimal类型
            assert isinstance(bar.chg, Decimal)
            assert isinstance(bar.pct_chg, Decimal)
            assert isinstance(bar.amplitude, Decimal)
            assert isinstance(bar.middle_price, Decimal)
            assert isinstance(bar.typical_price, Decimal)
            assert isinstance(bar.weighted_price, Decimal)

            # 验证精确计算结果
            expected_chg = Decimal('10.777777777') - Decimal('10.123456789')
            assert bar.chg == expected_chg.quantize(Decimal('0.0001'))

            expected_amplitude = Decimal('10.987654321') - Decimal('9.555555555')
            assert bar.amplitude == expected_amplitude.quantize(Decimal('0.0001'))

            # 验证Decimal计算避免了浮点数精度误差
            # Bar类的chg属性使用Decimal计算并四舍五入到4位小数
            # 验证计算结果是Decimal类型且精度正确
            assert isinstance(bar.chg, Decimal), "chg应该是Decimal类型"

            # 验证精确计算：使用Decimal避免浮点误差
            # 手动计算期望值并比较
            expected_chg = (Decimal('10.777777777') - Decimal('10.123456789')).quantize(Decimal('0.0001'))
            assert bar.chg == expected_chg, f"chg计算结果应为{expected_chg}，实际为{bar.chg}"

        finally:
            # 恢复原始精度设置
            getcontext().prec = original_precision


@pytest.mark.unit
class TestBarDataQuality:
    """6. 数据质量测试"""

    def test_zero_price_detection(self):
        """测试零价格检测"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常价格 - 应该没有零价格问题
        normal_bar = Bar(
            code="000001.SZ", open=10, high=12, low=9, close=11,
            volume=1000, amount=10500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证正常价格没有零值
        assert normal_bar.open > 0
        assert normal_bar.high > 0
        assert normal_bar.low > 0
        assert normal_bar.close > 0

        # 测试开盘价为0的情况（异常但允许）
        zero_open_bar = Bar(
            code="000002.SZ", open=0, high=5, low=0, close=3,
            volume=1000, amount=1500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证零开盘价被正确记录
        assert zero_open_bar.open == 0
        assert zero_open_bar.high > 0
        assert zero_open_bar.close > 0

        # 测试最低价为0的情况（停牌或特殊情况）
        zero_low_bar = Bar(
            code="000003.SZ", open=1, high=5, low=0, close=3,
            volume=1000, amount=2000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证零最低价被正确记录
        assert zero_low_bar.low == 0
        assert zero_low_bar.open > 0
        assert zero_low_bar.high > 0
        assert zero_low_bar.close > 0

        # 测试所有价格都为0的极端情况（数据错误）
        all_zero_bar = Bar(
            code="000004.SZ", open=0, high=0, low=0, close=0,
            volume=0, amount=0,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证全零价格被正确记录（虽然异常）
        assert all_zero_bar.open == 0
        assert all_zero_bar.high == 0
        assert all_zero_bar.low == 0
        assert all_zero_bar.close == 0

        # 验证零价格不会影响计算属性的安全性
        assert zero_open_bar.pct_chg == Decimal('0')  # 除零保护
        assert zero_open_bar.amplitude == Decimal('5.0000')  # 正常计算
        assert all_zero_bar.amplitude == Decimal('0.0000')  # 零振幅

    def test_negative_price_detection(self):
        """测试负价格检测"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常正价格
        normal_bar = Bar(
            code="000001.SZ", open=10, high=12, low=9, close=11,
            volume=1000, amount=10500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证所有价格都为正数
        assert normal_bar.open > 0
        assert normal_bar.high > 0
        assert normal_bar.low > 0
        assert normal_bar.close > 0

        # 测试负开盘价情况（数据错误）
        negative_open_bar = Bar(
            code="000002.SZ", open=-1, high=5, low=-1, close=3,
            volume=1000, amount=1500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证负价格被正确记录（不拒绝，让上层处理）
        assert negative_open_bar.open < 0
        assert negative_open_bar.low < 0
        assert negative_open_bar.high > 0
        assert negative_open_bar.close > 0

        # 测试负最高价（极端数据错误）
        negative_high_bar = Bar(
            code="000003.SZ", open=1, high=-2, low=-5, close=0,
            volume=1000, amount=500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证负最高价被记录
        assert negative_high_bar.high < 0
        assert negative_high_bar.low < 0
        assert negative_high_bar.open > 0
        assert negative_high_bar.close == 0

        # 测试所有价格都为负的极端情况
        all_negative_bar = Bar(
            code="000004.SZ", open=-10, high=-5, low=-15, close=-8,
            volume=1000, amount=0,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证全负价格被记录
        assert all_negative_bar.open < 0
        assert all_negative_bar.high < 0
        assert all_negative_bar.low < 0
        assert all_negative_bar.close < 0

        # 验证负价格情况下计算属性的行为
        # chg = -8 - (-10) = 2 (可以为正，表示"负向减少")
        assert all_negative_bar.chg == Decimal('2.0000')

        # amplitude = -5 - (-15) = 10 (振幅始终为正)
        assert all_negative_bar.amplitude == Decimal('10.0000')

        # pct_chg = ((-8) - (-10)) / (-10) * 100 = 2 / (-10) * 100 = -20%
        assert all_negative_bar.pct_chg == Decimal('-20.0000')

        # 验证Bar作为数据容器不拒绝负价格，保持数据原样
        # 数据质量控制应该在上层业务逻辑中处理

    def test_extreme_price_jump_detection(self):
        """测试极端价格跳跃检测"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常涨跌幅（5%以内）
        normal_bar = Bar(
            code="000001.SZ", open=10, high=10.5, low=9.5, close=10.3,
            volume=1000000, amount=10300000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert abs(normal_bar.pct_chg) <= Decimal('5.0'), "正常涨跌幅应在合理范围内"

        # 测试轻度异常涨跌幅（10%左右）
        moderate_jump_bar = Bar(
            code="000002.SZ", open=10, high=11.2, low=8.8, close=11,
            volume=2000000, amount=22000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert moderate_jump_bar.pct_chg == Decimal('10.0000'), "轻度异常涨幅计算正确"
        assert moderate_jump_bar.amplitude == Decimal('2.4000'), "振幅计算正确"

        # 测试极端价格跳跃（涨停20%）
        extreme_up_bar = Bar(
            code="000003.SZ", open=10, high=12, low=10, close=12,
            volume=5000000, amount=60000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert extreme_up_bar.pct_chg == Decimal('20.0000'), "涨停板涨幅计算正确"
        assert extreme_up_bar.amplitude == Decimal('2.0000'), "涨停板振幅计算正确"

        # 测试极端价格跳跃（跌停-10%）
        extreme_down_bar = Bar(
            code="000004.SZ", open=10, high=10, low=9, close=9,
            volume=8000000, amount=72000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert extreme_down_bar.pct_chg == Decimal('-10.0000'), "跌停板涨幅计算正确"
        assert extreme_down_bar.amplitude == Decimal('1.0000'), "跌停板振幅计算正确"

        # 测试超极端情况（上市首日或重组）
        super_extreme_bar = Bar(
            code="000005.SZ", open=1, high=5, low=0.5, close=4.5,
            volume=10000000, amount=45000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert super_extreme_bar.pct_chg == Decimal('350.0000'), "超极端涨幅计算正确"
        assert super_extreme_bar.amplitude == Decimal('4.5000'), "超极端振幅计算正确"

        # 验证Bar作为数据容器能正确存储所有情况
        # 对极端情况的业务判断应在上层逻辑中处理
        bars_with_extreme_changes = [moderate_jump_bar, extreme_up_bar, extreme_down_bar, super_extreme_bar]
        for bar in bars_with_extreme_changes:
            assert isinstance(bar.pct_chg, Decimal), "所有涨跌幅计算结果应为Decimal类型"
            assert bar.volume >= 0, "成交量应为非负数"

    def test_zero_volume_with_price_change(self):
        """测试零成交量但有价格变动"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常情况：有成交量且有价格变动
        normal_bar = Bar(
            code="000001.SZ", open=10, high=12, low=9, close=11,
            volume=1000, amount=10500,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证正常交易情况
        assert normal_bar.volume > 0
        assert normal_bar.chg != 0  # 有价格变动
        assert normal_bar.amount > 0

        # 测试异常情况：零成交量但有价格变动（停牌复牌、技术调整等）
        zero_volume_with_change_bar = Bar(
            code="000002.SZ", open=10, high=11, low=9, close=10.5,
            volume=0, amount=0,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证异常情况被正确记录
        assert zero_volume_with_change_bar.volume == 0
        assert zero_volume_with_change_bar.amount == Decimal('0')
        assert zero_volume_with_change_bar.chg == Decimal('0.5000')  # 有价格变动
        assert zero_volume_with_change_bar.pct_chg == Decimal('5.0000')  # 5%涨幅

        # 测试零成交量但价格无变动（正常停牌）
        zero_volume_no_change_bar = Bar(
            code="000003.SZ", open=10, high=10, low=10, close=10,
            volume=0, amount=0,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证停牌情况
        assert zero_volume_no_change_bar.volume == 0
        assert zero_volume_no_change_bar.amount == Decimal('0')
        assert zero_volume_no_change_bar.chg == Decimal('0.0000')  # 无价格变动
        assert zero_volume_no_change_bar.pct_chg == Decimal('0.0000')  # 无涨跌幅

        # 测试极端情况：零成交量但有大幅价格变动（重大消息、技术调整）
        zero_volume_big_change_bar = Bar(
            code="000004.SZ", open=10, high=15, low=8, close=12,
            volume=0, amount=0,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )

        # 验证极端异常情况
        assert zero_volume_big_change_bar.volume == 0
        assert zero_volume_big_change_bar.amount == Decimal('0')
        assert zero_volume_big_change_bar.chg == Decimal('2.0000')  # +2元
        assert zero_volume_big_change_bar.pct_chg == Decimal('20.0000')  # +20%
        assert zero_volume_big_change_bar.amplitude == Decimal('7.0000')  # 振幅7元

        # 验证计算属性在零成交量情况下仍能正常工作
        assert zero_volume_with_change_bar.middle_price == Decimal('10.0000')
        assert zero_volume_with_change_bar.typical_price == Decimal('10.1667')
        assert zero_volume_with_change_bar.weighted_price == Decimal('10.2500')

        # 注意：Bar作为数据容器不判断业务合理性
        # 零成交量但有价格变动的业务逻辑检查应在上层处理

    def test_abnormal_volume_detection(self):
        """测试异常成交量检测"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常成交量
        normal_volume_bar = Bar(
            code="000001.SZ", open=10, high=10.5, low=9.5, close=10.2,
            volume=1000000, amount=10200000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert normal_volume_bar.volume == 1000000, "正常成交量记录正确"
        assert normal_volume_bar.amount == Decimal('10200000'), "正常成交金额记录正确"

        # 测试成交量异常放大（平常的10倍）
        huge_volume_bar = Bar(
            code="000002.SZ", open=10, high=11, low=9.8, close=10.8,
            volume=10000000, amount=108000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert huge_volume_bar.volume == 10000000, "异常大成交量记录正确"
        # 验证成交量与成交金额的合理性（简单校验）
        avg_price = huge_volume_bar.amount / huge_volume_bar.volume
        assert Decimal('9.8') <= avg_price <= Decimal('11'), "成交量与金额应在价格范围内"

        # 测试极小成交量（几手）
        tiny_volume_bar = Bar(
            code="000003.SZ", open=10, high=10.1, low=9.9, close=10,
            volume=100, amount=1000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert tiny_volume_bar.volume == 100, "极小成交量记录正确"
        assert tiny_volume_bar.amount == Decimal('1000'), "极小成交金额记录正确"

        # 测试零成交量（停牌）
        zero_volume_bar = Bar(
            code="000004.SZ", open=10, high=10, low=10, close=10,
            volume=0, amount=0,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert zero_volume_bar.volume == 0, "零成交量记录正确"
        assert zero_volume_bar.amount == Decimal('0'), "零成交金额记录正确"

        # 测试不合理的成交量和金额组合（金额过低）
        unrealistic_amount_bar = Bar(
            code="000005.SZ", open=10, high=10.5, low=9.5, close=10.2,
            volume=1000000, amount=100,  # 不合理的低金额
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # Bar作为数据容器不判断合理性，只存储数据
        assert unrealistic_amount_bar.volume == 1000000
        assert unrealistic_amount_bar.amount == Decimal('100')

        # 验证所有volume值都为非负整数
        volume_bars = [normal_volume_bar, huge_volume_bar, tiny_volume_bar, zero_volume_bar, unrealistic_amount_bar]
        for bar in volume_bars:
            assert isinstance(bar.volume, int), f"成交量应为整数类型，实际为{type(bar.volume)}"
            assert bar.volume >= 0, f"成交量应为非负数，实际为{bar.volume}"
            assert isinstance(bar.amount, Decimal), f"成交金额应为Decimal类型，实际为{type(bar.amount)}"

    def test_data_completeness_check(self):
        """测试数据完整性检查"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试完整数据
        complete_bar = Bar(
            code="000001.SZ", open=10, high=11, low=9, close=10.5,
            volume=1000000, amount=10500000,
            frequency=FREQUENCY_TYPES.DAY, timestamp="2023-01-01 09:30:00"
        )

        # 验证所有必要字段存在且非空
        assert hasattr(complete_bar, 'code') and complete_bar.code is not None, "code字段不能为空"
        assert hasattr(complete_bar, 'open') and complete_bar.open is not None, "open字段不能为空"
        assert hasattr(complete_bar, 'high') and complete_bar.high is not None, "high字段不能为空"
        assert hasattr(complete_bar, 'low') and complete_bar.low is not None, "low字段不能为空"
        assert hasattr(complete_bar, 'close') and complete_bar.close is not None, "close字段不能为空"
        assert hasattr(complete_bar, 'volume') and complete_bar.volume is not None, "volume字段不能为空"
        assert hasattr(complete_bar, 'amount') and complete_bar.amount is not None, "amount字段不能为空"
        assert hasattr(complete_bar, 'frequency') and complete_bar.frequency is not None, "frequency字段不能为空"
        assert hasattr(complete_bar, 'timestamp') and complete_bar.timestamp is not None, "timestamp字段不能为空"

        # 验证继承的Base类字段
        assert hasattr(complete_bar, 'uuid') and complete_bar.uuid is not None, "uuid字段不能为空"
        assert hasattr(complete_bar, 'component_type'), "component_type字段应存在"

        # 验证数据类型的正确性
        assert isinstance(complete_bar.code, str), "code应为字符串类型"
        assert isinstance(complete_bar.open, Decimal), "open应为Decimal类型"
        assert isinstance(complete_bar.high, Decimal), "high应为Decimal类型"
        assert isinstance(complete_bar.low, Decimal), "low应为Decimal类型"
        assert isinstance(complete_bar.close, Decimal), "close应为Decimal类型"
        assert isinstance(complete_bar.volume, int), "volume应为整数类型"
        assert isinstance(complete_bar.amount, Decimal), "amount应为Decimal类型"
        assert isinstance(complete_bar.timestamp, datetime.datetime), "timestamp应为datetime类型"

        # 验证计算属性的可访问性（不会抛出异常）
        calculated_properties = [
            'chg', 'pct_chg', 'amplitude', 'middle_price', 'typical_price', 'weighted_price'
        ]
        for prop in calculated_properties:
            assert hasattr(complete_bar, prop), f"计算属性{prop}应存在"
            value = getattr(complete_bar, prop)
            assert value is not None, f"计算属性{prop}不应为None"
            assert isinstance(value, Decimal), f"计算属性{prop}应为Decimal类型"

    def test_statistical_outlier_detection(self):
        """测试统计异常值检测"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime
        import statistics
        import math

        # 创建一组正常数据作为基准
        normal_data = [
            (10.0, 10.5, 9.5, 10.2, 1000000),
            (10.2, 10.8, 9.8, 10.6, 1100000),
            (10.6, 11.0, 10.0, 10.8, 950000),
            (10.8, 11.2, 10.2, 11.0, 1200000),
            (11.0, 11.5, 10.5, 11.3, 1050000),
        ]

        bars = []
        for i, (open_p, high_p, low_p, close_p, vol) in enumerate(normal_data):
            bar = Bar(
                code=f"00000{i+1}.SZ", open=open_p, high=high_p, low=low_p, close=close_p,
                volume=vol, amount=vol * close_p,
                frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
            )
            bars.append(bar)

        # 计算正常数据的统计指标
        closes = [float(bar.close) for bar in bars]
        volumes = [bar.volume for bar in bars]

        close_mean = statistics.mean(closes)
        close_std = statistics.stdev(closes)
        volume_mean = statistics.mean(volumes)
        volume_std = statistics.stdev(volumes)

        # 验证正常数据在3σ范围内
        for bar in bars:
            close_z_score = abs((float(bar.close) - close_mean) / close_std)
            volume_z_score = abs((bar.volume - volume_mean) / volume_std)

            assert close_z_score < 3, f"正常数据的价格Z分数应小于3，实际为{close_z_score:.2f}"
            assert volume_z_score < 3, f"正常数据的成交量Z分数应小于3，实际为{volume_z_score:.2f}"

        # 测试价格异常值（远超过3σ）
        price_outlier_bar = Bar(
            code="OUTLIER1.SZ", open=10, high=20, low=8, close=18,  # 价格异常高
            volume=1000000, amount=18000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        price_outlier_z = abs((float(price_outlier_bar.close) - close_mean) / close_std)
        assert price_outlier_z > 3, f"价格异常值的Z分数应大于3，实际为{price_outlier_z:.2f}"

        # 测试成交量异常值（远超过3σ）
        volume_outlier_bar = Bar(
            code="OUTLIER2.SZ", open=10, high=10.5, low=9.5, close=10.2,
            volume=5000000, amount=51000000,  # 成交量异常高
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        volume_outlier_z = abs((volume_outlier_bar.volume - volume_mean) / volume_std)
        assert volume_outlier_z > 3, f"成交量异常值的Z分数应大于3，实际为{volume_outlier_z:.2f}"

        # 测试极端低值异常
        extreme_low_bar = Bar(
            code="OUTLIER3.SZ", open=10, high=10.1, low=9.9, close=0.1,  # 极端低价
            volume=100, amount=10,  # 极端低成交量
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        low_price_z = abs((float(extreme_low_bar.close) - close_mean) / close_std)
        low_volume_z = abs((extreme_low_bar.volume - volume_mean) / volume_std)
        assert low_price_z > 3, f"极端低价的Z分数应大于3，实际为{low_price_z:.2f}"
        assert low_volume_z > 3, f"极端低成交量的Z分数应大于3，实际为{low_volume_z:.2f}"

        # 验证异常值也能正常存储和计算
        outlier_bars = [price_outlier_bar, volume_outlier_bar, extreme_low_bar]
        for bar in outlier_bars:
            assert isinstance(bar.chg, Decimal), "异常值数据也应能正常计算涨跌幅"
            assert isinstance(bar.pct_chg, Decimal), "异常值数据也应能正常计算百分比涨跌幅"

    def test_price_volume_correlation_check(self):
        """测试价格成交量相关性检查"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试正常相关性：价格上涨成交量放大
        price_up_volume_up_bar = Bar(
            code="000001.SZ", open=10, high=12, low=9.8, close=11.5,
            volume=2000000, amount=23000000,  # 高成交量对应价格上涨
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert price_up_volume_up_bar.pct_chg > 0, "价格上涨时涨幅应为正数"
        assert price_up_volume_up_bar.volume > 1000000, "价格上涨时成交量应放大"
        # 验证平均成交价格在合理范围内
        avg_price = price_up_volume_up_bar.amount / price_up_volume_up_bar.volume
        assert price_up_volume_up_bar.low <= avg_price <= price_up_volume_up_bar.high, "平均成交价应在高低价范围内"

        # 测试正常相关性：价格下跌成交量放大
        price_down_volume_up_bar = Bar(
            code="000002.SZ", open=10, high=10.2, low=8.5, close=9,
            volume=3000000, amount=27000000,  # 高成交量对应价格下跌
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert price_down_volume_up_bar.pct_chg < 0, "价格下跌时涨幅应为负数"
        assert price_down_volume_up_bar.volume > 1000000, "价格下跌时成交量也可放大（恭慌抛售）"

        # 测试正常相关性：价格横盘成交量缩小
        price_flat_volume_low_bar = Bar(
            code="000003.SZ", open=10, high=10.1, low=9.9, close=10,
            volume=500000, amount=5000000,  # 低成交量对应价格横盘
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert abs(price_flat_volume_low_bar.pct_chg) < Decimal('2'), "横盘时涨跌幅应很小"
        assert price_flat_volume_low_bar.volume < 1000000, "横盘时成交量应相对较小"

        # 测试异常相关性：价格大涨但成交量很小（可能的操纵或数据错误）
        abnormal_correlation_bar = Bar(
            code="000004.SZ", open=10, high=15, low=9.5, close=14,
            volume=1000, amount=14000,  # 大涨但成交量很小
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert abnormal_correlation_bar.pct_chg == Decimal('40.0000'), "大涨幅计算正确"
        assert abnormal_correlation_bar.volume < 10000, "成交量确实很小"
        # Bar作为数据容器不判断合理性，但能正确记录这种异常情况

        # 测试另一种异常：成交量很大但价格没有变化（大单对冲）
        big_volume_no_change_bar = Bar(
            code="000005.SZ", open=10, high=10.05, low=9.95, close=10,
            volume=10000000, amount=100000000,  # 巨大成交量但价格无变化
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        assert abs(big_volume_no_change_bar.pct_chg) < Decimal('1'), "大量对冲时价格变化很小"
        assert big_volume_no_change_bar.volume > 5000000, "对冲时成交量很大"

        # 验证所有情况下的基本计算都能正常运行
        all_bars = [
            price_up_volume_up_bar, price_down_volume_up_bar, price_flat_volume_low_bar,
            abnormal_correlation_bar, big_volume_no_change_bar
        ]
        for bar in all_bars:
            # 验证所有数据都能正常访问和计算
            assert isinstance(bar.middle_price, Decimal), "中间价计算正常"
            assert isinstance(bar.typical_price, Decimal), "典型价计算正常"
            assert isinstance(bar.weighted_price, Decimal), "加权价计算正常"
            # 验证成交金额与成交量的一致性
            if bar.volume > 0:
                calc_avg_price = bar.amount / bar.volume
                assert bar.low <= calc_avg_price <= bar.high, f"\n平均价{calc_avg_price}应在高低价范围[{bar.low}, {bar.high}]内"

    def test_data_repair_strategies(self):
        """测试数据修复策略"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal
        import datetime

        # 测试数据修复的基本原则：Bar作为数据容器不修复数据，只存储原始数据
        # 数据修复应在上层业务逻辑中处理

        # 测试异常数据1：高低价倒置
        inverted_bar = Bar(
            code="BAD001.SZ", open=10, high=8, low=12, close=9,  # high < low 的异常情况
            volume=1000000, amount=9000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # Bar不修复数据，原样存储
        assert inverted_bar.high == Decimal('8')
        assert inverted_bar.low == Decimal('12')
        # 但计算属性仍能正常工作（可能结果为负数）
        assert inverted_bar.amplitude == Decimal('-4.0000')  # 8 - 12 = -4
        assert inverted_bar.middle_price == Decimal('10.0000')  # (8 + 12) / 2 = 10

        # 测试异常数据2：收盘价超出高低价范围
        out_of_range_bar = Bar(
            code="BAD002.SZ", open=10, high=11, low=9, close=12,  # close > high
            volume=1000000, amount=12000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # Bar不修复数据，原样存储
        assert out_of_range_bar.close == Decimal('12')
        assert out_of_range_bar.high == Decimal('11')
        # 计算属性仍能正常工作
        assert out_of_range_bar.chg == Decimal('2.0000')  # 12 - 10 = 2
        assert out_of_range_bar.pct_chg == Decimal('20.0000')  # (12-10)/10*100 = 20%

        # 测试异常数据3：负数价格
        negative_price_bar = Bar(
            code="BAD003.SZ", open=10, high=12, low=-5, close=8,  # 负数最低价
            volume=1000000, amount=8000000,
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # Bar不修复数据，原样存储
        assert negative_price_bar.low == Decimal('-5')
        # 计算属性仍能正常工作
        assert negative_price_bar.amplitude == Decimal('17.0000')  # 12 - (-5) = 17
        assert negative_price_bar.middle_price == Decimal('3.5000')  # (12 + (-5)) / 2 = 3.5

        # 测试异常数据4：成交金额与成交量不匹配
        mismatched_amount_bar = Bar(
            code="BAD004.SZ", open=10, high=11, low=9, close=10.5,
            volume=1000000, amount=1000,  # 金额过小，不匹配成交量
            frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.datetime.now()
        )
        # Bar不修复数据，原样存储
        assert mismatched_amount_bar.volume == 1000000
        assert mismatched_amount_bar.amount == Decimal('1000')
        # 计算属性仍能正常工作
        assert mismatched_amount_bar.chg == Decimal('0.5000')

        # 测试数据完整性保持：所有异常数据都能被完整保存
        bad_bars = [inverted_bar, out_of_range_bar, negative_price_bar, mismatched_amount_bar]
        for bar in bad_bars:
            # 验证所有属性都可访问，不会抛出异常
            assert hasattr(bar, 'code') and bar.code is not None
            assert hasattr(bar, 'open') and bar.open is not None
            assert hasattr(bar, 'high') and bar.high is not None
            assert hasattr(bar, 'low') and bar.low is not None
            assert hasattr(bar, 'close') and bar.close is not None
            assert hasattr(bar, 'volume') and bar.volume is not None
            assert hasattr(bar, 'amount') and bar.amount is not None

            # 验证计算属性不会抛出异常
            try:
                _ = bar.chg
                _ = bar.pct_chg
                _ = bar.amplitude
                _ = bar.middle_price
                _ = bar.typical_price
                _ = bar.weighted_price
                calculation_successful = True
            except Exception as e:
                calculation_successful = False
                assert False, f"计算属性不应抛出异常：{e}"

            assert calculation_successful, "所有计算属性都应能正常计算"

        # 总结：Bar类的设计原则是作为纯粹的数据容器
        # 不进行数据验证或修复，保持数据的原始性和完整性
        # 数据质量检查和修复应在上层业务逻辑中实现
