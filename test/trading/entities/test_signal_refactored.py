"""
Signal类测试 - Refactored

使用pytest最佳实践重构的Signal测试套件
包括fixtures共享、参数化测试和清晰的测试分组
"""
import pytest
import datetime
from decimal import Decimal

from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    COMPONENT_TYPES
)


@pytest.mark.unit
class TestSignalConstruction:
    """1. 构造和初始化测试"""

    def test_required_parameters(self, sample_signal_data):
        """测试必需参数构造"""
        signal = Signal(**sample_signal_data)

        assert signal.portfolio_id == "test_portfolio"
        assert signal.code == "000001.SZ"
        assert signal.direction == DIRECTION_TYPES.LONG
        assert isinstance(signal.uuid, str)

    def test_base_class_inheritance(self, sample_signal_data):
        """测试Base类继承验证"""
        from ginkgo.trading.core.base import Base

        signal = Signal(**sample_signal_data)
        assert isinstance(signal, Base)
        assert hasattr(signal, 'uuid')
        assert hasattr(signal, 'component_type')

    def test_component_type_assignment(self, sample_signal_data):
        """测试组件类型分配"""
        signal = Signal(**sample_signal_data)
        assert signal.component_type == COMPONENT_TYPES.SIGNAL

    def test_uuid_generation(self, sample_signal_data):
        """测试UUID生成和唯一性"""
        signal1 = Signal(**sample_signal_data)
        signal2 = Signal(**sample_signal_data)

        assert signal1.uuid != signal2.uuid
        assert len(signal1.uuid) > 0
        assert len(signal2.uuid) > 0

    def test_custom_uuid(self, sample_signal_data):
        """测试自定义UUID"""
        custom_uuid = "custom-signal-uuid-456"
        sample_signal_data['uuid'] = custom_uuid

        signal = Signal(**sample_signal_data)
        assert signal.uuid == custom_uuid

    @pytest.mark.parametrize("direction", [
        DIRECTION_TYPES.LONG,
        DIRECTION_TYPES.SHORT
    ])
    def test_direction_types(self, sample_signal_data, direction):
        """测试交易方向类型"""
        sample_signal_data['direction'] = direction
        signal = Signal(**sample_signal_data)
        assert signal.direction == direction

    @pytest.mark.parametrize("reason", [
        None,
        "MA Crossover",
        "RSI Oversold",
        "Breakout",
        ""
    ])
    def test_reason_parameter(self, sample_signal_data, reason):
        """测试原因参数"""
        sample_signal_data['reason'] = reason
        signal = Signal(**sample_signal_data)
        assert signal.reason == reason


@pytest.mark.unit
class TestSignalProperties:
    """2. 属性访问测试"""

    def test_portfolio_id_validation(self, sample_signal_data):
        """测试portfolio_id验证"""
        signal = Signal(**sample_signal_data)
        assert signal.portfolio_id == "test_portfolio"
        assert isinstance(signal.portfolio_id, str)

        # 无效类型
        sample_signal_data['portfolio_id'] = 123
        with pytest.raises(Exception):
            Signal(**sample_signal_data)

        # 空字符串
        sample_signal_data['portfolio_id'] = ""
        with pytest.raises(Exception):
            Signal(**sample_signal_data)

    def test_code_validation(self, sample_signal_data):
        """测试code验证"""
        signal = Signal(**sample_signal_data)
        assert signal.code == "000001.SZ"
        assert isinstance(signal.code, str)

    def test_direction_validation(self, sample_signal_data):
        """测试direction验证"""
        # 有效方向
        for direction in [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT]:
            sample_signal_data['direction'] = direction
            signal = Signal(**sample_signal_data)
            assert signal.direction == direction

        # 无效方向
        sample_signal_data['direction'] = "INVALID"
        with pytest.raises(Exception):
            Signal(**sample_signal_data)

    def test_timestamp_validation(self, sample_signal_data):
        """测试timestamp验证"""
        # datetime对象
        dt = datetime.datetime(2024, 1, 1, 10, 30, 0)
        sample_signal_data['timestamp'] = dt
        signal = Signal(**sample_signal_data)
        assert signal.timestamp == dt

        # 字符串时间
        time_str = "2024-01-01 10:30:00"
        sample_signal_data['timestamp'] = time_str
        signal = Signal(**sample_signal_data)
        assert isinstance(signal.timestamp, datetime.datetime)


@pytest.mark.unit
class TestSignalSourceManagement:
    """3. 数据源管理测试"""

    def test_default_source(self, sample_signal_data):
        """测试默认数据源"""
        signal = Signal(**sample_signal_data)
        assert signal.source == SOURCE_TYPES.OTHER

    @pytest.mark.parametrize("source", [
        SOURCE_TYPES.SIM,
        SOURCE_TYPES.REALTIME,
        SOURCE_TYPES.BACKTEST,
        SOURCE_TYPES.STRATEGY,
        SOURCE_TYPES.DATABASE
    ])
    def test_various_sources(self, sample_signal_data, source):
        """测试各种数据源"""
        sample_signal_data['source'] = source
        signal = Signal(**sample_signal_data)
        assert signal.source == source

    def test_invalid_source(self, sample_signal_data):
        """测试无效数据源"""
        sample_signal_data['source'] = "INVALID_SOURCE"
        with pytest.raises(Exception):
            Signal(**sample_signal_data)


@pytest.mark.unit
class TestSignalBusinessLogic:
    """4. 信号业务逻辑测试"""

    @pytest.mark.parametrize("direction,expected", [
        (DIRECTION_TYPES.LONG, 1),
        (DIRECTION_TYPES.SHORT, 2)
    ])
    def test_direction_value(self, sample_signal_data, direction, expected):
        """测试方向枚举值"""
        sample_signal_data['direction'] = direction
        signal = Signal(**sample_signal_data)
        assert signal.direction.value == expected

    @pytest.mark.parametrize("direction,should_buy", [
        (DIRECTION_TYPES.LONG, True),
        (DIRECTION_TYPES.SHORT, False)
    ])
    def test_buy_sell_decision(self, sample_signal_data, direction, should_buy):
        """测试买卖决策"""
        sample_signal_data['direction'] = direction
        signal = Signal(**sample_signal_data)

        if should_buy:
            assert signal.direction == DIRECTION_TYPES.LONG
        else:
            assert signal.direction == DIRECTION_TYPES.SHORT

    def test_signal_with_reason(self, sample_signal_data):
        """测试带原因的信号"""
        sample_signal_data['reason'] = "Golden Cross"
        signal = Signal(**sample_signal_data)

        assert signal.reason == "Golden Cross"
        assert isinstance(signal.reason, str)

    def test_signal_without_reason(self, sample_signal_data):
        """测试不带原因的信号"""
        sample_signal_data['reason'] = None
        signal = Signal(**sample_signal_data)

        assert signal.reason is None

    @pytest.mark.parametrize("reason", [
        "Moving Average Crossover",
        "RSI < 30",
        "Price > Upper Bollinger Band",
        "Volume Spike"
    ])
    def test_various_reasons(self, sample_signal_data, reason):
        """测试各种信号原因"""
        sample_signal_data['reason'] = reason
        signal = Signal(**sample_signal_data)
        assert signal.reason == reason


@pytest.mark.unit
class TestSignalEdgeCases:
    """5. 边界情况测试"""

    def test_same_code_different_directions(self, sample_signal_data):
        """测试相同代码不同方向"""
        sample_signal_data['direction'] = DIRECTION_TYPES.LONG
        long_signal = Signal(**sample_signal_data)

        sample_signal_data['direction'] = DIRECTION_TYPES.SHORT
        short_signal = Signal(**sample_signal_data)

        assert long_signal.code == short_signal.code
        assert long_signal.direction != short_signal.direction

    def test_multiple_signals_same_time(self, sample_signal_data):
        """测试同一时间多个信号"""
        timestamp = datetime.datetime(2024, 1, 1, 10, 30, 0)

        sample_signal_data['timestamp'] = timestamp
        sample_signal_data['direction'] = DIRECTION_TYPES.LONG
        signal1 = Signal(**sample_signal_data)

        sample_signal_data['timestamp'] = timestamp
        sample_signal_data['direction'] = DIRECTION_TYPES.SHORT
        signal2 = Signal(**sample_signal_data)

        assert signal1.timestamp == signal2.timestamp
        assert signal1.direction != signal2.direction

    def test_signal_with_empty_reason(self, sample_signal_data):
        """测试空原因字符串"""
        sample_signal_data['reason'] = ""
        signal = Signal(**sample_signal_data)
        assert signal.reason == ""

    @pytest.mark.parametrize("code", [
        "000001.SZ",
        "600000.SH",
        "300001.SZ",
        "AAPL",
        "BTC/USD"
    ])
    def test_various_codes(self, sample_signal_data, code):
        """测试各种股票代码"""
        sample_signal_data['code'] = code
        signal = Signal(**sample_signal_data)
        assert signal.code == code


@pytest.mark.unit
class TestSignalDataSetting:
    """6. 数据设置测试"""

    def test_direct_parameter_setting(self, sample_signal_data):
        """测试直接参数设置"""
        signal = Signal(**sample_signal_data)

        # 重新设置
        signal.set(
            "updated_portfolio",
            "updated_engine",
            "updated_run",
            "000002.SZ",
            DIRECTION_TYPES.SHORT
        )

        assert signal.portfolio_id == "updated_portfolio"
        assert signal.code == "000002.SZ"
        assert signal.direction == DIRECTION_TYPES.SHORT

    def test_pandas_series_setting(self, sample_signal_data):
        """测试pandas.Series设置"""
        import pandas as pd

        signal = Signal(**sample_signal_data)

        series_data = pd.Series({
            'portfolio_id': 'SERIES_PORTFOLIO',
            'engine_id': 'SERIES_ENGINE',
            'run_id': 'SERIES_RUN',
            'code': '000002.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'reason': 'Test Signal'
        })

        signal.set(series_data)

        assert signal.portfolio_id == 'SERIES_PORTFOLIO'
        assert signal.code == '000002.SZ'
        assert signal.direction == DIRECTION_TYPES.SHORT


@pytest.mark.integration
class TestSignalDatabaseOperations:
    """7. 数据库操作测试"""

    def test_signal_to_model(self, sample_signal_data, ginkgo_config):
        """测试Signal到Model的转换"""
        signal = Signal(**sample_signal_data)
        model = signal.to_model()

        assert model.portfolio_id == signal.portfolio_id
        assert model.code == signal.code
        assert model.direction == signal.direction.value

    def test_signal_from_model(self, sample_signal_data, ginkgo_config):
        """测试Model到Signal的转换"""
        signal1 = Signal(**sample_signal_data)
        model = signal1.to_model()
        signal2 = Signal.from_model(model)

        assert signal2.portfolio_id == signal1.portfolio_id
        assert signal2.code == signal1.code
        assert signal2.direction == signal1.direction


@pytest.mark.unit
class TestSignalValidation:
    """8. 信号验证测试"""

    @pytest.mark.parametrize("invalid_data", [
        {"portfolio_id": None, "code": "000001.SZ", "direction": DIRECTION_TYPES.LONG},
        {"portfolio_id": "", "code": "000001.SZ", "direction": DIRECTION_TYPES.LONG},
        {"portfolio_id": "test", "code": None, "direction": DIRECTION_TYPES.LONG},
        {"portfolio_id": "test", "code": "", "direction": DIRECTION_TYPES.LONG},
        {"portfolio_id": "test", "code": "000001.SZ", "direction": None},
    ])
    def test_invalid_parameters(self, invalid_data):
        """测试无效参数"""
        with pytest.raises(Exception):
            Signal(**invalid_data)

    def test_empty_portfolio_id(self, sample_signal_data):
        """测试空portfolio_id"""
        sample_signal_data['portfolio_id'] = ""
        with pytest.raises(Exception):
            Signal(**sample_signal_data)

    def test_empty_code(self, sample_signal_data):
        """测试空code"""
        sample_signal_data['code'] = ""
        with pytest.raises(Exception):
            Signal(**sample_signal_data)


@pytest.mark.financial
class TestSignalBusinessScenarios:
    """9. 业务场景测试"""

    def test_long_signal_creation(self, sample_signal_data):
        """测试创建做多信号"""
        sample_signal_data['direction'] = DIRECTION_TYPES.LONG
        sample_signal_data['reason'] = "MA Golden Cross"

        signal = Signal(**sample_signal_data)

        assert signal.direction == DIRECTION_TYPES.LONG
        assert signal.reason == "MA Golden Cross"

    def test_short_signal_creation(self, sample_signal_data):
        """测试创建做空信号"""
        sample_signal_data['direction'] = DIRECTION_TYPES.SHORT
        sample_signal_data['reason'] = "Break Support Level"

        signal = Signal(**sample_signal_data)

        assert signal.direction == DIRECTION_TYPES.SHORT
        assert signal.reason == "Break Support Level"

    @pytest.mark.parametrize("reason", [
        "5-day MA crosses above 20-day MA",
        "RSI drops below 30",
        "Price breaks above resistance",
        "Volume > 2x average volume"
    ])
    def test_strategy_reasons(self, sample_signal_data, reason):
        """测试策略原因"""
        sample_signal_data['reason'] = reason
        signal = Signal(**sample_signal_data)
        assert signal.reason == reason
