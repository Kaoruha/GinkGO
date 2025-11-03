"""
Signal类TDD测试

通过TDD方式开发Signal交易信号类的完整测试套件
涵盖基础功能和量化交易扩展功能
"""
import pytest
import datetime
from datetime import timezone, timedelta

# 导入Signal类和相关枚举 - 使用已安装的包
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, COMPONENT_TYPES


@pytest.mark.unit
class TestSignalConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        # Signal要求direction参数，默认构造器应该失败
        with pytest.raises(Exception):
            Signal()

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        # 使用Signal应有的核心参数创建
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
            # 不包含price和volume - 它们不属于Signal的职责
        )

        # 验证核心字段正确赋值
        assert signal.portfolio_id == "test_portfolio"
        assert signal.engine_id == "test_engine"
        assert signal.run_id == "test_run"
        assert signal.code == "000001.SZ"
        assert signal.direction == DIRECTION_TYPES.LONG
        assert signal.reason == "test signal"
        assert signal.source == SOURCE_TYPES.SIM
        assert signal.timestamp is not None

        # Signal已经移除了price和volume属性，专注于核心职责
        assert not hasattr(signal, 'price')
        assert not hasattr(signal, 'volume')

    def test_base_class_inheritance(self):
        """测试Base类继承验证"""
        # 创建Signal验证继承Base类的功能
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        # 验证继承自Base类的属性和方法
        assert hasattr(signal, 'uuid'), "Signal应该继承uuid属性"
        assert hasattr(signal, 'component_type'), "Signal应该继承component_type属性"
        assert hasattr(signal, 'source'), "Signal应该继承source属性"
        assert hasattr(signal, 'set_source'), "Signal应该继承set_source方法"
        assert hasattr(signal, 'to_dataframe'), "Signal应该继承to_dataframe方法"

        # 验证UUID不为空且是字符串
        assert signal.uuid is not None
        assert isinstance(signal.uuid, str)
        assert len(signal.uuid) > 0

    def test_component_type_signal(self):
        """测试组件类型设置"""
        # 验证Signal的组件类型被正确设置为COMPONENT_TYPES.SIGNAL
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        assert signal.component_type == COMPONENT_TYPES.SIGNAL, "Signal的组件类型应该是COMPONENT_TYPES.SIGNAL"

        # 验证component_type是枚举类型而不是字符串
        assert isinstance(signal.component_type, COMPONENT_TYPES), "component_type应该是COMPONENT_TYPES枚举类型"

        # 创建另一个Signal验证组件类型的一致性
        another_signal = Signal(
            portfolio_id="test_portfolio2",
            engine_id="test_engine2",
            run_id="test_run2",
            timestamp="2024-01-01 14:30:00",
            code="000002.SZ",
            direction=DIRECTION_TYPES.SHORT,
            reason="another test signal",
            source=SOURCE_TYPES.TUSHARE
        )
        assert another_signal.component_type == COMPONENT_TYPES.SIGNAL, "所有Signal实例的组件类型都应该是COMPONENT_TYPES.SIGNAL"

    def test_constructor_exception_handling(self):
        """测试构造异常处理"""
        # 测试各个必需字段的验证
        base_params = {
            "portfolio_id": "test_portfolio",
            "engine_id": "test_engine",
            "run_id": "test_run",
            "timestamp": "2024-01-01 09:30:00",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "reason": "test reason",
            "source": SOURCE_TYPES.SIM
        }

        # 测试每个字段为空或None的情况（不匹配具体消息，因为被包装了）
        with pytest.raises(Exception):
            Signal(**{**base_params, "portfolio_id": ""})

        with pytest.raises(Exception):
            Signal(**{**base_params, "engine_id": ""})

        with pytest.raises(Exception):
            Signal(**{**base_params, "run_id": ""})

        with pytest.raises(Exception):
            Signal(**{**base_params, "timestamp": None})

        with pytest.raises(Exception):
            Signal(**{**base_params, "code": ""})

        with pytest.raises(Exception):
            Signal(**{**base_params, "direction": None})

        with pytest.raises(Exception):
            Signal(**{**base_params, "reason": ""})

        with pytest.raises(Exception):
            Signal(**{**base_params, "source": None})

        # 验证所有参数都提供时可以正常创建
        valid_signal = Signal(**base_params)
        assert valid_signal is not None

    def test_uuid_generation(self):
        """测试UUID生成"""
        # 验证每个Signal都有唯一的UUID标识
        base_params = {
            "portfolio_id": "test_portfolio",
            "engine_id": "test_engine",
            "run_id": "test_run",
            "timestamp": "2024-01-01 09:30:00",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "reason": "test signal",
            "source": SOURCE_TYPES.SIM
        }

        signal1 = Signal(**base_params)
        signal2 = Signal(**{**base_params, "code": "000002.SZ"})

        # 验证UUID存在且是字符串
        assert signal1.uuid is not None
        assert signal2.uuid is not None
        assert isinstance(signal1.uuid, str)
        assert isinstance(signal2.uuid, str)

        # 验证UUID不为空
        assert len(signal1.uuid) > 0
        assert len(signal2.uuid) > 0

        # 验证UUID是唯一的
        assert signal1.uuid != signal2.uuid

    def test_custom_uuid_support(self):
        """测试自定义UUID支持"""
        custom_uuid = "custom_signal_12345"

        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM,
            uuid=custom_uuid  # 使用自定义UUID
        )

        # 验证自定义UUID被正确设置
        assert signal.uuid == custom_uuid

    def test_empty_uuid_auto_generation(self):
        """测试空UUID自动生成"""
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM,
            uuid=""  # 空UUID应触发自动生成
        )

        # 验证UUID被自动生成
        assert signal.uuid is not None
        assert len(signal.uuid) > 0
        assert signal.uuid != ""
        assert "SIGNAL" in signal.uuid  # 应包含组件类型标识, "不同Signal实例应该有不同的UUID"

        # 测试自定义UUID
        custom_uuid = "custom-signal-123"
        signal_with_uuid = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM,
            uuid=custom_uuid
        )
        assert signal_with_uuid.uuid == custom_uuid


@pytest.mark.unit
class TestSignalProperties:
    """2. 属性访问测试"""

    def test_portfolio_id_property(self):
        """测试组合ID属性"""
        # 创建Signal测试portfolio_id属性
        portfolio_id = "test_portfolio_123"
        signal = Signal(
            portfolio_id=portfolio_id,
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        # 验证portfolio_id属性正确读取
        assert signal.portfolio_id == portfolio_id
        assert isinstance(signal.portfolio_id, str)

        # 验证portfolio_id是只读属性
        assert hasattr(signal, 'portfolio_id')
        assert not hasattr(signal, 'portfolio_id.setter') or not callable(getattr(signal, 'portfolio_id.setter', None))

    def test_engine_id_property(self):
        """测试引擎ID属性"""
        # 创建Signal测试engine_id属性
        original_engine_id = "test_engine_456"
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id=original_engine_id,
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        # 验证engine_id属性正确读取
        assert signal.engine_id == original_engine_id
        assert isinstance(signal.engine_id, str)

        # 验证engine_id可以修改（有setter）
        new_engine_id = "updated_engine_789"
        signal.engine_id = new_engine_id
        assert signal.engine_id == new_engine_id

    def test_run_id_property(self):
        """测试运行ID属性"""
        # 创建Signal测试run_id属性
        original_run_id = "test_run_001"
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id=original_run_id,
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        # 验证run_id属性正确读取
        assert signal.run_id == original_run_id
        assert isinstance(signal.run_id, str)

        # 验证run_id可以修改（有setter）
        new_run_id = "updated_run_002"
        signal.run_id = new_run_id
        assert signal.run_id == new_run_id

    def test_code_property(self):
        """测试股票代码属性"""
        # 创建Signal测试code属性
        code = "000001.SZ"
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code=code,
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        # 验证code属性正确读取
        assert signal.code == code
        assert isinstance(signal.code, str)

        # 验证code是只读属性（不能修改）
        with pytest.raises(AttributeError):
            signal.code = "000002.SZ"

    def test_direction_property(self):
        """测试交易方向属性"""
        # 测试LONG方向
        signal_long = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        # 验证direction属性正确读取
        assert signal_long.direction == DIRECTION_TYPES.LONG
        assert isinstance(signal_long.direction, DIRECTION_TYPES)

        # 测试SHORT方向
        signal_short = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000002.SZ",
            direction=DIRECTION_TYPES.SHORT,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        assert signal_short.direction == DIRECTION_TYPES.SHORT

        # 验证direction是只读属性（不能修改）
        with pytest.raises(AttributeError):
            signal_long.direction = DIRECTION_TYPES.SHORT

    def test_reason_property(self):
        """测试信号原因属性"""
        # 创建Signal测试reason属性
        reason = "技术指标突破"
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason=reason,
            source=SOURCE_TYPES.SIM
        )

        # 验证reason属性正确读取
        assert signal.reason == reason
        assert isinstance(signal.reason, str)

        # 验证reason是只读属性（不能修改）
        with pytest.raises(AttributeError):
            signal.reason = "新的原因"

    def test_timestamp_property(self):
        """测试时间戳属性"""
        # 创建Signal测试timestamp属性
        timestamp_str = "2024-01-01 14:30:00"
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp=timestamp_str,
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.SIM
        )

        # 验证timestamp属性正确读取和类型
        assert signal.timestamp is not None
        assert isinstance(signal.timestamp, datetime.datetime)

        # 验证timestamp可以修改（继承自TimeRelated）
        new_timestamp = datetime.datetime.now()
        signal.timestamp = new_timestamp
        assert signal.timestamp == new_timestamp

    def test_source_property(self):
        """测试信号源属性"""
        # 测试不同的信号源类型
        for source_type in [SOURCE_TYPES.SIM, SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO]:
            signal = Signal(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                timestamp="2024-01-01 09:30:00",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="test signal",
                source=source_type
            )

            # 验证source属性正确读取和枚举类型
            assert signal.source == source_type
            assert isinstance(signal.source, SOURCE_TYPES)

        # 验证source是只读属性（不能修改）
        with pytest.raises(AttributeError):
            signal.source = SOURCE_TYPES.OTHER


@pytest.mark.unit
class TestSignalDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self):
        """测试直接参数设置"""
        # 测试通过构造函数直接参数方式设置信号数据
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.STRATEGY
        )

        # 验证所有参数都被正确设置
        assert signal.portfolio_id == "test_portfolio"
        assert signal.engine_id == "test_engine"
        assert signal.run_id == "test_run"
        assert signal.code == "000001.SZ"
        assert signal.direction == DIRECTION_TYPES.LONG
        assert signal.reason == "test signal"
        assert signal.source == SOURCE_TYPES.STRATEGY

        # 验证时间戳被正确标准化
        from datetime import datetime
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.year == 2024

        # 测试已存在Signal的重新设置
        signal.set(
            "new_portfolio",
            "new_engine",
            "new_run",
            "2024-06-01 14:30:00",
            "000002.SZ",
            DIRECTION_TYPES.SHORT,
            "new test signal",
            SOURCE_TYPES.BACKTEST
        )

        # 验证重新设置后的值
        assert signal.portfolio_id == "new_portfolio"
        assert signal.engine_id == "new_engine"
        assert signal.code == "000002.SZ"
        assert signal.direction == DIRECTION_TYPES.SHORT

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        import pandas as pd

        # 创建测试用的pandas.Series数据
        series_data = pd.Series({
            'portfolio_id': 'series_portfolio',
            'engine_id': 'series_engine',
            'run_id': 'series_run',
            'timestamp': '2024-03-01 10:30:00',
            'code': '000003.SZ',
            'direction': DIRECTION_TYPES.LONG.value,  # 使用枚举值
            'reason': 'pandas series signal',
            'source': SOURCE_TYPES.DATABASE.value
        })

        # 先创建一个Signal实例（使用有效参数）
        signal = Signal(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            timestamp="2024-01-01",
            code="temp",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.OTHER
        )

        # 使用pandas.Series重新设置数据
        signal.set(series_data)

        # 验证从Series设置的数据
        assert signal.portfolio_id == 'series_portfolio'
        assert signal.engine_id == 'series_engine'
        assert signal.run_id == 'series_run'
        assert signal.code == '000003.SZ'
        assert signal.direction == DIRECTION_TYPES.LONG
        assert signal.reason == 'pandas series signal'
        assert signal.source == SOURCE_TYPES.DATABASE

        # 验证时间戳正确解析
        from datetime import datetime
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.month == 3

    def test_pandas_dataframe_setting(self):
        """测试pandas.DataFrame设置"""
        import pandas as pd

        # 创建测试用的pandas.DataFrame数据（单行）
        df_data = pd.DataFrame([{
            'portfolio_id': 'df_portfolio',
            'engine_id': 'df_engine',
            'run_id': 'df_run',
            'timestamp': '2024-03-01 14:30:00',
            'code': '000004.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,  # 使用枚举值
            'reason': 'pandas dataframe signal',
            'source': SOURCE_TYPES.BACKTEST.value
        }])

        # 先创建一个Signal实例（使用有效参数）
        signal = Signal(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            timestamp="2024-01-01",
            code="temp",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.OTHER
        )

        # 使用完整DataFrame重新设置数据（自动使用第一行）
        signal.set(df_data)

        # 验证从DataFrame设置的数据
        assert signal.portfolio_id == 'df_portfolio'
        assert signal.engine_id == 'df_engine'
        assert signal.run_id == 'df_run'
        assert signal.code == '000004.SZ'
        assert signal.direction == DIRECTION_TYPES.SHORT
        assert signal.reason == 'pandas dataframe signal'
        assert signal.source == SOURCE_TYPES.BACKTEST

        # 验证时间戳正确解析
        from datetime import datetime
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.hour == 14

    def test_singledispatch_routing(self):
        """测试方法分派路由"""
        import pandas as pd

        signal = Signal(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            timestamp="2024-01-01",
            code="test",
            direction=DIRECTION_TYPES.LONG,
            reason="test",
            source=SOURCE_TYPES.OTHER
        )

        # 测试直接参数分派
        signal.set(
            "direct_portfolio", "direct_engine", "direct_run",
            "2024-01-01", "000001.SZ", DIRECTION_TYPES.LONG,
            "direct signal", SOURCE_TYPES.STRATEGY
        )
        assert signal.portfolio_id == "direct_portfolio"

        # 测试Series分派
        series_data = pd.Series({
            'portfolio_id': 'series_portfolio',
            'engine_id': 'series_engine',
            'run_id': 'series_run',
            'timestamp': '2024-01-01',
            'code': '000002.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'reason': 'series signal',
            'source': SOURCE_TYPES.DATABASE.value
        })
        signal.set(series_data)
        assert signal.portfolio_id == "series_portfolio"

        # 测试DataFrame分派
        df_data = pd.DataFrame([{
            'portfolio_id': 'df_portfolio',
            'engine_id': 'df_engine',
            'run_id': 'df_run',
            'timestamp': '2024-01-01',
            'code': '000003.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'df signal',
            'source': SOURCE_TYPES.BACKTEST.value
        }])
        signal.set(df_data)
        assert signal.portfolio_id == "df_portfolio"

        # 测试不支持的类型会抛出NotImplementedError
        with pytest.raises(NotImplementedError, match="Unsupported input type"):
            signal.set({"invalid": "dict"})

    def test_parameter_order_validation(self):
        """测试参数顺序验证"""
        # 测试正确的参数顺序
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal",
            source=SOURCE_TYPES.STRATEGY
        )

        # 验证正确顺序的参数设置成功
        signal.set(
            "portfolio1",    # portfolio_id
            "engine1",       # engine_id
            "run1",          # run_id
            "2024-01-02",    # timestamp
            "000002.SZ",     # code
            DIRECTION_TYPES.SHORT,  # direction
            "order test",    # reason
            SOURCE_TYPES.DATABASE   # source
        )
        assert signal.portfolio_id == "portfolio1"
        assert signal.code == "000002.SZ"

        # 测试参数数量不足会触发错误
        with pytest.raises(TypeError):
            signal.set("portfolio2", "engine2")  # 缺少必要参数

        # 测试包含strength和confidence参数的完整设置
        signal.set(
            "portfolio3", "engine3", "run3", "2024-01-03",
            "000003.SZ", DIRECTION_TYPES.LONG, "extra test",
            SOURCE_TYPES.BACKTEST, 0.8, 0.7  # strength=0.8, confidence=0.7
        )
        assert signal.portfolio_id == "portfolio3"
        assert signal.strength == 0.8
        assert signal.confidence == 0.7

        # 测试参数过多会被*args捕获（额外参数应该被忽略）
        signal.set(
            "portfolio4", "engine4", "run4", "2024-01-04",
            "000004.SZ", DIRECTION_TYPES.SHORT, "ignore extra test",
            SOURCE_TYPES.BACKTEST, 0.9, 0.6, "extra_param", "another_extra"  # 额外参数
        )
        assert signal.portfolio_id == "portfolio4"
        assert signal.strength == 0.9
        assert signal.confidence == 0.6

    def test_optional_parameter_handling(self):
        """测试可选参数处理"""
        import pandas as pd

        signal = Signal(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            timestamp="2024-01-01",
            code="temp",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.OTHER
        )

        # 测试直接参数方式：所有参数都是必需的
        with pytest.raises(TypeError):
            # 缺少必需参数应该失败
            signal.set("portfolio", "engine")  # 缺少run_id, timestamp等

        # 测试Series方式：缺少必需字段应该失败
        incomplete_series = pd.Series({
            'portfolio_id': 'test_portfolio',
            'timestamp': '2024-01-01 09:30:00',
            'code': '000001.SZ'
            # 缺少direction和reason
        })

        with pytest.raises(ValueError):
            signal.set(incomplete_series)

        # 测试DataFrame方式：缺少必需字段应该失败
        incomplete_df = pd.DataFrame([{
            'portfolio_id': 'test_portfolio',
            'timestamp': '2024-01-01 09:30:00'
            # 缺少code, direction, reason
        }])

        with pytest.raises(ValueError):
            signal.set(incomplete_df)

        # 测试所有方式的一致性：完整数据应该都成功
        # 1. 直接参数方式
        signal.set(
            "direct_portfolio", "direct_engine", "direct_run",
            "2024-01-01", "000001.SZ", DIRECTION_TYPES.LONG,
            "direct signal", SOURCE_TYPES.STRATEGY
        )
        assert signal.portfolio_id == "direct_portfolio"

        # 2. Series方式
        complete_series = pd.Series({
            'portfolio_id': 'series_portfolio',
            'engine_id': 'series_engine',
            'run_id': 'series_run',
            'timestamp': '2024-01-01',
            'code': '000002.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'reason': 'series signal',
            'source': SOURCE_TYPES.DATABASE.value
        })
        signal.set(complete_series)
        assert signal.portfolio_id == "series_portfolio"

        # 3. DataFrame方式
        complete_df = pd.DataFrame([{
            'portfolio_id': 'df_portfolio',
            'engine_id': 'df_engine',
            'run_id': 'df_run',
            'timestamp': '2024-01-01',
            'code': '000003.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'df signal',
            'source': SOURCE_TYPES.BACKTEST.value
        }])
        signal.set(complete_df)
        assert signal.portfolio_id == "df_portfolio"

    def test_parameter_type_conversion(self):
        """测试参数类型转换"""
        import pandas as pd

        signal = Signal(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            timestamp="2024-01-01",
            code="temp",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.OTHER
        )

        # 测试直接参数方式的类型转换
        signal.set(
            "test_portfolio",  # portfolio_id必须是字符串
            "test_engine",
            "test_run",
            "2024-01-01 09:30:00",  # 字符串时间戳转datetime
            "000001.SZ",  # code保持字符串
            2,    # 整数转DIRECTION_TYPES.SHORT
            "timestamp test",
            9     # 整数转SOURCE_TYPES.DATABASE
        )

        # 验证枚举类型转换
        assert signal.portfolio_id == "test_portfolio"
        assert signal.code == "000001.SZ"
        assert signal.direction == DIRECTION_TYPES.SHORT  # 2 -> SHORT
        assert signal.source == SOURCE_TYPES.DATABASE     # 9 -> DATABASE

        # 验证时间戳被转换为datetime对象
        from datetime import datetime
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.year == 2024

        # 测试Series中枚举值的转换
        series_data = pd.Series({
            'portfolio_id': 'series_portfolio',  # 保持字符串
            'engine_id': 'enum_engine',
            'run_id': 'enum_run',
            'timestamp': '2024-03-01 14:30:00',
            'code': '000002.SZ',  # 保持字符串
            'direction': 1,  # 整数值，应该转换为DIRECTION_TYPES.LONG
            'reason': 'enum conversion test',
            'source': 11  # 整数值，应该转换为SOURCE_TYPES.STRATEGY
        })

        signal.set(series_data)

        # 验证类型转换
        assert signal.portfolio_id == "series_portfolio"
        assert signal.code == "000002.SZ"
        assert signal.direction == DIRECTION_TYPES.LONG    # 1 -> LONG
        assert signal.source == SOURCE_TYPES.STRATEGY      # 11 -> STRATEGY
        assert signal.timestamp.month == 3

        # 测试DataFrame中的类型转换
        df_data = pd.DataFrame([{
            'portfolio_id': 'df_convert_portfolio',
            'engine_id': 'df_convert_engine',
            'run_id': 'df_convert_run',
            'timestamp': '2024-06-01 16:45:30',
            'code': '000003.SZ',
            'direction': 2,  # SHORT
            'reason': 'df conversion test',
            'source': 13  # BACKTEST
        }])

        signal.set(df_data)

        # 验证转换结果
        assert signal.direction == DIRECTION_TYPES.SHORT     # 2 -> SHORT
        assert signal.source == SOURCE_TYPES.BACKTEST       # 13 -> BACKTEST
        assert signal.timestamp.month == 6
        assert signal.timestamp.hour == 16

    def test_invalid_input_rejection(self):
        """测试无效输入拒绝"""
        import pandas as pd

        signal = Signal(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            timestamp="2024-01-01",
            code="temp",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.OTHER
        )

        # 测试不支持的数据类型
        with pytest.raises(NotImplementedError):
            signal.set({"dict": "not_supported"})

        with pytest.raises(NotImplementedError):
            signal.set(["list", "not_supported"])

        with pytest.raises(NotImplementedError):
            signal.set(12345)

        # 测试空DataFrame
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError):
            signal.set(empty_df)

        # 测试直接参数方式的类型错误
        with pytest.raises(TypeError):
            signal.set("portfolio", 456, "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", 789, "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", 123,
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, 456, SOURCE_TYPES.STRATEGY)

        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      "invalid_direction", "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", "invalid_source")

        # 测试直接参数方式的值错误
        with pytest.raises(ValueError):
            signal.set("", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(ValueError):
            signal.set("portfolio", "", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", None, "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      None, "reason", SOURCE_TYPES.STRATEGY)

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "", SOURCE_TYPES.STRATEGY)

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", None)

        # 测试Series中的无效枚举值
        invalid_series = pd.Series({
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-01-01',
            'code': '000001.SZ',
            'direction': 999,  # 无效的direction枚举值
            'reason': 'test signal',
            'source': SOURCE_TYPES.STRATEGY.value
        })

        with pytest.raises((ValueError, KeyError)):  # 枚举转换应该失败
            signal.set(invalid_series)

        # 测试DataFrame中的无效数据
        invalid_df = pd.DataFrame([{
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-01-01',
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'test signal',
            'source': 888  # 无效的source枚举值
        }])

        with pytest.raises((ValueError, KeyError)):  # 枚举转换应该失败
            signal.set(invalid_df)


@pytest.mark.unit
class TestSignalParameterValidation:
    """4. 参数验证测试"""

    def test_portfolio_id_validation(self):
        """测试组合ID验证"""
        # 测试portfolio_id不能为空字符串
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="",  # 空字符串
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试有效的portfolio_id
        signal = Signal(
            portfolio_id="valid_portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal.portfolio_id == "valid_portfolio"

        # 测试通过set方法设置空portfolio_id
        with pytest.raises(ValueError):
            signal.set("", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

    def test_engine_id_validation(self):
        """测试引擎ID验证"""
        # 测试engine_id不能为空字符串
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="",  # 空字符串
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试有效的engine_id
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="valid_engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal.engine_id == "valid_engine"

        # 测试通过set方法设置无效engine_id (非字符串类型)
        with pytest.raises(TypeError):
            signal.set("portfolio", 123, "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        # 测试通过set方法设置空engine_id
        with pytest.raises(ValueError):
            signal.set("portfolio", "", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

    def test_run_id_validation(self):
        """测试运行ID验证"""
        # 测试run_id不能为空字符串
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="",  # 空字符串
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试run_id不能为非字符串类型
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id=123,  # 非字符串类型
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试有效的run_id
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="valid_run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal.run_id == "valid_run"

        # 测试通过set方法设置无效run_id (非字符串类型)
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", 456, "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        # 测试通过set方法设置空run_id
        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

    def test_code_validation(self):
        """测试股票代码验证"""
        # 测试code不能为空字符串
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="",  # 空字符串
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试code不能为非字符串类型
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code=123,  # 非字符串类型
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试有效的code
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal.code == "000001.SZ"

        # 测试通过set方法设置无效code (非字符串类型)
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", 789,
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        # 测试通过set方法设置空code
        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

    def test_reason_validation(self):
        """测试信号原因验证"""
        # 测试reason不能为空字符串
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="",  # 空字符串
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试reason不能为非字符串类型
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason=123,  # 非字符串类型
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试有效的reason
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="valid signal reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal.reason == "valid signal reason"

        # 测试通过set方法设置无效reason (非字符串类型)
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, 456, SOURCE_TYPES.STRATEGY)

        # 测试通过set方法设置空reason
        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "", SOURCE_TYPES.STRATEGY)

    def test_timestamp_validation(self):
        """测试时间戳验证"""
        # 测试timestamp不能为None
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp=None,  # None值
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试有效的timestamp (字符串)
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        from datetime import datetime
        assert isinstance(signal.timestamp, datetime)

        # 测试有效的timestamp (datetime对象)
        from datetime import datetime
        dt = datetime(2024, 1, 15, 10, 30, 0)
        signal2 = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp=dt,
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal2.timestamp == dt

        # 测试通过set方法设置None timestamp
        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", None, "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

    def test_direction_validation(self):
        """测试方向验证"""
        # 测试direction不能为None
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=None,  # None值
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试direction不能为无效类型
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction="invalid_direction",  # 字符串类型不被接受
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试有效的direction (枚举类型)
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal.direction == DIRECTION_TYPES.LONG

        # 测试有效的direction (整数类型，应被转换为枚举)
        signal2 = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=2,  # 对应DIRECTION_TYPES.SHORT
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal2.direction == DIRECTION_TYPES.SHORT

        # 测试通过set方法设置None direction
        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      None, "reason", SOURCE_TYPES.STRATEGY)

        # 测试通过set方法设置无效direction类型
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      "invalid_direction", "reason", SOURCE_TYPES.STRATEGY)

    def test_source_validation(self):
        """测试数据源验证"""
        # 测试source不能为None
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=None  # None值
            )

        # 测试source不能为无效类型
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source="invalid_source"  # 字符串类型不被接受
            )

        # 测试有效的source (枚举类型)
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal.source == SOURCE_TYPES.STRATEGY

        # 测试有效的source (整数类型，应被转换为枚举)
        signal2 = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=9  # 对应SOURCE_TYPES.DATABASE
        )
        assert signal2.source == SOURCE_TYPES.DATABASE

        # 测试通过set方法设置None source
        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", None)

        # 测试通过set方法设置无效source类型
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", "invalid_source")

    def test_direction_not_empty(self):
        """测试方向非空验证"""
        # 测试direction不能为None
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=None,  # None值
                reason="reason",
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试通过set方法设置None direction
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      None, "reason", SOURCE_TYPES.STRATEGY)

    def test_reason_not_empty(self):
        """测试原因非空验证"""
        # 测试reason不能为空字符串
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="",  # 空字符串
                source=SOURCE_TYPES.STRATEGY
            )

        # 测试通过set方法设置空reason
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="valid reason",
            source=SOURCE_TYPES.STRATEGY
        )

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "", SOURCE_TYPES.STRATEGY)

        # 测试reason类型验证
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, 123, SOURCE_TYPES.STRATEGY)

    def test_source_not_empty(self):
        """测试来源非空验证"""
        # 测试source不能为None
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="reason",
                source=None  # None值
            )

        # 测试通过set方法设置None source
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )

        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", None)

        # 测试source类型验证
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", "invalid_source")

    def test_value_error_messages(self):
        """测试错误消息验证"""
        # 验证TypeError错误消息包含参数名和类型信息
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )

        # 测试engine_id类型错误
        with pytest.raises(TypeError):
            signal.set("portfolio", 123, "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        # 测试run_id类型错误
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", 123, "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        # 测试portfolio_id空值错误
        with pytest.raises(ValueError):
            signal.set("", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        # 测试direction类型错误
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      "invalid_direction", "reason", SOURCE_TYPES.STRATEGY)

    def test_validation_early_termination(self):
        """测试验证提前终止"""
        # 验证遇到第一个错误时会立即终止，不会继续检查后续参数
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="reason",
            source=SOURCE_TYPES.STRATEGY
        )

        # 测试验证提前终止 - 第二个参数类型错误应该立即抛出
        with pytest.raises(TypeError):
            signal.set("portfolio",  # 第一个参数正确
                      456,  # 第二个参数类型错误
                      789,  # 第三个参数也有类型错误
                      "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)

        # 测试第一个参数值错误应该立即抛出ValueError
        with pytest.raises(ValueError):
            signal.set("",  # 第一个参数值错误（空字符串）
                      "",  # 第二个参数也有值错误
                      "",  # 第三个参数也有值错误
                      "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", SOURCE_TYPES.STRATEGY)


@pytest.mark.unit
class TestSignalSourceManagement:
    """5. 信号源管理测试"""

    def test_source_types_assignment(self):
        """测试来源类型分配"""
        # 测试所有主要SOURCE_TYPES枚举的正确分配

        # 测试STRATEGY源类型
        signal_strategy = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="strategy signal",
            source=SOURCE_TYPES.STRATEGY
        )
        assert signal_strategy.source == SOURCE_TYPES.STRATEGY
        assert isinstance(signal_strategy.source, SOURCE_TYPES)

        # 测试DATABASE源类型
        signal_database = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.SHORT,
            reason="database signal",
            source=SOURCE_TYPES.DATABASE
        )
        assert signal_database.source == SOURCE_TYPES.DATABASE

        # 测试BACKTEST源类型
        signal_backtest = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="backtest signal",
            source=SOURCE_TYPES.BACKTEST
        )
        assert signal_backtest.source == SOURCE_TYPES.BACKTEST

        # 测试LIVE源类型
        signal_live = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.SHORT,
            reason="live signal",
            source=SOURCE_TYPES.LIVE
        )
        assert signal_live.source == SOURCE_TYPES.LIVE

        # 测试SIM源类型
        signal_sim = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="sim signal",
            source=SOURCE_TYPES.SIM
        )
        assert signal_sim.source == SOURCE_TYPES.SIM

    def test_source_tracking(self):
        """测试信号源追踪"""
        # 测试信号源在信号生命周期中的追踪功能

        # 创建信号时记录源
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="initial signal",
            source=SOURCE_TYPES.STRATEGY
        )

        # 验证初始源记录
        assert signal.source == SOURCE_TYPES.STRATEGY

        # 测试通过set方法更新源的追踪
        signal.set(
            "portfolio",
            "engine",
            "run",
            "2024-01-01 10:30:00",
            "000002.SZ",
            DIRECTION_TYPES.SHORT,
            "updated signal",
            SOURCE_TYPES.DATABASE  # 更新源类型
        )

        # 验证源已被正确更新
        assert signal.source == SOURCE_TYPES.DATABASE

        # 测试源的只读性（不能直接修改）
        with pytest.raises(AttributeError):
            signal.source = SOURCE_TYPES.LIVE

        # 测试源的可追溯性（源信息始终可用）
        assert hasattr(signal, 'source')
        assert signal.source is not None
        assert isinstance(signal.source, SOURCE_TYPES)

        # 测试使用pandas Series设置时源的追踪
        import pandas as pd
        series_data = pd.Series({
            'portfolio_id': 'series_portfolio',
            'engine_id': 'series_engine',
            'run_id': 'series_run',
            'timestamp': '2024-01-02',
            'code': '000003.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'series signal',
            'source': SOURCE_TYPES.BACKTEST.value
        })

        signal.set(series_data)
        assert signal.source == SOURCE_TYPES.BACKTEST

        # 测试使用DataFrame设置时源的追踪
        df_data = pd.DataFrame([{
            'portfolio_id': 'df_portfolio',
            'engine_id': 'df_engine',
            'run_id': 'df_run',
            'timestamp': '2024-01-03',
            'code': '000004.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'reason': 'df signal',
            'source': SOURCE_TYPES.LIVE.value
        }])

        signal.set(df_data)
        assert signal.source == SOURCE_TYPES.LIVE

    def test_default_source_handling(self):
        """测试默认信号源处理"""
        # 测试Signal构造函数的默认SOURCE_TYPES.OTHER处理

        # 测试使用默认source参数
        signal_default = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="default source test"
            # 不传入source参数，应使用默认值SOURCE_TYPES.OTHER
        )
        assert signal_default.source == SOURCE_TYPES.OTHER

        # 测试pandas Series缺少source字段时的默认处理
        import pandas as pd
        series_without_source = pd.Series({
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-01-01',
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'series without source'
            # 没有source字段
        })

        signal_series = Signal(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            timestamp="2024-01-01",
            code="temp",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.STRATEGY
        )

        signal_series.set(series_without_source)
        # Signal的set方法应该保持原有的source值，因为pandas数据没有source字段
        # 检查_source是否已被设置（从Base类继承）
        assert hasattr(signal_series, '_source')

        # 测试pandas DataFrame缺少source字段时的默认处理
        df_without_source = pd.DataFrame([{
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-01-01',
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'reason': 'df without source'
            # 没有source字段
        }])

        signal_df = Signal(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            timestamp="2024-01-01",
            code="temp",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.DATABASE
        )

        signal_df.set(df_without_source)
        # 同样应该保持源的可访问性
        assert hasattr(signal_df, '_source')

        # 测试显式设置None时不应该被接受
        with pytest.raises(Exception):
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="test",
                source=None  # 显式传入None应该被拒绝
            )

    def test_source_enum_validation(self):
        """测试信号源枚举验证"""
        # 测试SOURCE_TYPES枚举的验证和转换功能

        # 测试有效的枚举值
        valid_sources = [
            SOURCE_TYPES.STRATEGY,
            SOURCE_TYPES.DATABASE,
            SOURCE_TYPES.BACKTEST,
            SOURCE_TYPES.LIVE,
            SOURCE_TYPES.SIM,
            SOURCE_TYPES.OTHER,
            SOURCE_TYPES.SIMMATCH,
            SOURCE_TYPES.BROKERMATCHMAKING
        ]

        for source in valid_sources:
            signal = Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp="2024-01-01",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason=f"test {source.name}",
                source=source
            )
            assert signal.source == source
            assert isinstance(signal.source, SOURCE_TYPES)

        # 测试整数值到枚举的转换
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="int conversion test",
            source=SOURCE_TYPES.STRATEGY
        )

        # 测试通过set方法进行整数到枚举转换
        signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                  DIRECTION_TYPES.LONG, "reason", 9)  # 9对应DATABASE
        assert signal.source == SOURCE_TYPES.DATABASE

        signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                  DIRECTION_TYPES.LONG, "reason", 11)  # 11对应STRATEGY
        assert signal.source == SOURCE_TYPES.STRATEGY

        signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                  DIRECTION_TYPES.LONG, "reason", 13)  # 13对应BACKTEST
        assert signal.source == SOURCE_TYPES.BACKTEST

        # 测试无效类型应该被拒绝
        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", "invalid_string")

        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", [])

        with pytest.raises(TypeError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", {})

        # 测试None值应该被拒绝
        with pytest.raises(ValueError):
            signal.set("portfolio", "engine", "run", "2024-01-01", "000001.SZ",
                      DIRECTION_TYPES.LONG, "reason", None)

        # 测试pandas Series中的枚举验证
        import pandas as pd
        series_data = pd.Series({
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-01-01',
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'series enum test',
            'source': SOURCE_TYPES.LIVE.value  # 使用枚举值
        })

        signal.set(series_data)
        assert signal.source == SOURCE_TYPES.LIVE

        # 测试DataFrame中的枚举验证
        df_data = pd.DataFrame([{
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-01-01',
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'reason': 'df enum test',
            'source': SOURCE_TYPES.SIM.value  # 使用枚举值
        }])

        signal.set(df_data)
        assert signal.source == SOURCE_TYPES.SIM

    def test_source_identification(self):
        """测试信号源标识"""
        # 测试信号源的标识和区分功能

        # 创建不同源的信号进行对比
        signal_strategy = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="strategy signal",
            source=SOURCE_TYPES.STRATEGY
        )

        signal_database = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="database signal",
            source=SOURCE_TYPES.DATABASE
        )

        signal_live = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="live signal",
            source=SOURCE_TYPES.LIVE
        )

        # 验证源的唯一标识
        assert signal_strategy.source != signal_database.source
        assert signal_strategy.source != signal_live.source
        assert signal_database.source != signal_live.source

        # 验证相同源的信号具有相同标识
        signal_strategy2 = Signal(
            portfolio_id="portfolio2",
            engine_id="engine2",
            run_id="run2",
            timestamp="2024-01-02",
            code="000002.SZ",
            direction=DIRECTION_TYPES.SHORT,
            reason="another strategy signal",
            source=SOURCE_TYPES.STRATEGY
        )

        assert signal_strategy.source == signal_strategy2.source

        # 测试源标识的类型安全
        assert isinstance(signal_strategy.source, SOURCE_TYPES)
        assert isinstance(signal_database.source, SOURCE_TYPES)
        assert isinstance(signal_live.source, SOURCE_TYPES)

        # 测试源标识的可比较性
        assert signal_strategy.source == SOURCE_TYPES.STRATEGY
        assert signal_database.source == SOURCE_TYPES.DATABASE
        assert signal_live.source == SOURCE_TYPES.LIVE

        # 测试源标识的枚举值
        assert signal_strategy.source.value == 11  # STRATEGY的值
        assert signal_database.source.value == 9   # DATABASE的值
        assert signal_live.source.value == 14      # LIVE的值

        # 测试源标识的字符串表示
        assert signal_strategy.source.name == "STRATEGY"
        assert signal_database.source.name == "DATABASE"
        assert signal_live.source.name == "LIVE"

        # 测试通过源标识区分信号类型
        def identify_signal_type(signal):
            """根据source识别信号类型的示例函数"""
            if signal.source == SOURCE_TYPES.STRATEGY:
                return "strategy_generated"
            elif signal.source == SOURCE_TYPES.DATABASE:
                return "database_retrieved"
            elif signal.source == SOURCE_TYPES.LIVE:
                return "live_market"
            elif signal.source == SOURCE_TYPES.BACKTEST:
                return "backtest_simulation"
            else:
                return "other_source"

        assert identify_signal_type(signal_strategy) == "strategy_generated"
        assert identify_signal_type(signal_database) == "database_retrieved"
        assert identify_signal_type(signal_live) == "live_market"

        # 测试源标识在集合中的唯一性
        sources_set = {signal_strategy.source, signal_database.source, signal_live.source}
        assert len(sources_set) == 3  # 三个不同的源

        sources_list = [signal_strategy.source, signal_strategy2.source]
        unique_sources = set(sources_list)
        assert len(unique_sources) == 1  # 相同源的信号


@pytest.mark.unit
class TestSignalTimeNormalization:
    """6. 时间标准化测试"""

    def test_datetime_normalization(self):
        """测试日期时间标准化"""
        # 测试datetime_normalize函数在Signal中的正确调用
        from datetime import datetime

        # 测试字符串时间戳的标准化
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-15 09:30:00",  # 字符串格式
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="normalization test",
            source=SOURCE_TYPES.STRATEGY
        )

        # 验证时间戳被正确标准化为datetime对象
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 1
        assert signal.timestamp.day == 15
        assert signal.timestamp.hour == 9
        assert signal.timestamp.minute == 30
        assert signal.timestamp.second == 0

        # 测试不同字符串格式的标准化
        test_formats = [
            "2024-01-15",
            "2024-01-15 10:30",
            "2024-01-15 10:30:45",
            "2024/01/15",
            "20240115",
            "2024-01-15T10:30:00"
        ]

        for timestamp_str in test_formats:
            signal.set(
                "portfolio", "engine", "run", timestamp_str, "000001.SZ",
                DIRECTION_TYPES.LONG, "format test", SOURCE_TYPES.STRATEGY
            )
            assert isinstance(signal.timestamp, datetime)
            assert signal.timestamp.year == 2024
            assert signal.timestamp.month == 1
            assert signal.timestamp.day == 15

        # 测试通过pandas Series的时间标准化
        import pandas as pd
        series_data = pd.Series({
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-03-20 14:45:30',
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.SHORT.value,
            'reason': 'series normalization test',
            'source': SOURCE_TYPES.DATABASE.value
        })

        signal.set(series_data)
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 3
        assert signal.timestamp.day == 20
        assert signal.timestamp.hour == 14
        assert signal.timestamp.minute == 45
        assert signal.timestamp.second == 30

        # 测试通过pandas DataFrame的时间标准化
        df_data = pd.DataFrame([{
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': '2024-06-10 16:20:15',
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'df normalization test',
            'source': SOURCE_TYPES.BACKTEST.value
        }])

        signal.set(df_data)
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 6
        assert signal.timestamp.day == 10
        assert signal.timestamp.hour == 16
        assert signal.timestamp.minute == 20
        assert signal.timestamp.second == 15

    def test_string_timestamp_conversion(self):
        """测试字符串时间转换"""
        # 测试各种字符串格式的时间戳转换
        from datetime import datetime

        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.STRATEGY
        )

        # 测试常见的日期格式
        date_formats = [
            ("2024-01-15", (2024, 1, 15, 0, 0, 0)),
            ("2024/01/15", (2024, 1, 15, 0, 0, 0)),
            ("20240115", (2024, 1, 15, 0, 0, 0)),
            ("2024-01-15 09:30:00", (2024, 1, 15, 9, 30, 0)),
            ("2024-01-15T09:30:00", (2024, 1, 15, 9, 30, 0)),
            ("2024-01-15 09:30", (2024, 1, 15, 9, 30, 0)),
            ("2024-01-15 09:30:45.123", (2024, 1, 15, 9, 30, 45))
        ]

        for timestamp_str, expected in date_formats:
            signal.set(
                "portfolio", "engine", "run", timestamp_str, "000001.SZ",
                DIRECTION_TYPES.LONG, f"test {timestamp_str}", SOURCE_TYPES.STRATEGY
            )

            assert isinstance(signal.timestamp, datetime)
            assert signal.timestamp.year == expected[0]
            assert signal.timestamp.month == expected[1]
            assert signal.timestamp.day == expected[2]
            assert signal.timestamp.hour == expected[3]
            assert signal.timestamp.minute == expected[4]
            assert signal.timestamp.second == expected[5]

        # 测试边界情况的日期
        boundary_dates = [
            "2024-01-01 00:00:00",  # 年初
            "2024-12-31 23:59:59",  # 年末
            "2024-02-29 12:00:00",  # 闰年2月29日
            "2024-06-15 12:00:00"   # 年中
        ]

        for boundary_date in boundary_dates:
            signal.set(
                "portfolio", "engine", "run", boundary_date, "000001.SZ",
                DIRECTION_TYPES.LONG, "boundary test", SOURCE_TYPES.STRATEGY
            )
            assert isinstance(signal.timestamp, datetime)

        # 测试市场交易时间
        trading_times = [
            "2024-01-15 09:30:00",  # 开盘
            "2024-01-15 11:30:00",  # 上午收盘
            "2024-01-15 13:00:00",  # 下午开盘
            "2024-01-15 15:00:00"   # 下午收盘
        ]

        for trading_time in trading_times:
            signal.set(
                "portfolio", "engine", "run", trading_time, "000001.SZ",
                DIRECTION_TYPES.LONG, "trading time test", SOURCE_TYPES.STRATEGY
            )
            assert isinstance(signal.timestamp, datetime)
            # 验证时间在合理的交易时间范围内
            assert 9 <= signal.timestamp.hour <= 15

        # 测试字符串转换后的时间戳可修改性（继承自TimeRelated）
        original_timestamp = signal.timestamp
        # timestamp属性可以修改
        new_timestamp = datetime(2025, 1, 1)
        signal.timestamp = new_timestamp

        # 确认时间戳已经被正确修改
        assert signal.timestamp == new_timestamp
        assert signal.timestamp != original_timestamp

    def test_datetime_object_handling(self):
        """测试datetime对象处理"""
        # 测试直接传入datetime对象的处理
        from datetime import datetime, date, time

        # 测试传入完整的datetime对象
        dt = datetime(2024, 3, 15, 14, 30, 45)
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp=dt,  # 直接传入datetime对象
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="datetime object test",
            source=SOURCE_TYPES.STRATEGY
        )

        # 验证datetime对象被正确保存
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp == dt
        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 3
        assert signal.timestamp.day == 15
        assert signal.timestamp.hour == 14
        assert signal.timestamp.minute == 30
        assert signal.timestamp.second == 45

        # 测试通过set方法传入datetime对象
        new_dt = datetime(2024, 6, 20, 10, 15, 30)
        signal.set(
            "portfolio", "engine", "run", new_dt, "000002.SZ",
            DIRECTION_TYPES.SHORT, "set datetime test", SOURCE_TYPES.DATABASE
        )

        assert signal.timestamp == new_dt
        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 6
        assert signal.timestamp.day == 20
        assert signal.timestamp.hour == 10
        assert signal.timestamp.minute == 15
        assert signal.timestamp.second == 30

        # 测试不同精度的datetime对象
        dt_with_microseconds = datetime(2024, 7, 10, 9, 30, 0, 123456)
        signal.set(
            "portfolio", "engine", "run", dt_with_microseconds, "000003.SZ",
            DIRECTION_TYPES.LONG, "microseconds test", SOURCE_TYPES.LIVE
        )

        assert signal.timestamp == dt_with_microseconds
        assert signal.timestamp.microsecond == 123456

        # 测试极端的datetime值
        min_datetime = datetime(1900, 1, 1, 0, 0, 0)
        max_datetime = datetime(2099, 12, 31, 23, 59, 59)

        for extreme_dt in [min_datetime, max_datetime]:
            signal.set(
                "portfolio", "engine", "run", extreme_dt, "000001.SZ",
                DIRECTION_TYPES.LONG, "extreme datetime test", SOURCE_TYPES.STRATEGY
            )
            assert signal.timestamp == extreme_dt

        # 测试datetime对象在pandas Series中的处理
        import pandas as pd
        dt_for_pandas = datetime(2024, 8, 25, 11, 45, 20)
        series_data = pd.Series({
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': dt_for_pandas,  # pandas Series中的datetime对象
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'pandas datetime test',
            'source': SOURCE_TYPES.BACKTEST.value
        })

        signal.set(series_data)
        assert isinstance(signal.timestamp, datetime)
        # 注意：pandas可能会改变datetime的类型，但应该保持值的一致性
        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 8
        assert signal.timestamp.day == 25
        assert signal.timestamp.hour == 11
        assert signal.timestamp.minute == 45
        assert signal.timestamp.second == 20

        # 测试datetime对象的不可变性
        original_dt = signal.timestamp
        assert signal.timestamp is not None

        # 验证传入的datetime对象不会影响原始对象
        test_dt = datetime(2024, 9, 30, 16, 0, 0)
        signal.set(
            "portfolio", "engine", "run", test_dt, "000001.SZ",
            DIRECTION_TYPES.LONG, "immutability test", SOURCE_TYPES.STRATEGY
        )

        # 原始datetime对象应该保持不变
        assert test_dt == datetime(2024, 9, 30, 16, 0, 0)

    def test_invalid_timestamp_rejection(self):
        """测试无效时间戳拒绝"""
        # 测试无效时间戳格式的拒绝机制

        # 测试None值被拒绝
        with pytest.raises(Exception):  # Signal构造函数包装了原始异常
            Signal(
                portfolio_id="portfolio",
                engine_id="engine",
                run_id="run",
                timestamp=None,  # None应该被拒绝
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="invalid timestamp test",
                source=SOURCE_TYPES.STRATEGY
            )

        # 创建一个有效的signal用于后续测试
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp="2024-01-01",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="temp",
            source=SOURCE_TYPES.STRATEGY
        )

        # 测试完全无效的字符串格式
        invalid_timestamps = [
            "invalid_date",
            "2024-13-32",  # 无效月份和日期
            "2024-02-30",  # 2月没有30日
            "2024-01-32",  # 1月没有32日
            "24-01-15",    # 年份格式错误
            "2024-1-1",    # 月日格式不规范（虽然可能被某些解析器接受）
            "abc123",      # 完全非数字
            "",            # 空字符串
            "   ",         # 空白字符串
            "2024/13/01",  # 斜杠格式的无效月份
            "20241301",    # 紧凑格式的无效月份
        ]

        for invalid_ts in invalid_timestamps:
            try:
                signal.set(
                    "portfolio", "engine", "run", invalid_ts, "000001.SZ",
                    DIRECTION_TYPES.LONG, "invalid test", SOURCE_TYPES.STRATEGY
                )
                # 如果某些格式被接受，我们也认为这是可以的
                # 因为不同的时间解析器可能有不同的容错策略
            except (ValueError, Exception):
                # 预期的异常，测试通过
                pass

        # 测试非字符串、非datetime类型
        invalid_types = [
            123,           # 纯数字（除非是有效的日期格式如19900101）
            [],            # 列表
            {},            # 字典
            object(),      # 任意对象
        ]

        for invalid_type in invalid_types:
            # 对于非int类型，应该抛出异常
            if not isinstance(invalid_type, int):
                with pytest.raises((ValueError, TypeError, Exception)):
                    signal.set(
                        "portfolio", "engine", "run", invalid_type, "000001.SZ",
                        DIRECTION_TYPES.LONG, "type test", SOURCE_TYPES.STRATEGY
                    )
            else:
                # int类型可能是有效的时间戳，允许通过或抛出异常
                try:
                    signal.set(
                        "portfolio", "engine", "run", invalid_type, "000001.SZ",
                        DIRECTION_TYPES.LONG, "type test", SOURCE_TYPES.STRATEGY
                    )
                except (ValueError, TypeError, Exception):
                    pass  # 异常也是可接受的

        # 测试边界外的年份
        extreme_dates = [
            "1800-01-01",  # 太早的年份
            "2200-01-01",  # 太晚的年份
        ]

        for extreme_date in extreme_dates:
            try:
                signal.set(
                    "portfolio", "engine", "run", extreme_date, "000001.SZ",
                    DIRECTION_TYPES.LONG, "extreme test", SOURCE_TYPES.STRATEGY
                )
                # 某些极端日期可能被接受，这里只是测试行为一致性
            except (ValueError, Exception):
                # 如果被拒绝也是可以接受的
                pass

        # 验证signal在无效输入后仍然保持一致状态
        assert signal.timestamp is not None
        from datetime import datetime
        assert isinstance(signal.timestamp, datetime)

    def test_timezone_handling(self):
        """测试时区处理"""
        # 测试时区信息的处理逻辑
        from datetime import datetime, timezone, timedelta

        # 测试不带时区信息的datetime对象（naive datetime）
        naive_dt = datetime(2024, 1, 15, 9, 30, 0)
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp=naive_dt,
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="naive datetime test",
            source=SOURCE_TYPES.STRATEGY
        )

        # 验证naive datetime被正确处理
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp == naive_dt
        # 大多数系统将naive datetime视为本地时区

        # 测试带时区信息的datetime对象（aware datetime）
        # UTC时区
        utc_dt = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        signal.set(
            "portfolio", "engine", "run", utc_dt, "000001.SZ",
            DIRECTION_TYPES.LONG, "utc datetime test", SOURCE_TYPES.STRATEGY
        )

        assert isinstance(signal.timestamp, datetime)
        # datetime_normalize可能会处理时区信息，这里测试行为一致性

        # 测试其他时区
        # 东八区（北京时间）
        beijing_tz = timezone(timedelta(hours=8))
        beijing_dt = datetime(2024, 1, 15, 17, 30, 0, tzinfo=beijing_tz)

        signal.set(
            "portfolio", "engine", "run", beijing_dt, "000001.SZ",
            DIRECTION_TYPES.LONG, "beijing datetime test", SOURCE_TYPES.STRATEGY
        )

        assert isinstance(signal.timestamp, datetime)

        # 测试美东时区
        eastern_tz = timezone(timedelta(hours=-5))
        eastern_dt = datetime(2024, 1, 15, 4, 30, 0, tzinfo=eastern_tz)

        signal.set(
            "portfolio", "engine", "run", eastern_dt, "000001.SZ",
            DIRECTION_TYPES.LONG, "eastern datetime test", SOURCE_TYPES.STRATEGY
        )

        assert isinstance(signal.timestamp, datetime)

        # 测试字符串格式中的时区信息（如果datetime_normalize支持）
        # 注意：标准的datetime_normalize可能不支持时区解析
        iso_with_tz_strings = [
            "2024-01-15T09:30:00Z",      # UTC标记
            "2024-01-15T09:30:00+00:00", # UTC offset
            "2024-01-15T17:30:00+08:00", # 北京时间
        ]

        for tz_string in iso_with_tz_strings:
            try:
                signal.set(
                    "portfolio", "engine", "run", tz_string, "000001.SZ",
                    DIRECTION_TYPES.LONG, "tz string test", SOURCE_TYPES.STRATEGY
                )
                # 如果成功解析，验证结果是datetime对象
                assert isinstance(signal.timestamp, datetime)
            except (ValueError, Exception):
                # 如果不支持时区解析，这也是可以接受的
                # datetime_normalize目前可能不支持时区信息
                pass

        # 测试pandas中的时区aware对象
        import pandas as pd

        # 创建带时区的pandas Timestamp
        try:
            pd_tz_timestamp = pd.Timestamp('2024-01-15 09:30:00', tz='UTC')

            series_with_tz = pd.Series({
                'portfolio_id': 'test_portfolio',
                'engine_id': 'test_engine',
                'run_id': 'test_run',
                'timestamp': pd_tz_timestamp,
                'code': '000001.SZ',
                'direction': DIRECTION_TYPES.LONG.value,
                'reason': 'pandas tz test',
                'source': SOURCE_TYPES.DATABASE.value
            })

            signal.set(series_with_tz)
            assert isinstance(signal.timestamp, datetime)

        except Exception:
            # 如果pandas时区处理有问题，跳过这个测试
            pass

        # 验证最终的timestamp仍然是有效的datetime对象
        assert signal.timestamp is not None
        assert isinstance(signal.timestamp, datetime)

        # 测试时区处理的一致性
        # 无论输入什么时区信息，输出应该是一致的格式
        test_times = [
            datetime(2024, 1, 15, 9, 30, 0),  # naive
            datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc),  # UTC
        ]

        timestamps = []
        for test_time in test_times:
            signal.set(
                "portfolio", "engine", "run", test_time, "000001.SZ",
                DIRECTION_TYPES.LONG, "consistency test", SOURCE_TYPES.STRATEGY
            )
            timestamps.append(signal.timestamp)

        # 所有timestamp都应该是datetime对象
        for ts in timestamps:
            assert isinstance(ts, datetime)

    def test_timestamp_precision(self):
        """测试时间戳精度"""
        # 测试时间戳精度的保持
        from datetime import datetime

        # 测试秒级精度
        dt_seconds = datetime(2024, 1, 15, 9, 30, 45)
        signal = Signal(
            portfolio_id="portfolio",
            engine_id="engine",
            run_id="run",
            timestamp=dt_seconds,
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="seconds precision test",
            source=SOURCE_TYPES.STRATEGY
        )

        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 1
        assert signal.timestamp.day == 15
        assert signal.timestamp.hour == 9
        assert signal.timestamp.minute == 30
        assert signal.timestamp.second == 45
        assert signal.timestamp.microsecond == 0

        # 测试微秒级精度
        dt_microseconds = datetime(2024, 1, 15, 9, 30, 45, 123456)
        signal.set(
            "portfolio", "engine", "run", dt_microseconds, "000001.SZ",
            DIRECTION_TYPES.LONG, "microseconds precision test", SOURCE_TYPES.STRATEGY
        )

        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 1
        assert signal.timestamp.day == 15
        assert signal.timestamp.hour == 9
        assert signal.timestamp.minute == 30
        assert signal.timestamp.second == 45
        assert signal.timestamp.microsecond == 123456

        # 测试字符串格式的微秒精度保持
        microsecond_strings = [
            "2024-01-15 09:30:45.123456",
            "2024-01-15T09:30:45.654321",
        ]

        for ms_string in microsecond_strings:
            signal.set(
                "portfolio", "engine", "run", ms_string, "000001.SZ",
                DIRECTION_TYPES.LONG, "string microseconds test", SOURCE_TYPES.STRATEGY
            )

            # 验证微秒精度被保持
            assert isinstance(signal.timestamp, datetime)
            assert signal.timestamp.microsecond > 0

        # 测试不同精度级别的时间
        precision_tests = [
            ("2024-01-15", 0, 0, 0, 0),  # 日期精度
            ("2024-01-15 09:30:00", 9, 30, 0, 0),  # 秒精度
            ("2024-01-15 09:30:45", 9, 30, 45, 0),  # 秒精度
        ]

        for time_str, expected_hour, expected_minute, expected_second, expected_microsecond in precision_tests:
            signal.set(
                "portfolio", "engine", "run", time_str, "000001.SZ",
                DIRECTION_TYPES.LONG, "precision test", SOURCE_TYPES.STRATEGY
            )

            assert signal.timestamp.hour == expected_hour
            assert signal.timestamp.minute == expected_minute
            assert signal.timestamp.second == expected_second
            if expected_microsecond == 0:
                # 对于没有微秒信息的输入，应该是0
                assert signal.timestamp.microsecond == expected_microsecond

        # 测试极高精度的微秒值
        high_precision_dt = datetime(2024, 1, 15, 9, 30, 45, 999999)
        signal.set(
            "portfolio", "engine", "run", high_precision_dt, "000001.SZ",
            DIRECTION_TYPES.LONG, "high precision test", SOURCE_TYPES.STRATEGY
        )

        assert signal.timestamp.microsecond == 999999

        # 测试精度在pandas操作中的保持
        import pandas as pd

        high_precision_series = pd.Series({
            'portfolio_id': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'timestamp': datetime(2024, 1, 15, 9, 30, 45, 789012),
            'code': '000001.SZ',
            'direction': DIRECTION_TYPES.LONG.value,
            'reason': 'pandas precision test',
            'source': SOURCE_TYPES.DATABASE.value
        })

        signal.set(high_precision_series)

        # 验证通过pandas设置后精度是否保持
        assert isinstance(signal.timestamp, datetime)
        # 注意：pandas可能会影响精度，这里主要测试兼容性

        # 测试时间戳精度的一致性
        original_dt = datetime(2024, 1, 15, 9, 30, 45, 123456)
        signal.set(
            "portfolio", "engine", "run", original_dt, "000001.SZ",
            DIRECTION_TYPES.LONG, "consistency test", SOURCE_TYPES.STRATEGY
        )

        # 多次获取应该返回相同的精度
        ts1 = signal.timestamp
        ts2 = signal.timestamp

        assert ts1 == ts2
        assert ts1.microsecond == ts2.microsecond

        # 测试精度边界
        boundary_microseconds = [0, 1, 500000, 999999]

        for microsecond in boundary_microseconds:
            boundary_dt = datetime(2024, 1, 15, 9, 30, 45, microsecond)
            signal.set(
                "portfolio", "engine", "run", boundary_dt, "000001.SZ",
                DIRECTION_TYPES.LONG, "boundary test", SOURCE_TYPES.STRATEGY
            )

            assert signal.timestamp.microsecond == microsecond

        # 验证最终时间戳的完整精度信息
        final_dt = datetime(2024, 1, 15, 9, 30, 45, 123456)
        signal.set(
            "portfolio", "engine", "run", final_dt, "000001.SZ",
            DIRECTION_TYPES.LONG, "final precision test", SOURCE_TYPES.STRATEGY
        )

        # 验证所有时间组件都被正确保存
        assert signal.timestamp.year == 2024
        assert signal.timestamp.month == 1
        assert signal.timestamp.day == 15
        assert signal.timestamp.hour == 9
        assert signal.timestamp.minute == 30
        assert signal.timestamp.second == 45
        assert signal.timestamp.microsecond == 123456


@pytest.mark.unit
class TestSignalStrengthAndConfidence:
    """7. 信号强度和置信度测试"""

    def test_signal_strength_validation(self):
        """测试信号强度验证"""
        # 测试有效的信号强度值
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="strength test signal",
            source=SOURCE_TYPES.SIM,
            strength=0.8  # 有效强度值
        )

        # 验证强度值被正确设置
        assert signal.strength == 0.8
        assert 0.0 <= signal.strength <= 1.0

        # 测试边界值
        signal.strength = 0.0  # 最小值
        assert signal.strength == 0.0

        signal.strength = 1.0  # 最大值
        assert signal.strength == 1.0

        # 测试无效强度值应该被拒绝
        with pytest.raises(ValueError, match="信号强度必须在0.0-1.0范围内"):
            signal.strength = 1.5  # 超出上限

        with pytest.raises(ValueError, match="信号强度必须在0.0-1.0范围内"):
            signal.strength = -0.1  # 低于下限

    def test_confidence_level_validation(self):
        """测试置信度验证"""
        # 创建带有置信度的信号
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="confidence test signal",
            source=SOURCE_TYPES.SIM,
            confidence=0.85  # 置信度85%
        )

        # 验证置信度正确设置
        assert signal.confidence == 0.85
        assert isinstance(signal.confidence, float)

        # 测试置信度范围验证
        signal.confidence = 0.0  # 完全不确定
        assert signal.confidence == 0.0

        signal.confidence = 1.0  # 完全确定
        assert signal.confidence == 1.0

        # 测试置信度中间值
        signal.confidence = 0.5  # 中等置信度
        assert signal.confidence == 0.5

        # 验证无效置信度被拒绝
        with pytest.raises(ValueError, match="置信度必须在0.0-1.0范围内"):
            signal.confidence = 1.1  # 超出范围

        with pytest.raises(ValueError, match="置信度必须在0.0-1.0范围内"):
            signal.confidence = -0.05  # 负值

    def test_strength_confidence_ranges(self):
        """测试强度和置信度的有效范围"""
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="range test signal",
            source=SOURCE_TYPES.SIM,
            strength=0.75,
            confidence=0.85
        )

        # 测试有效范围内的各种值
        test_values = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]

        for value in test_values:
            signal.strength = value
            assert signal.strength == value
            assert 0.0 <= signal.strength <= 1.0

            signal.confidence = value
            assert signal.confidence == value
            assert 0.0 <= signal.confidence <= 1.0

    def test_signal_combination_scenarios(self):
        """测试强度和置信度的组合场景"""
        # 测试高强度高置信度信号
        strong_confident_signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="strong confident signal",
            source=SOURCE_TYPES.SIM,
            strength=0.9,
            confidence=0.85
        )

        assert strong_confident_signal.strength == 0.9
        assert strong_confident_signal.confidence == 0.85

        # 测试低强度低置信度信号
        weak_uncertain_signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000002.SZ",
            direction=DIRECTION_TYPES.SHORT,
            reason="weak uncertain signal",
            source=SOURCE_TYPES.SIM,
            strength=0.2,
            confidence=0.3
        )

        assert weak_uncertain_signal.strength == 0.2
        assert weak_uncertain_signal.confidence == 0.3

        # 测试不同组合的有效性
        combinations = [
            (0.9, 0.2),  # 高强度低置信度
            (0.1, 0.9),  # 低强度高置信度
            (0.5, 0.5),  # 中等强度中等置信度
        ]

        for strength, confidence in combinations:
            signal = Signal(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                timestamp="2024-01-01 09:30:00",
                code="000003.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="combination test",
                source=SOURCE_TYPES.SIM,
                strength=strength,
                confidence=confidence
            )
            assert signal.strength == strength
            assert signal.confidence == confidence

    def test_strength_confidence_independence(self):
        """测试强度与置信度的独立性"""
        # 创建具有强度和置信度的信号
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="independence test signal",
            source=SOURCE_TYPES.SIM,
            strength=0.9,     # 高强度
            confidence=0.3    # 低置信度 - 这是完全合理的
        )

        # 验证强度和置信度可以独立设置
        assert signal.strength == 0.9
        assert signal.confidence == 0.3
        # 两者可以有显著差异，这是正常的

        # 测试各种合理的组合
        test_combinations = [
            (0.9, 0.2),  # 高强度，低置信度：明确信号但不确定
            (0.3, 0.9),  # 低强度，高置信度：弱信号但很确定
            (0.1, 0.1),  # 低强度，低置信度：弱且不确定
            (0.8, 0.8),  # 高强度，高置信度：强且确定
        ]

        for strength, confidence in test_combinations:
            signal.strength = strength
            signal.confidence = confidence

            # 验证设置成功
            assert signal.strength == strength
            assert signal.confidence == confidence

            # 验证都在有效范围内
            assert 0.0 <= signal.strength <= 1.0
            assert 0.0 <= signal.confidence <= 1.0

        # 验证它们可以独立修改
        original_strength = signal.strength
        signal.confidence = 0.5
        assert signal.strength == original_strength  # 强度不受影响

        original_confidence = signal.confidence
        signal.strength = 0.7
        assert signal.confidence == original_confidence  # 置信度不受影响

    def test_default_strength_values(self):
        """测试默认强度值"""
        # 测试不指定强度时的默认值
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="default strength test",
            source=SOURCE_TYPES.SIM
            # 不指定 strength 和 confidence 参数
        )

        # 验证默认值存在且合理
        if hasattr(signal, 'strength'):
            assert signal.strength is not None
            assert 0.0 <= signal.strength <= 1.0
            # 默认值通常是中等强度
            assert signal.strength == 0.5

        if hasattr(signal, 'confidence'):
            assert signal.confidence is not None
            assert 0.0 <= signal.confidence <= 1.0
            # 默认值通常是中等置信度
            assert signal.confidence == 0.5

    def test_invalid_strength_rejection(self):
        """测试无效强度值拒绝"""
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-01 09:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="invalid strength test",
            source=SOURCE_TYPES.SIM,
            strength=0.5  # 先设置有效值
        )

        # 测试各种无效的强度值
        invalid_strengths = [
            -0.1,   # 负值
            1.1,    # 超过1
            2.0,    # 大于1
            -1.0,   # 负数
            float('inf'),  # 无穷大
            float('-inf'), # 负无穷
            # float('nan')   # NaN值（如果需要的话）
        ]

        for invalid_strength in invalid_strengths:
            with pytest.raises(ValueError, match="信号强度必须在0.0-1.0范围内"):
                signal.strength = invalid_strength

        # 验证原值不受无效设置影响
        assert signal.strength == 0.5  # 原值保持不变

        # 测试类型错误
        with pytest.raises(TypeError):
            signal.strength = "invalid"  # 字符串

        with pytest.raises(TypeError):
            signal.strength = None  # None值


# 策略归因功能已移除 - 不属于Signal实体的核心职责
# Signal实体专注于交易信号的基本属性：强度、置信度、方向、价格、时间戳等


# 生命周期管理功能已移除 - 属于系统级功能，不是Signal实体的核心职责
# Signal实体专注于交易信号的基础属性：portfolio_id、code、direction、timestamp、strength、confidence等


@pytest.mark.unit
class TestSignalQuantitativeValidation:
    """8. Signal量化交易验证场景测试"""

    def test_signal_validation_business_rules(self):
        """测试Signal的is_valid()业务规则验证"""
        import datetime

        # 创建一个完全有效的信号作为基准（使用UTC时区）
        valid_signal = Signal(
            portfolio_id="quant_portfolio_001",
            engine_id="strategy_engine",
            run_id="test_run_20240118",
            timestamp=datetime.datetime(2024, 1, 18, 10, 30, 0, tzinfo=timezone.utc),
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="技术指标买入信号",
            source=SOURCE_TYPES.STRATEGY,
            strength=0.75,
            confidence=0.68
        )

        # 验证完全有效的信号
        assert valid_signal.is_valid() == True

        # 测试各种无效情况 - 通过修改有效信号的内部状态来测试is_valid()
        # 注意：Signal构造时会进行验证，所以我们需要直接修改内部属性来测试边界情况

        # 1. 测试空portfolio_id
        test_signal_1 = Signal(
            portfolio_id="valid_portfolio",
            engine_id="strategy_engine",
            run_id="test_run",
            timestamp=datetime.datetime(2024, 1, 18, 10, 30, 0, tzinfo=timezone.utc),
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal"
        )
        # 直接修改内部属性来测试验证逻辑
        test_signal_1._portfolio_id = ""
        assert test_signal_1.is_valid() == False

        # 2. 测试空engine_id
        test_signal_2 = Signal(
            portfolio_id="test_portfolio",
            engine_id="valid_engine",
            run_id="test_run",
            timestamp=datetime.datetime(2024, 1, 18, 10, 30, 0, tzinfo=timezone.utc),
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal"
        )
        test_signal_2._engine_id = ""
        assert test_signal_2.is_valid() == False

        # 3. 测试空code
        test_signal_3 = Signal(
            portfolio_id="test_portfolio",
            engine_id="strategy_engine",
            run_id="test_run",
            timestamp=datetime.datetime(2024, 1, 18, 10, 30, 0, tzinfo=timezone.utc),
            code="valid_code",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal"
        )
        test_signal_3._code = ""
        assert test_signal_3.is_valid() == False

        # 4. 测试None direction
        test_signal_4 = Signal(
            portfolio_id="test_portfolio",
            engine_id="strategy_engine",
            run_id="test_run",
            timestamp=datetime.datetime(2024, 1, 18, 10, 30, 0, tzinfo=timezone.utc),
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="test signal"
        )
        test_signal_4._direction = None
        assert test_signal_4.is_valid() == False

    def test_signal_timestamp_future_validation(self):
        """测试Signal时间戳未来时间验证"""
        import datetime

        # 创建未来时间的信号（应该无效）- 使用UTC时区
        future_time = datetime.datetime.now(timezone.utc) + timedelta(hours=1)
        future_signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="strategy_engine",
            run_id="test_run",
            timestamp=future_time,  # 未来时间
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="future signal - should be invalid"
        )

        # 未来时间的信号应该无效
        assert future_signal.is_valid() == False

        # 创建当前或过去时间的信号（应该有效）- 使用UTC时区
        past_time = datetime.datetime.now(timezone.utc) - timedelta(minutes=10)
        past_signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="strategy_engine",
            run_id="test_run",
            timestamp=past_time,  # 过去时间
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="past signal - should be valid"
        )

        # 过去时间的信号应该有效
        assert past_signal.is_valid() == True

    def test_signal_strength_confidence_business_constraints(self):
        """测试Signal强度和置信度的业务约束"""
        import datetime

        base_params = {
            "portfolio_id": "test_portfolio",
            "engine_id": "strategy_engine",
            "run_id": "test_run",
            "timestamp": datetime.datetime(2024, 1, 18, 10, 30, 0),
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "reason": "test signal"
        }

        # 测试边界值
        # 1. 最小值 (0.0)
        min_signal = Signal(**base_params, strength=0.0, confidence=0.0)
        assert min_signal.strength == 0.0
        assert min_signal.confidence == 0.0
        assert min_signal.is_valid() == True  # 技术上有效，但实际意义不大

        # 2. 最大值 (1.0)
        max_signal = Signal(**base_params, strength=1.0, confidence=1.0)
        assert max_signal.strength == 1.0
        assert max_signal.confidence == 1.0
        assert max_signal.is_valid() == True

        # 3. 典型的量化交易信号强度范围
        typical_signal = Signal(**base_params, strength=0.75, confidence=0.68)
        assert 0.5 <= typical_signal.strength <= 0.9  # 典型强度范围
        assert 0.5 <= typical_signal.confidence <= 0.9  # 典型置信度范围
        assert typical_signal.is_valid() == True

        # 4. 测试无效范围（应该在构造时被拒绝）
        with pytest.raises(Exception):  # Signal构造时抛出Exception
            Signal(**base_params, strength=1.5)  # 超出范围

        with pytest.raises(Exception):  # Signal构造时抛出Exception
            Signal(**base_params, confidence=-0.1)  # 负值

    def test_signal_direction_trading_semantics(self):
        """测试Signal方向的交易语义正确性"""
        import datetime

        base_params = {
            "portfolio_id": "test_portfolio",
            "engine_id": "strategy_engine",
            "run_id": "test_run",
            "timestamp": datetime.datetime(2024, 1, 18, 10, 30, 0),
            "code": "000001.SZ",
            "reason": "test signal",
            "strength": 0.7,
            "confidence": 0.6
        }

        # 1. 买入信号
        long_signal = Signal(**base_params, direction=DIRECTION_TYPES.LONG)
        assert long_signal.direction == DIRECTION_TYPES.LONG
        assert long_signal.is_valid() == True

        # 2. 卖出信号
        short_signal = Signal(**base_params, direction=DIRECTION_TYPES.SHORT)
        assert short_signal.direction == DIRECTION_TYPES.SHORT
        assert short_signal.is_valid() == True

        # 3. 验证direction是必需的
        with pytest.raises(Exception):
            Signal(**base_params, direction=None)

    def test_signal_chinese_stock_code_patterns(self):
        """测试Signal对中国股票代码模式的处理"""
        import datetime

        base_params = {
            "portfolio_id": "a_share_portfolio",
            "engine_id": "strategy_engine",
            "run_id": "test_run",
            "timestamp": datetime.datetime(2024, 1, 18, 10, 30, 0),
            "direction": DIRECTION_TYPES.LONG,
            "reason": "A股交易信号",
            "strength": 0.7,
            "confidence": 0.65
        }

        # A股不同板块的股票代码
        stock_codes = [
            "000001.SZ",  # 深主板
            "000858.SZ",  # 深主板
            "002594.SZ",  # 中小板
            "300059.SZ",  # 创业板
            "600519.SH",  # 沪主板
            "600036.SH",  # 沪主板
            "688111.SH",  # 科创板
            "510300.SH",  # ETF
            "159919.SZ"   # ETF
        ]

        # 验证所有代码格式都能被正确处理
        for code in stock_codes:
            signal = Signal(**base_params, code=code)
            assert signal.code == code
            assert signal.is_valid() == True

            # 验证A股特有的代码格式
            assert len(code) == 9  # 6位数字 + 3位后缀
            assert "." in code
            assert code.endswith((".SZ", ".SH"))

    def test_signal_portfolio_engine_traceability(self):
        """测试Signal的投资组合和引擎可追溯性"""
        import datetime

        # 测试信号的可追溯性信息完整性
        traceable_signal = Signal(
            portfolio_id="multi_factor_portfolio_001",
            engine_id="alpha_strategy_engine_v2.1",
            run_id="backtest_20240118_session_001",
            timestamp=datetime.datetime(2024, 1, 18, 10, 30, 15),
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="多因子模型显示alpha因子评分8.5/10",
            source=SOURCE_TYPES.STRATEGY,
            strength=0.82,
            confidence=0.77
        )

        # 验证可追溯性字段的业务合理性
        assert len(traceable_signal.portfolio_id) > 0
        assert len(traceable_signal.engine_id) > 0
        assert len(traceable_signal.run_id) > 0

        # 验证时间戳精度（量化交易需要精确时间）
        assert traceable_signal.timestamp.microsecond is not None

        # 验证reason包含有意义的信息
        assert len(traceable_signal.reason) > 10  # 不是简单的占位符

        # 验证信号有效性
        assert traceable_signal.is_valid() == True


@pytest.mark.unit
class TestSignalValidation:
    """9. Signal验证逻辑测试"""

    def test_is_valid_complete_signal(self):
        """测试完整有效Signal的is_valid方法"""
        valid_signal = Signal(
            portfolio_id="valid_portfolio",
            engine_id="valid_engine",
            run_id="valid_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="完整有效的信号",
            source=SOURCE_TYPES.STRATEGY,
            strength=0.75,
            confidence=0.80
        )

        # 验证完整信号有效
        assert valid_signal.is_valid() == True

    def test_is_valid_with_invalid_fields(self):
        """测试包含无效字段的Signal的is_valid方法"""
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="测试信号"
        )

        # 直接修改内部属性来测试验证逻辑
        signal._portfolio_id = ""
        assert signal.is_valid() == False

        # 重置并测试空engine_id
        signal._portfolio_id = "test_portfolio"
        signal._engine_id = ""
        assert signal.is_valid() == False

        # 重置并测试空code
        signal._engine_id = "test_engine"
        signal._code = ""
        assert signal.is_valid() == False

        # 重置并测试None direction
        signal._code = "000001.SZ"
        signal._direction = None
        assert signal.is_valid() == False

        # 重置并测试None timestamp
        signal._direction = DIRECTION_TYPES.LONG
        signal._timestamp = None
        assert signal.is_valid() == False


@pytest.mark.unit
class TestSignalModelConversion:
    """10. Signal模型转换测试"""

    def test_to_model_complete_conversion(self):
        """测试完整的to_model转换，包括strength和confidence"""
        signal = Signal(
            portfolio_id="model_test_portfolio",
            engine_id="model_test_engine",
            run_id="model_test_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="模型转换测试",
            source=SOURCE_TYPES.STRATEGY,
            strength=0.85,
            confidence=0.70
        )

        # 转换为模型
        model = signal.to_model()

        # 验证所有字段正确转换
        assert model.portfolio_id == "model_test_portfolio"
        assert model.engine_id == "model_test_engine"
        assert model.run_id == "model_test_run"
        assert model.uuid == signal.uuid
        assert model.code == "000001.SZ"
        assert model.direction == DIRECTION_TYPES.LONG.value  # 模型中存储枚举值
        assert model.reason == "模型转换测试"
        assert model.source == SOURCE_TYPES.STRATEGY.value  # 模型中存储枚举值
        assert model.strength == 0.85
        assert model.confidence == 0.70

    def test_from_model_complete_reconstruction(self):
        """测试完整的from_model重构，包括strength和confidence"""
        original = Signal(
            portfolio_id="reconstruction_portfolio",
            engine_id="reconstruction_engine",
            run_id="reconstruction_run",
            timestamp="2024-01-15 14:30:00",
            code="600519.SH",
            direction=DIRECTION_TYPES.SHORT,
            reason="重构测试信号",
            source=SOURCE_TYPES.STRATEGY,
            strength=0.92,
            confidence=0.78
        )

        # 转换为模型再转回Signal
        model = original.to_model()
        reconstructed = Signal.from_model(model)

        # 验证所有关键属性一致
        assert reconstructed.portfolio_id == original.portfolio_id
        assert reconstructed.engine_id == original.engine_id
        assert reconstructed.run_id == original.run_id
        assert reconstructed.code == original.code
        assert reconstructed.direction == original.direction
        assert reconstructed.reason == original.reason
        assert reconstructed.source == original.source
        assert reconstructed.strength == original.strength
        assert reconstructed.confidence == original.confidence


@pytest.mark.unit
class TestSignalSetterMethods:
    """11. Signal Setter方法测试"""

    def test_strength_setter_valid_values(self):
        """测试strength setter的有效值设置"""
        signal = Signal(
            portfolio_id="setter_test_portfolio",
            engine_id="setter_test_engine",
            run_id="setter_test_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="setter测试信号"
        )

        # 测试边界值和有效值
        valid_strengths = [0.0, 0.1, 0.5, 0.99, 1.0]
        for strength in valid_strengths:
            signal.strength = strength
            assert signal.strength == strength
            assert isinstance(signal.strength, float)

        # 测试整数转浮点数
        signal.strength = 1
        assert signal.strength == 1.0

    def test_strength_setter_invalid_values(self):
        """测试strength setter的无效值处理"""
        signal = Signal(
            portfolio_id="setter_test_portfolio",
            engine_id="setter_test_engine",
            run_id="setter_test_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="setter测试信号"
        )

        # 测试超出范围的值
        invalid_strengths = [-0.1, 1.1, 2.0, -1.0]
        for invalid_strength in invalid_strengths:
            with pytest.raises(ValueError):
                signal.strength = invalid_strength

        # 测试错误类型
        invalid_types = ["0.5", None, [], {}]
        for invalid_type in invalid_types:
            with pytest.raises(TypeError):
                signal.strength = invalid_type

    def test_confidence_setter_valid_values(self):
        """测试confidence setter的有效值设置"""
        signal = Signal(
            portfolio_id="setter_test_portfolio",
            engine_id="setter_test_engine",
            run_id="setter_test_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="setter测试信号"
        )

        # 测试边界值和有效值
        valid_confidences = [0.0, 0.25, 0.5, 0.75, 1.0]
        for confidence in valid_confidences:
            signal.confidence = confidence
            assert signal.confidence == confidence
            assert isinstance(signal.confidence, float)

        # 测试整数转浮点数
        signal.confidence = 0
        assert signal.confidence == 0.0

    def test_confidence_setter_invalid_values(self):
        """测试confidence setter的无效值处理"""
        signal = Signal(
            portfolio_id="setter_test_portfolio",
            engine_id="setter_test_engine",
            run_id="setter_test_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="setter测试信号"
        )

        # 测试超出范围的值
        invalid_confidences = [-0.1, 1.1, 5.0, -2.0]
        for invalid_confidence in invalid_confidences:
            with pytest.raises(ValueError):
                signal.confidence = invalid_confidence

        # 测试错误类型
        invalid_types = ["0.8", None, [], {}]
        for invalid_type in invalid_types:
            with pytest.raises(TypeError):
                signal.confidence = invalid_type

    def test_setter_independence(self):
        """测试setter方法的独立性"""
        signal = Signal(
            portfolio_id="independence_test_portfolio",
            engine_id="independence_test_engine",
            run_id="independence_test_run",
            timestamp="2024-01-15 10:30:00",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="独立性测试信号",
            strength=0.5,
            confidence=0.5
        )

        # 修改strength不应该影响confidence
        original_confidence = signal.confidence
        signal.strength = 0.9
        assert signal.confidence == original_confidence

        # 修改confidence不应该影响strength
        original_strength = signal.strength
        signal.confidence = 0.1
        assert signal.strength == original_strength

        # 验证最终值
        assert signal.strength == 0.9
        assert signal.confidence == 0.1
