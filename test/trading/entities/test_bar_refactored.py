"""
Bar类测试 - Refactored

使用pytest最佳实践重构的Bar测试套件
包括fixtures共享、参数化测试和清晰的测试分组
"""
import pytest
import datetime
from decimal import Decimal

from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES, COMPONENT_TYPES


@pytest.mark.unit
class TestBarConstruction:
    """1. 构造和初始化测试"""

    def test_required_parameters(self, sample_bar_data):
        """测试必需参数构造"""
        bar = Bar(**sample_bar_data)

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

    def test_base_class_inheritance(self, sample_bar_data):
        """测试Base类继承验证"""
        from ginkgo.trading.core.base import Base

        bar = Bar(**sample_bar_data)
        assert isinstance(bar, Base)
        assert hasattr(bar, 'uuid')
        assert hasattr(bar, 'component_type')

    def test_component_type_assignment(self, sample_bar_data):
        """测试组件类型分配"""
        bar = Bar(**sample_bar_data)
        assert bar.component_type == COMPONENT_TYPES.BAR

    def test_uuid_generation(self, sample_bar_data):
        """测试UUID生成和唯一性"""
        bar1 = Bar(**sample_bar_data)
        bar2 = Bar(**sample_bar_data)

        assert bar1.uuid != bar2.uuid
        assert len(bar1.uuid) > 0
        assert len(bar2.uuid) > 0

    def test_custom_uuid(self, sample_bar_data):
        """测试自定义UUID"""
        custom_uuid = "custom-bar-uuid-123"
        sample_bar_data['uuid'] = custom_uuid

        bar = Bar(**sample_bar_data)
        assert bar.uuid == custom_uuid

    @pytest.mark.parametrize("freq", [
        FREQUENCY_TYPES.MIN1,
        FREQUENCY_TYPES.MIN5,
        FREQUENCY_TYPES.MIN15,
        FREQUENCY_TYPES.MIN30,
        FREQUENCY_TYPES.HOUR1,
        FREQUENCY_TYPES.WEEK,
        FREQUENCY_TYPES.MONTH
    ])
    def test_various_frequencies(self, sample_bar_data, freq):
        """测试各种频率类型"""
        sample_bar_data['frequency'] = freq
        bar = Bar(**sample_bar_data)
        assert bar.frequency == freq

    @pytest.mark.parametrize("volume,expected", [
            (1000.5, 1000),  # 浮点数截断
            ("2000", 2000),   # 字符串转换
            (3000, 3000),     # 整数
    ])
    def test_volume_integer_conversion(self, sample_bar_data, volume, expected):
        """测试成交量整数转换"""
        sample_bar_data['volume'] = volume
        bar = Bar(**sample_bar_data)
        assert isinstance(bar.volume, int)
        assert bar.volume == expected

    @pytest.mark.parametrize("price_value,expected", [
            (10.123456789, Decimal('10.123456789')),
            ("15.75", Decimal('15.75')),
            (20, Decimal('20')),
    ])
    def test_decimal_precision(self, sample_bar_data, price_value, expected):
        """测试价格精度保持"""
        sample_bar_data.update({
            'open': price_value,
            'high': price_value,
            'low': price_value,
            'close': price_value
        })
        bar = Bar(**sample_bar_data)
        assert bar.open == expected


@pytest.mark.unit
class TestBarProperties:
    """2. 属性访问测试"""

    def test_code_property(self, sample_bar_data):
        """测试代码属性"""
        bar = Bar(**sample_bar_data)
        assert bar.code == "000001.SZ"
        assert isinstance(bar.code, str)

    def test_ohlc_properties(self, sample_bar_data):
        """测试OHLC价格属性"""
        bar = Bar(**sample_bar_data)

        assert isinstance(bar.open, Decimal)
        assert isinstance(bar.high, Decimal)
        assert isinstance(bar.low, Decimal)
        assert isinstance(bar.close, Decimal)

        assert bar.open == Decimal('10.50')
        assert bar.high == Decimal('11.20')
        assert bar.low == Decimal('10.30')
        assert bar.close == Decimal('11.00')

    def test_volume_amount_properties(self, sample_bar_data):
        """测试成交量和成交额属性"""
        bar = Bar(**sample_bar_data)

        assert isinstance(bar.volume, int)
        assert bar.volume == 1000000
        assert isinstance(bar.amount, Decimal)
        assert bar.amount == Decimal('10800000')

    def test_calculated_properties(self, sample_bar_data):
        """测试计算属性（涨跌幅、振幅）"""
        bar = Bar(**sample_bar_data)

        # chg = close - open = 11.00 - 10.50 = 0.50
        assert bar.chg == Decimal('0.5000')
        assert isinstance(bar.chg, Decimal)

        # amplitude = high - low = 11.20 - 10.30 = 0.90
        assert bar.amplitude == Decimal('0.9000')
        assert isinstance(bar.amplitude, Decimal)

    @pytest.mark.parametrize("open_p,high_p,low_p,close_p,expected_chg", [
            (10.0, 11.5, 9.5, 10.8, Decimal('0.8000')),
            (10.0, 10.2, 9.0, 9.5, Decimal('-0.5000')),
            (10.0, 10.0, 10.0, 10.0, Decimal('0.0000')),
    ])
    def test_change_calculation(self, sample_bar_data, open_p, high_p, low_p, close_p, expected_chg):
        """测试涨跌额计算"""
        sample_bar_data.update({
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p
        })
        bar = Bar(**sample_bar_data)
        assert bar.chg == expected_chg

    @pytest.mark.parametrize("high_p,low_p,expected_amplitude", [
            (11.5, 9.2, Decimal('2.3000')),
            (10.1, 9.95, Decimal('0.1500')),
            (10.0, 10.0, Decimal('0.0000')),
    ])
    def test_amplitude_calculation(self, sample_bar_data, high_p, low_p, expected_amplitude):
        """测试振幅计算"""
        sample_bar_data.update({
            'open': 10.0,
            'high': high_p,
            'low': low_p,
            'close': 10.8
        })
        bar = Bar(**sample_bar_data)
        assert bar.amplitude == expected_amplitude


@pytest.mark.unit
class TestBarDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self, sample_bar_data):
        """测试直接参数设置"""
        bar = Bar(**sample_bar_data)

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
            "2024-01-02"  # timestamp
        )

        assert bar.code == "000002.SZ"
        assert bar.open == Decimal('12.0')
        assert bar.high == Decimal('13.0')
        assert bar.low == Decimal('11.5')
        assert bar.close == Decimal('12.8')
        assert bar.volume == 2000
        assert bar.amount == Decimal('25600')
        assert bar.frequency == FREQUENCY_TYPES.MIN5

    def test_pandas_series_setting(self, sample_bar_data):
        """测试pandas.Series设置"""
        import pandas as pd

        bar = Bar(**sample_bar_data)

        series_data = pd.Series({
            "code": "000003.SZ",
            "open": 15.0,
            "high": 16.2,
            "low": 14.8,
            "close": 15.9,
            "volume": 3000,
            "amount": 47700,
            "frequency": FREQUENCY_TYPES.HOUR1,
            "timestamp": "2024-01-03 10:00:00"
        })

        bar.set(series_data)

        assert bar.code == "000003.SZ"
        assert bar.open == Decimal('15.0')
        assert bar.high == Decimal('16.2')
        assert bar.low == Decimal('14.8')
        assert bar.close == Decimal('15.9')
        assert bar.volume == 3000
        assert bar.amount == Decimal('47700')
        assert bar.frequency == FREQUENCY_TYPES.HOUR1


@pytest.mark.unit
class TestBarValidation:
    """4. 数据验证测试"""

    def test_ohlc_consistency(self, sample_bar_data):
        """测试OHLC一致性验证"""
        bar = Bar(**sample_bar_data)

        # 验证OHLC关系
        assert bar.high >= bar.open
        assert bar.high >= bar.close
        assert bar.low <= bar.open
        assert bar.low <= bar.close
        assert bar.high >= bar.low

    def test_volume_integer_validation(self, sample_bar_data):
        """测试成交量整数验证"""
        sample_bar_data['volume'] = 1000.7
        bar = Bar(**sample_bar_data)

        assert isinstance(bar.volume, int)
        assert bar.volume == 1000
        assert bar.volume >= 0

    def test_frequency_enum_validation(self, sample_bar_data):
        """测试频率枚举验证"""
        valid_frequencies = [
            FREQUENCY_TYPES.DAY,
            FREQUENCY_TYPES.MIN5,
            FREQUENCY_TYPES.HOUR1,
            FREQUENCY_TYPES.WEEK
        ]

        for freq in valid_frequencies:
            sample_bar_data['frequency'] = freq
            bar = Bar(**sample_bar_data)
            assert isinstance(bar.frequency, FREQUENCY_TYPES)
            assert bar.frequency == freq

    @pytest.mark.parametrize("time_format", [
            "2024-01-01",
            "2024-01-01 09:30:00",
            datetime.datetime(2024, 1, 1, 9, 30, 0)
    ])
    def test_timestamp_format_validation(self, sample_bar_data, time_format):
        """测试时间戳格式验证"""
        sample_bar_data['timestamp'] = time_format
        bar = Bar(**sample_bar_data)

        assert isinstance(bar.timestamp, datetime.datetime)
        assert bar.timestamp.year == 2024
        assert bar.timestamp.month == 1


@pytest.mark.unit
class TestBarTechnicalCalculations:
    """5. 技术指标计算测试"""

    @pytest.mark.parametrize("open_p,high_p,low_p,close_p,expected_pct", [
            (10, 12, 8, 11, Decimal('10.0000')),
            (10, 10.5, 9.5, 9, Decimal('-10.0000')),
            (10, 10, 10, 10, Decimal('0.0000')),
            (0, 5, 0, 3, Decimal('0')),
    ])
    def test_percentage_change(self, sample_bar_data, open_p, high_p, low_p, close_p, expected_pct):
        """测试涨跌幅计算"""
        sample_bar_data.update({
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p
        })
        bar = Bar(**sample_bar_data)
        assert bar.pct_chg == expected_pct

    def test_middle_price(self, sample_bar_data):
        """测试中间价计算"""
        sample_bar_data.update({
            'open': 10,
            'high': 12,
            'low': 8,
            'close': 11
        })
        bar = Bar(**sample_bar_data)
        # (12 + 8) / 2 = 10
        assert bar.middle_price == Decimal('10.0000')

    def test_typical_price(self, sample_bar_data):
        """测试典型价计算"""
        sample_bar_data.update({
            'open': 10,
            'high': 12,
            'low': 9,
            'close': 11
        })
        bar = Bar(**sample_bar_data)
        # (12 + 9 + 11) / 3 = 10.6667
        assert bar.typical_price == Decimal('10.6667')

    def test_weighted_price(self, sample_bar_data):
        """测试加权价计算"""
        sample_bar_data.update({
            'open': 10,
            'high': 12,
            'low': 8,
            'close': 11
        })
        bar = Bar(**sample_bar_data)
        # (12 + 8 + 2*11) / 4 = 10.5
        assert bar.weighted_price == Decimal('10.5000')


@pytest.mark.unit
class TestBarDataQuality:
    """6. 数据质量测试"""

    @pytest.mark.parametrize("open_p,high_p,low_p,close_p,volume,amount", [
            (0, 0, 0, 0, 0, 0),           # 全零
            (10, 12, 9, 11, 1000000, 11000000),  # 正常
            (10, 15, 5, 12, 5000000, 60000000),  # 大幅波动
    ])
    def test_extreme_values(self, sample_bar_data, open_p, high_p, low_p, close_p, volume, amount):
        """测试极值处理"""
        sample_bar_data.update({
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
            'volume': volume,
            'amount': amount
        })
        bar = Bar(**sample_bar_data)

        # 验证数据正确存储
        assert bar.open == Decimal(str(open_p))
        assert bar.high == Decimal(str(high_p))
        assert bar.low == Decimal(str(low_p))
        assert bar.close == Decimal(str(close_p))
        assert bar.volume == volume
        assert bar.amount == Decimal(str(amount))

    def test_high_precision_prices(self, sample_bar_data):
        """测试高精度价格处理"""
        sample_bar_data.update({
            'open': Decimal('10.123456789'),
            'high': Decimal('10.987654321'),
            'low': Decimal('9.555555555'),
            'close': Decimal('10.777777777'),
        })
        bar = Bar(**sample_bar_data)

        assert isinstance(bar.open, Decimal)
        assert str(bar.open) == "10.123456789"
        assert isinstance(bar.chg, Decimal)
        assert isinstance(bar.pct_chg, Decimal)

    @pytest.mark.parametrize("vol,amt", [
            (1000000, 10200000),
            (10000000, 108000000),
            (100, 1000),
            (0, 0),
    ])
    def test_volume_amount_consistency(self, sample_bar_data, vol, amt):
        """测试成交量成交额一致性"""
        sample_bar_data.update({
            'volume': vol,
            'amount': amt
        })
        bar = Bar(**sample_bar_data)

        assert bar.volume >= 0
        assert bar.amount >= 0
        if bar.volume > 0:
            assert bar.amount >= 0


@pytest.mark.unit
class TestBarEdgeCases:
    """7. 边界情况测试"""

    def test_zero_prices(self, sample_bar_data):
        """测试零价格处理"""
        sample_bar_data.update({
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0
        })
        bar = Bar(**sample_bar_data)

        assert bar.open == Decimal('0')
        assert bar.high == Decimal('0')
        assert bar.low == Decimal('0')
        assert bar.close == Decimal('0')
        assert bar.chg == Decimal('0.0000')
        assert bar.amplitude == Decimal('0.0000')

    def test_same_prices(self, sample_bar_data):
        """测试相同价格（一字板）"""
        sample_bar_data.update({
            'open': 10,
            'high': 10,
            'low': 10,
            'close': 10
        })
        bar = Bar(**sample_bar_data)

        assert bar.chg == Decimal('0.0000')
        assert bar.amplitude == Decimal('0.0000')
        assert bar.middle_price == Decimal('10.0000')

    def test_inverted_high_low(self, sample_bar_data):
        """测试高低价倒置（数据异常）"""
        sample_bar_data.update({
            'open': 10,
            'high': 8,
            'low': 12,
            'close': 9
        })
        bar = Bar(**sample_bar_data)

        # Bar不修复数据，原样存储
        assert bar.high == Decimal('8')
        assert bar.low == Decimal('12')
        # 计算属性仍能工作（结果为负）
        assert bar.amplitude == Decimal('-4.0000')


@pytest.mark.integration
class TestBarDatabaseOperations:
    """8. 数据库操作测试"""

    def test_bar_to_model_conversion(self, sample_bar_data, ginkgo_config):
        """测试Bar到Model的转换"""
        bar = Bar(**sample_bar_data)
        model = bar.to_model()

        assert model.code == bar.code
        assert model.open == bar.open
        assert model.high == bar.high
        assert model.low == bar.low
        assert model.close == bar.close
        assert model.volume == bar.volume
        assert model.amount == bar.amount

    def test_bar_from_model_conversion(self, sample_bar_data, ginkgo_config):
        """测试Model到Bar的转换"""
        bar1 = Bar(**sample_bar_data)
        model = bar1.to_model()
        bar2 = Bar.from_model(model)

        assert bar2.code == bar1.code
        assert bar2.open == bar1.open
        assert bar2.high == bar1.high
        assert bar2.low == bar1.low
        assert bar2.close == bar1.close
        assert bar2.volume == bar1.volume
