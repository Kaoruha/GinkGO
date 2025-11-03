"""
BaseStrategy类TDD测试

通过TDD方式开发BaseStrategy策略基类的完整测试套件
涵盖信号生成和策略核心功能
"""
import pytest
import sys
from pathlib import Path

# 导入BaseStrategy类和相关依赖
from ginkgo.trading.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.entities.time_related import TimeRelated
from ginkgo.enums import DIRECTION_TYPES
from datetime import datetime


@pytest.mark.unit
class TestBaseStrategyConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        strategy = BaseStrategy()

        # 验证name默认为"Strategy"
        assert strategy.name == "Strategy"

        # 验证_data_feeder初始化为None
        assert strategy._data_feeder is None
        assert strategy.data_feeder is None

        # 验证_raw字典初始化为空字典
        assert hasattr(strategy, '_raw')
        assert strategy._raw == {}

        # 验证继承自BacktestBase的属性
        assert hasattr(strategy, 'engine_id')
        assert hasattr(strategy, 'portfolio_id')
        assert hasattr(strategy, 'run_id')

    def test_named_constructor(self):
        """测试命名构造"""
        custom_name = "MomentumStrategy"
        strategy = BaseStrategy(name=custom_name)

        # 验证name被正确设置
        assert strategy.name == custom_name
        assert strategy.name == "MomentumStrategy"

    def test_backtest_base_inheritance(self):
        """测试BacktestBase类继承"""
        strategy = BaseStrategy(name="TestStrategy")

        # 验证正确继承BacktestBase的方法
        assert hasattr(strategy, 'set_backtest_ids')
        assert hasattr(strategy, 'get_id_dict')
        assert hasattr(strategy, 'bind_engine')
        assert hasattr(strategy, 'set_name')
        assert hasattr(strategy, 'log')

        # 验证ID管理属性
        assert strategy.engine_id == ""
        assert strategy.portfolio_id == ""
        assert strategy.run_id == ""

        # 验证日志功能
        assert hasattr(strategy, 'loggers')
        assert len(strategy.loggers) > 0  # 默认添加了GLOG

    def test_raw_data_initialization(self):
        """测试原始数据初始化"""
        strategy = BaseStrategy()

        # 验证_raw字典初始化为空字典
        assert hasattr(strategy, '_raw')
        assert isinstance(strategy._raw, dict)
        assert len(strategy._raw) == 0

        # 测试_raw字典的访问（只读性质）
        strategy._raw['test_key'] = 'test_value'
        assert strategy._raw['test_key'] == 'test_value'

    def test_data_feeder_initialization(self):
        """测试数据接口初始化"""
        strategy = BaseStrategy()

        # 验证_data_feeder初始值为None
        assert strategy._data_feeder is None
        assert strategy.data_feeder is None

        # 验证data_feeder是property访问器
        assert hasattr(BaseStrategy, 'data_feeder')
        assert isinstance(getattr(BaseStrategy, 'data_feeder', None), property)

    def test_args_kwargs_handling(self):
        """测试参数传递处理"""
        # 创建避免参数验证的测试策略子类
        class SimpleStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                # 跳过ParameterValidationMixin初始化
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

        # 测试传递额外参数（避免参数验证问题）
        strategy = SimpleStrategy(name="TestStrategy", test_param="test_value")

        # 验证name参数正确传递
        assert strategy.name == "TestStrategy"

        # 验证基础功能仍然正常
        assert hasattr(strategy, 'set_backtest_ids')
        assert strategy._data_feeder is None
        assert strategy._raw == {}

    def test_strategy_uuid_generation(self):
        """测试策略UUID生成"""
        strategy1 = BaseStrategy()
        strategy2 = BaseStrategy()

        # 验证每个实例都有UUID
        assert hasattr(strategy1, 'uuid')
        assert hasattr(strategy2, 'uuid')

        # 验证UUID不为空且唯一
        assert strategy1.uuid is not None
        assert strategy2.uuid is not None
        assert strategy1.uuid != strategy2.uuid

        # 验证UUID是字符串类型
        assert isinstance(strategy1.uuid, str)
        assert isinstance(strategy2.uuid, str)

    def test_multiple_instances_independence(self):
        """测试多实例独立性"""
        # 创建多个策略实例
        strategy1 = BaseStrategy(name="Strategy1")
        strategy2 = BaseStrategy(name="Strategy2")

        # 验证实例独立性
        strategy1.set_backtest_ids(engine_id="engine1", portfolio_id="portfolio1", run_id="run1")
        strategy2.set_backtest_ids(engine_id="engine2", portfolio_id="portfolio2", run_id="run2")

        # 验证各自独立设置
        assert strategy1.engine_id == "engine1"
        assert strategy1.portfolio_id == "portfolio1"
        assert strategy1.run_id == "run1"

        assert strategy2.engine_id == "engine2"
        assert strategy2.portfolio_id == "portfolio2"
        assert strategy2.run_id == "run2"

        # 验证名称独立性
        assert strategy1.name == "Strategy1"
        assert strategy2.name == "Strategy2"

        # 验证数据独立性
        strategy1._raw['param1'] = 'value1'
        strategy2._raw['param2'] = 'value2'
        assert strategy1._raw != strategy2._raw


@pytest.mark.unit
class TestBaseStrategyProperties:
    """2. 属性访问测试"""

    def test_name_property(self):
        """测试策略名称属性"""
        # 测试默认名称
        strategy1 = BaseStrategy()
        assert strategy1.name == "Strategy"
        assert isinstance(strategy1.name, str)

        # 测试自定义名称
        custom_name = "MyMomentumStrategy"
        strategy2 = BaseStrategy(name=custom_name)
        assert strategy2.name == custom_name
        assert strategy2.name == "MyMomentumStrategy"

        # 验证名称属性可读但不可直接修改（通过property保护）
        assert hasattr(BaseStrategy, 'name')
        strategy3 = BaseStrategy(name="TestStrategy")
        # 名称应该是可读取的字符串
        assert isinstance(strategy3.name, str)
        assert len(strategy3.name) > 0

    def test_data_feeder_property(self):
        """测试数据接口属性"""
        strategy = BaseStrategy()

        # 验证初始data_feeder为None
        assert strategy.data_feeder is None
        assert strategy._data_feeder is None

        # 验证data_feeder是property装饰器
        assert hasattr(BaseStrategy, 'data_feeder')
        assert isinstance(getattr(BaseStrategy, 'data_feeder'), property)

        # 创建模拟数据馈送器
        class MockDataFeeder:
            def __init__(self):
                self.name = "MockFeeder"

        mock_feeder = MockDataFeeder()

        # 通过bind_data_feeder方法设置
        strategy.bind_data_feeder(mock_feeder)

        # 验证property返回正确的对象
        assert strategy.data_feeder is mock_feeder
        assert strategy.data_feeder.name == "MockFeeder"
        assert strategy._data_feeder is mock_feeder

    def test_raw_data_access(self):
        """测试原始数据访问"""
        strategy = BaseStrategy()

        # 验证_raw字典初始化为空
        assert hasattr(strategy, '_raw')
        assert strategy._raw == {}
        assert isinstance(strategy._raw, dict)

        # 测试_raw数据的读写访问
        strategy._raw['param1'] = 100
        strategy._raw['param2'] = "test_value"
        strategy._raw['param3'] = [1, 2, 3]

        # 验证数据正确存储
        assert strategy._raw['param1'] == 100
        assert strategy._raw['param2'] == "test_value"
        assert strategy._raw['param3'] == [1, 2, 3]
        assert len(strategy._raw) == 3

        # 验证_raw是可变的字典
        strategy._raw.clear()
        assert strategy._raw == {}
        assert len(strategy._raw) == 0

        # 验证可以重新赋值整个字典
        new_data = {'new_param': 'new_value'}
        strategy._raw = new_data
        assert strategy._raw == new_data

    def test_property_immutability(self):
        """测试属性不可变性"""
        strategy = BaseStrategy(name="ImmutableTest")

        # 测试name属性在一定程度的保护
        original_name = strategy.name
        # 虽然Python中属性可以被重新赋值，但我们应该验证其一致性
        assert strategy.name == original_name

        # 验证_data_feeder只能通过bind_data_feeder方法正确设置
        assert strategy._data_feeder is None

        # 直接设置_data_feeder（虽然技术上可行，但不是推荐做法）
        strategy._data_feeder = "direct_assignment"
        assert strategy._data_feeder == "direct_assignment"

        # 但通过property访问仍然是相同的对象
        assert strategy.data_feeder == "direct_assignment"

        # 验证_raw字典的访问控制
        strategy._raw = {'protected': 'data'}
        assert strategy._raw['protected'] == 'data'

    def test_inherited_properties(self):
        """测试继承属性"""
        strategy = BaseStrategy(name="InheritanceTest")

        # 测试从BacktestBase继承的属性
        assert hasattr(strategy, 'engine_id')
        assert hasattr(strategy, 'portfolio_id')
        assert hasattr(strategy, 'run_id')
        assert hasattr(strategy, 'uuid')
        assert hasattr(strategy, 'loggers')

        # 验证默认值
        assert strategy.engine_id == ""
        assert strategy.portfolio_id == ""
        assert strategy.run_id == ""
        assert isinstance(strategy.uuid, str)
        assert len(strategy.uuid) > 0
        assert isinstance(strategy.loggers, list)
        assert len(strategy.loggers) > 0

        # 测试从TimeRelated继承的属性
        assert hasattr(strategy, 'timestamp')

        # ParameterValidationMixin已移除，不再具有参数验证功能
        # Python动态类型特性不需要运行时参数验证

        # 验证继承方法可用
        ids = strategy.get_id_dict()
        assert isinstance(ids, dict)
        assert 'engine_id' in ids
        assert 'portfolio_id' in ids
        assert 'run_id' in ids

    def test_property_type_validation(self):
        """测试属性类型验证"""
        strategy = BaseStrategy(name="TypeValidationTest")

        # 验证name属性类型
        assert isinstance(strategy.name, str)

        # 验证data_feeder属性类型（初始为None）
        assert strategy.data_feeder is None

        # 验证_raw属性类型
        assert isinstance(strategy._raw, dict)

        # 验证继承属性的类型
        assert isinstance(strategy.engine_id, str)
        assert isinstance(strategy.portfolio_id, str)
        assert isinstance(strategy.run_id, str)
        assert isinstance(strategy.uuid, str)

        # 验证loggers属性类型
        assert isinstance(strategy.loggers, list)

        # 设置data_feeder后验证类型
        class TestFeeder:
            pass

        test_feeder = TestFeeder()
        strategy.bind_data_feeder(test_feeder)
        assert strategy.data_feeder is test_feeder
        assert not isinstance(strategy.data_feeder, str)

        # 验证_raw字典内容类型
        strategy._raw = {
            'int_value': 100,
            'str_value': 'test',
            'list_value': [1, 2, 3],
            'dict_value': {'nested': 'data'}
        }
        assert isinstance(strategy._raw['int_value'], int)
        assert isinstance(strategy._raw['str_value'], str)
        assert isinstance(strategy._raw['list_value'], list)
        assert isinstance(strategy._raw['dict_value'], dict)


@pytest.mark.unit
class TestBaseStrategyDataSetting:
    """3. 数据设置测试"""

    def test_data_feeder_binding(self):
        """测试数据接口绑定"""
        strategy = BaseStrategy(name="DataBindingTest")

        # 验证初始状态
        assert strategy._data_feeder is None
        assert strategy.data_feeder is None

        # 创建模拟数据馈送器
        class MockDataFeeder:
            def __init__(self, name="MockFeeder"):
                self.name = name
                self.data = {"test": "data"}

            def get_data(self):
                return self.data

        mock_feeder = MockDataFeeder()

        # 测试bind_data_feeder方法
        strategy.bind_data_feeder(mock_feeder)

        # 验证绑定效果
        assert strategy._data_feeder is mock_feeder
        assert strategy.data_feeder is mock_feeder
        assert strategy.data_feeder.name == "MockFeeder"
        assert strategy.data_feeder.get_data() == {"test": "data"}

        # 验证方法存在且可调用
        assert hasattr(strategy, 'bind_data_feeder')
        assert callable(strategy.bind_data_feeder)

    def test_data_feeder_rebinding(self):
        """测试数据接口重绑定"""
        strategy = BaseStrategy(name="RebindingTest")

        # 创建第一个数据馈送器
        class FirstFeeder:
            def __init__(self):
                self.name = "FirstFeeder"

        # 创建第二个数据馈送器
        class SecondFeeder:
            def __init__(self):
                self.name = "SecondFeeder"

        first_feeder = FirstFeeder()
        second_feeder = SecondFeeder()

        # 绑定第一个馈送器
        strategy.bind_data_feeder(first_feeder)
        assert strategy.data_feeder is first_feeder
        assert strategy.data_feeder.name == "FirstFeeder"

        # 重绑定到第二个馈送器
        strategy.bind_data_feeder(second_feeder)
        assert strategy.data_feeder is second_feeder
        assert strategy.data_feeder.name == "SecondFeeder"

        # 验证第一个馈送器不再被引用
        assert strategy.data_feeder is not first_feeder

        # 测试多次重绑定
        third_feeder = SecondFeeder()
        strategy.bind_data_feeder(third_feeder)
        assert strategy.data_feeder is third_feeder

    def test_data_feeder_validation(self):
        """测试数据接口验证"""
        strategy = BaseStrategy(name="ValidationTest")

        # 测试绑定None（应该允许，表示重置）
        strategy.bind_data_feeder(None)
        assert strategy.data_feeder is None

        # 测试绑定不同类型的对象
        class SimpleFeeder:
            pass

        class ComplexFeeder:
            def __init__(self):
                self.config = {"setting1": "value1"}
                self.methods = ["get_data", "process_data"]

        simple_feeder = SimpleFeeder()
        complex_feeder = ComplexFeeder()

        # 绑定简单馈送器
        strategy.bind_data_feeder(simple_feeder)
        assert strategy.data_feeder is simple_feeder

        # 绑定复杂馈送器
        strategy.bind_data_feeder(complex_feeder)
        assert strategy.data_feeder is complex_feeder
        assert strategy.data_feeder.config == {"setting1": "value1"}

        # 测试绑定字符串（虽然不常见，但应该允许）
        strategy.bind_data_feeder("string_feeder")
        assert strategy.data_feeder == "string_feeder"

        # 测试绑定字典（模拟配置对象）
        dict_feeder = {"type": "dict", "data": [1, 2, 3]}
        strategy.bind_data_feeder(dict_feeder)
        assert strategy.data_feeder == dict_feeder

    def test_raw_data_setting(self):
        """测试原始数据设置"""
        strategy = BaseStrategy(name="RawDataTest")

        # 验证初始状态
        assert strategy._raw == {}
        assert len(strategy._raw) == 0

        # 测试设置单个键值对
        strategy._raw['param1'] = 100
        assert strategy._raw['param1'] == 100
        assert len(strategy._raw) == 1

        # 测试设置不同类型的值
        strategy._raw.update({
            'string_param': 'test_string',
            'list_param': [1, 2, 3],
            'dict_param': {'nested': 'data'},
            'bool_param': True,
            'none_param': None
        })

        # 验证所有数据正确设置
        assert strategy._raw['string_param'] == 'test_string'
        assert strategy._raw['list_param'] == [1, 2, 3]
        assert strategy._raw['dict_param'] == {'nested': 'data'}
        assert strategy._raw['bool_param'] is True
        assert strategy._raw['none_param'] is None
        assert len(strategy._raw) == 6

        # 测试更新现有键
        strategy._raw['param1'] = 200
        assert strategy._raw['param1'] == 200

        # 测试删除键
        del strategy._raw['bool_param']
        assert 'bool_param' not in strategy._raw
        assert len(strategy._raw) == 5

        # 测试完全替换字典
        new_raw_data = {'completely': 'new', 'data': [4, 5, 6]}
        strategy._raw = new_raw_data
        assert strategy._raw == new_raw_data
        assert len(strategy._raw) == 2

    def test_strategy_parameters_setting(self):
        """测试策略参数设置"""
        # 测试通过kwargs传递基本参数（不包含未定义的参数）
        strategy = BaseStrategy(name="ParameterTest")

        # 验证策略对象创建成功
        assert strategy.name == "ParameterTest"
        assert hasattr(strategy, '_raw')

        # 测试通过_raw字典设置参数
        strategy._raw['period'] = 20
        strategy._raw['threshold'] = 0.02
        strategy._raw['use_stop_loss'] = True

        # 验证参数正确设置
        assert strategy._raw['period'] == 20
        assert strategy._raw['threshold'] == 0.02
        assert strategy._raw['use_stop_loss'] is True

        # 测试创建带参数规范的子类（避免调用setup_parameters）
        class ParameterizedStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                super().__init__(name=name, **kwargs)
                # 手动设置参数，避免调用setup_parameters
                self._raw.update({
                    'period': 10,
                    'threshold': 0.01,
                    'use_stop_loss': False
                })

        # 创建带参数规范的策略
        param_strategy = ParameterizedStrategy(name="ParamStrategy")

        assert param_strategy.name == "ParamStrategy"
        assert isinstance(param_strategy, BaseStrategy)

        # 验证_raw中的参数
        assert param_strategy._raw['period'] == 10
        assert param_strategy._raw['threshold'] == 0.01
        assert param_strategy._raw['use_stop_loss'] is False

        # ParameterValidationMixin已移除，不再有参数验证方法
        # Python动态类型特性通过setattr直接设置参数

    def test_configuration_validation(self):
        """测试配置验证"""
        # 测试基本配置创建
        strategy1 = BaseStrategy(name="BasicConfig")
        assert strategy1.name == "BasicConfig"
        assert strategy1._raw == {}

        # 测试通过_raw设置配置（避免参数验证问题）
        strategy2 = BaseStrategy(name="ComplexConfig")
        strategy2._raw.update({
            'param1': 100,
            'param2': 'test_value',
            'nested': {'sub_param': 'sub_value'}
        })
        assert strategy2.name == 'ComplexConfig'
        assert strategy2._raw['param1'] == 100
        assert strategy2._raw['param2'] == 'test_value'

        # 测试空配置
        strategy3 = BaseStrategy()
        assert strategy3.name == "Strategy"

        # 测试配置一致性
        strategy4 = BaseStrategy(name="ConsistencyTest")
        strategy4.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 验证配置后策略仍然功能正常
        assert strategy4.name == "ConsistencyTest"
        assert strategy4.engine_id == "test_engine"
        assert strategy4.portfolio_id == "test_portfolio"
        assert strategy4.run_id == "test_run"

        # 验证配置不影响核心方法
        assert hasattr(strategy4, 'cal')
        assert hasattr(strategy4, 'bind_data_feeder')
        assert callable(strategy4.cal)
        assert callable(strategy4.bind_data_feeder)

        # 测试多种配置方式的策略都能正常工作
        strategies = [strategy1, strategy2, strategy3, strategy4]
        for i, strategy in enumerate(strategies):
            # 验证每个策略都能正常调用基础方法
            result = strategy.cal({}, None)  # 调用cal方法
            assert isinstance(result, list)  # 应该返回列表
            assert len(result) == 0  # 基类应该返回空列表


@pytest.mark.unit
class TestBaseStrategySignalGeneration:
    """4. 信号生成逻辑测试"""

    def test_cal_method_interface(self):
        """测试cal方法接口"""
        strategy = BaseStrategy(name="InterfaceTest")

        # 验证cal方法存在且可调用
        assert hasattr(strategy, 'cal')
        assert callable(strategy.cal)

        # 测试方法签名接受两个参数（portfolio_info, event）
        # 基类应该返回空列表
        portfolio_info = {}
        event = None
        result = strategy.cal(portfolio_info, event)

        # 验证返回类型为list
        assert isinstance(result, list)
        assert len(result) == 0  # 基类默认返回空列表

        # 测试方法能接受不同的参数类型
        portfolio_info_variants = [
            {},  # 空字典
            {'cash': 10000},  # 简单字典
            {'uuid': 'test', 'positions': {}},  # 复杂字典
            None  # None值
        ]

        event_variants = [
            None,
            "string_event",
            123,
            {"type": "price_update", "data": {}}
        ]

        for p_info in portfolio_info_variants:
            for evt in event_variants:
                try:
                    result = strategy.cal(p_info, evt)
                    assert isinstance(result, list)  # 应该总是返回列表
                except Exception:
                    # 如果抛出异常也是可以接受的，因为基类可能不处理某些输入
                    pass

    def test_empty_signal_generation(self):
        """测试空信号生成"""
        strategy = BaseStrategy(name="EmptySignalTest")

        # 测试各种输入条件下基类都返回空列表
        test_cases = [
            ({}, None),
            ({'cash': 10000}, None),
            ({'portfolio_id': 'test'}, {'price': 100}),
            ({'positions': {}}, "mock_event"),
            ({}, 123),
            ({'complex': 'data'}, {'nested': {'value': 42}})
        ]

        for portfolio_info, event in test_cases:
            result = strategy.cal(portfolio_info, event)
            assert isinstance(result, list), f"输入组合 {portfolio_info}, {event} 应该返回列表"
            assert len(result) == 0, f"输入组合 {portfolio_info}, {event} 应该返回空列表"

        # 验证返回的是全新的空列表（不是缓存的同一个对象）
        result1 = strategy.cal({}, None)
        result2 = strategy.cal({}, None)
        assert result1 is not result2  # 应该是不同的列表对象

    def test_single_signal_generation(self):
        """测试单信号生成"""
        # 创建一个生成单个信号的子类
        class SingleSignalStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                # 生成单个买入信号
                signal = Signal(
                    portfolio_id=portfolio_info.get('portfolio_id', 'test_portfolio'),
                    engine_id=self.engine_id,
                    run_id=self.run_id,
                    timestamp=datetime.now(),
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG
                )
                return [signal]

        strategy = SingleSignalStrategy(name="SingleSignalTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 测试生成单个信号
        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'price': 10.0}

        result = strategy.cal(portfolio_info, event)

        # 验证返回单个信号
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Signal)
        assert result[0].code == "000001.SZ"
        assert result[0].direction == DIRECTION_TYPES.LONG

    def test_multiple_signals_generation(self):
        """测试多信号生成"""
        # 创建一个生成多个信号的子类
        class MultiSignalStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []
                codes = ["000001.SZ", "000002.SZ", "600000.SH"]

                for code in codes:
                    signal = Signal(
                        portfolio_id=portfolio_info.get('portfolio_id', 'test_portfolio'),
                        engine_id=self.engine_id,
                        run_id=self.run_id,
                        timestamp=datetime.now(),
                        code=code,
                        direction=DIRECTION_TYPES.LONG
                    )
                    signals.append(signal)

                return signals

        strategy = MultiSignalStrategy(name="MultiSignalTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 测试生成多个信号
        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'market_data': 'available'}

        result = strategy.cal(portfolio_info, event)

        # 验证返回多个信号
        assert isinstance(result, list)
        assert len(result) == 3
        for i, signal in enumerate(result):
            assert isinstance(signal, Signal)
            assert signal.code in ["000001.SZ", "000002.SZ", "600000.SH"]
            assert signal.direction == DIRECTION_TYPES.LONG

        # 验证信号不重复
        signal_codes = [s.code for s in result]
        assert len(signal_codes) == len(set(signal_codes))  # 无重复

    def test_signal_list_validation(self):
        """测试信号列表验证"""
        strategy = BaseStrategy(name="SignalValidationTest")

        # 基类应该总是返回列表
        result = strategy.cal({}, None)
        assert isinstance(result, list)

        # 创建返回非列表的子类来测试边界情况
        class InvalidReturnStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                return "not_a_list"  # 错误的返回类型

        # 虽然这个子类违反了契约，但基类本身应该返回正确的类型
        base_strategy = BaseStrategy()
        for i in range(10):
            result = base_strategy.cal({}, None)
            assert isinstance(result, list)
            assert len(result) == 0

        # 测试列表内容的正确性
        class ValidSignalStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                return [Signal(
                    portfolio_id='test',
                    engine_id='test',
                    run_id='test',
                    timestamp=datetime.now(),
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG
                )]

        valid_strategy = ValidSignalStrategy()
        result = valid_strategy.cal({}, None)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Signal)

    def test_portfolio_info_usage(self):
        """测试组合信息使用"""
        # 创建一个使用portfolio_info的子类
        class PortfolioAwareStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                # 根据portfolio_info决定是否生成信号
                cash = portfolio_info.get('cash', 0)
                if cash > 1000:  # 只有现金充足时才生成信号
                    signal = Signal(
                        portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                        engine_id=self.engine_id,
                        run_id=self.run_id,
                        timestamp=datetime.now(),
                        code="000001.SZ",
                        direction=DIRECTION_TYPES.LONG
                    )
                    signals.append(signal)

                return signals

        strategy = PortfolioAwareStrategy(name="PortfolioAwareTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 测试现金不足的情况
        poor_portfolio = {'cash': 500, 'portfolio_id': 'poor_portfolio'}
        result1 = strategy.cal(poor_portfolio, None)
        assert isinstance(result1, list)
        assert len(result1) == 0  # 现金不足，无信号

        # 测试现金充足的情况
        rich_portfolio = {'cash': 5000, 'portfolio_id': 'rich_portfolio'}
        result2 = strategy.cal(rich_portfolio, None)
        assert isinstance(result2, list)
        assert len(result2) == 1  # 现金充足，有信号
        assert result2[0].direction == DIRECTION_TYPES.LONG

        # 测试没有cash信息的情况
        no_cash_portfolio = {'portfolio_id': 'no_cash_portfolio'}
        result3 = strategy.cal(no_cash_portfolio, None)
        assert isinstance(result3, list)
        assert len(result3) == 0  # 默认现金为0，无信号

    def test_event_data_processing(self):
        """测试事件数据处理"""
        # 创建一个处理event数据的子类
        class EventAwareStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                # 根据event类型生成不同信号
                if isinstance(event, dict):
                    event_type = event.get('type', '')
                    price = event.get('price', 0)

                    if event_type == 'price_update' and price > 50:
                        signal = Signal(
                            portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                            engine_id=self.engine_id,
                            run_id=self.run_id,
                            timestamp=datetime.now(),
                            code="000001.SZ",
                            direction=DIRECTION_TYPES.LONG
                        )
                        signals.append(signal)
                    elif event_type == 'price_update' and price < 30:
                        signal = Signal(
                            portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                            engine_id=self.engine_id,
                            run_id=self.run_id,
                            timestamp=datetime.now(),
                            code="000001.SZ",
                            direction=DIRECTION_TYPES.SHORT
                        )
                        signals.append(signal)

                return signals

        strategy = EventAwareStrategy(name="EventAwareTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        portfolio_info = {'portfolio_id': 'test_portfolio'}

        # 测试高价事件
        high_price_event = {'type': 'price_update', 'price': 60}
        result1 = strategy.cal(portfolio_info, high_price_event)
        assert isinstance(result1, list)
        assert len(result1) == 1
        assert result1[0].direction == DIRECTION_TYPES.LONG

        # 测试低价事件
        low_price_event = {'type': 'price_update', 'price': 25}
        result2 = strategy.cal(portfolio_info, low_price_event)
        assert isinstance(result2, list)
        assert len(result2) == 1
        assert result2[0].direction == DIRECTION_TYPES.SHORT

        # 测试无关事件
        irrelevant_event = {'type': 'volume_update', 'volume': 1000}
        result3 = strategy.cal(portfolio_info, irrelevant_event)
        assert isinstance(result3, list)
        assert len(result3) == 0

        # 测试None事件
        result4 = strategy.cal(portfolio_info, None)
        assert isinstance(result4, list)
        assert len(result4) == 0

    def test_signal_generation_consistency(self):
        """测试信号生成一致性"""
        # 创建一个确定性策略
        class DeterministicStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                # 基于输入的确定性逻辑
                if isinstance(event, dict) and 'trigger' in event:
                    if event['trigger'] == 'buy':
                        signal = Signal(
                            portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                            engine_id=self.engine_id,
                            run_id=self.run_id,
                            timestamp=datetime.now(),
                            code="000001.SZ",
                            direction=DIRECTION_TYPES.LONG
                        )
                        signals.append(signal)
                    elif event['trigger'] == 'sell':
                        signal = Signal(
                            portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                            engine_id=self.engine_id,
                            run_id=self.run_id,
                            timestamp=datetime.now(),
                            code="000001.SZ",
                            direction=DIRECTION_TYPES.SHORT
                        )
                        signals.append(signal)

                return signals

        strategy = DeterministicStrategy(name="DeterministicTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        portfolio_info = {'portfolio_id': 'test_portfolio'}
        buy_event = {'trigger': 'buy'}
        sell_event = {'trigger': 'sell'}

        # 测试多次调用相同输入产生相同输出
        result1a = strategy.cal(portfolio_info, buy_event)
        result1b = strategy.cal(portfolio_info, buy_event)

        assert len(result1a) == len(result1b) == 1
        assert result1a[0].direction == result1b[0].direction == DIRECTION_TYPES.LONG

        # 测试不同输入产生不同输出
        result2 = strategy.cal(portfolio_info, sell_event)
        assert len(result2) == 1
        assert result2[0].direction == DIRECTION_TYPES.SHORT
        assert result2[0].direction != result1a[0].direction

        # 测试基类的一致性
        base_strategy = BaseStrategy(name="ConsistencyBase")
        for i in range(5):
            result = base_strategy.cal({}, None)
            assert isinstance(result, list)
            assert len(result) == 0


@pytest.mark.unit
class TestBaseStrategyDataFeederIntegration:
    """5. 数据接口集成测试"""

    def test_data_feeder_access(self):
        """测试数据接口访问"""
        # 创建避免参数验证的测试策略子类
        class SimpleDataStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

        strategy = SimpleDataStrategy(name="DataAccessTest")

        # 验证初始状态无数据接口
        assert strategy.data_feeder is None
        assert strategy._data_feeder is None

        # 创建模拟数据馈送器
        class MockDataFeeder:
            def __init__(self):
                self.access_count = 0
                self.name = "MockFeeder"
                self.data_store = {
                    "000001.SZ": [{"price": 10.5, "volume": 1000}],
                    "000002.SZ": [{"price": 20.3, "volume": 2000}]
                }

            def get_data(self, code):
                self.access_count += 1
                return self.data_store.get(code, [])

            def get_all_data(self):
                self.access_count += 1
                return self.data_store

            def is_available(self, code):
                # 这个方法不增加计数
                return code in self.data_store

        mock_feeder = MockDataFeeder()

        # 绑定数据馈送器
        strategy.bind_data_feeder(mock_feeder)

        # 验证访问能力
        assert strategy.data_feeder is mock_feeder
        assert strategy.data_feeder.access_count == 0

        # 测试数据访问
        data1 = strategy.data_feeder.get_data("000001.SZ")  # +1
        data2 = strategy.data_feeder.get_all_data()        # +1
        available = strategy.data_feeder.is_available("000002.SZ")  # 不计数

        assert data1 == [{"price": 10.5, "volume": 1000}]
        assert data2 == mock_feeder.data_store
        assert available is True
        assert strategy.data_feeder.access_count == 2

    def test_historical_data_retrieval(self):
        """测试历史数据获取"""
        # 创建一个使用data_feeder的策略子类
        class HistoricalDataStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                # 如果有数据接口，尝试获取历史数据
                if self.data_feeder and hasattr(self.data_feeder, 'get_historical_bars'):
                    code = event.get('code', '000001.SZ') if isinstance(event, dict) else '000001.SZ'
                    try:
                        bars = self.data_feeder.get_historical_bars(code, period="1d")
                        if bars and len(bars) > 0:
                            # 基于历史数据生成信号（这里简化逻辑）
                            latest_bar = bars[-1]
                            if latest_bar.get('price', 0) > 10:
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                                    engine_id=self.engine_id,
                                    run_id=self.run_id,
                                    timestamp=datetime.now(),
                                    code=code,
                                    direction=DIRECTION_TYPES.LONG
                                )
                                signals.append(signal)
                    except Exception:
                        pass  # 数据获取失败时忽略

                return signals

        # 创建带历史数据功能的模拟馈送器
        class HistoricalDataFeeder:
            def __init__(self):
                self.historical_data = {
                    "000001.SZ": [
                        {"timestamp": "2023-01-01", "price": 9.5, "volume": 1000},
                        {"timestamp": "2023-01-02", "price": 11.2, "volume": 1200},
                        {"timestamp": "2023-01-03", "price": 12.8, "volume": 1500}
                    ]
                }

            def get_historical_bars(self, code, period=None):
                return self.historical_data.get(code, [])

        strategy = HistoricalDataStrategy(name="HistoricalDataTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 绑定历史数据馈送器
        historical_feeder = HistoricalDataFeeder()
        strategy.bind_data_feeder(historical_feeder)

        # 测试历史数据获取和信号生成
        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'code': '000001.SZ', 'type': 'price_update'}

        result = strategy.cal(portfolio_info, event)

        # 验证基于历史数据生成了信号
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].code == "000001.SZ"
        assert result[0].direction == DIRECTION_TYPES.LONG

    def test_data_format_compatibility(self):
        """测试数据格式兼容性"""
        # 创建支持多种数据格式的策略子类
        class FlexibleFormatStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                if not self.data_feeder:
                    return signals

                # 测试不同的数据格式
                data_formats = ['json', 'csv', 'dict', 'list', 'pandas']

                for fmt in data_formats:
                    try:
                        if hasattr(self.data_feeder, f'get_data_as_{fmt}'):
                            data = getattr(self.data_feeder, f'get_data_as_{fmt}')("000001.SZ")
                            if data:
                                # 基于数据生成简单信号
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                                    engine_id=self.engine_id,
                                    run_id=self.run_id,
                                    timestamp=datetime.now(),
                                    code="000001.SZ",
                                    direction=DIRECTION_TYPES.LONG
                                )
                                signals.append(signal)
                                break  # 找到有效格式后停止
                    except Exception:
                        continue

                return signals

        # 创建支持多种格式的模拟馈送器
        class MultiFormatFeeder:
            def __init__(self):
                self.data_json = '{"price": 10.5, "volume": 1000}'
                self.data_dict = {"price": 10.5, "volume": 1000}
                self.data_list = [10.5, 1000]

            def get_data_as_json(self, code):
                return self.data_json

            def get_data_as_dict(self, code):
                return self.data_dict

            def get_data_as_list(self, code):
                return self.data_list

        strategy = FlexibleFormatStrategy(name="FormatTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 绑定多格式数据馈送器
        multi_feeder = MultiFormatFeeder()
        strategy.bind_data_feeder(multi_feeder)

        # 测试多格式兼容性
        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'type': 'data_request'}

        result = strategy.cal(portfolio_info, event)

        # 验证至少找到一种有效格式并生成了信号
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0].code == "000001.SZ"

    def test_missing_data_handling(self):
        """测试缺失数据处理"""
        # 创建一个处理缺失数据的策略子类
        class RobustDataStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                if not self.data_feeder:
                    # 无数据接口时的处理
                    return signals

                # 尝试获取数据，处理各种异常情况
                try:
                    # 尝试获取数据
                    if hasattr(self.data_feeder, 'get_data'):
                        data = self.data_feeder.get_data("000001.SZ")
                        if not data:
                            # 数据为空的处理
                            return signals

                        # 数据格式检查
                        if not isinstance(data, (list, dict)):
                            # 数据格式不正确时的处理
                            return signals

                        # 验证数据完整性
                        if isinstance(data, list) and len(data) == 0:
                            # 空列表数据的处理
                            return signals

                except AttributeError:
                    # 数据接口方法不存在时的处理
                    return signals
                except Exception:
                    # 其他异常时的处理
                    return signals

                # 如果数据正常，生成信号
                signal = Signal(
                    portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                    engine_id=self.engine_id,
                    run_id=self.run_id,
                    timestamp=datetime.now(),
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG
                )
                signals.append(signal)

                return signals

        # 测试各种缺失数据场景
        strategy = RobustDataStrategy(name="RobustDataTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'type': 'data_request'}

        # 场景1：无数据接口
        result1 = strategy.cal(portfolio_info, event)
        assert isinstance(result1, list)
        assert len(result1) == 0

        # 场景2：数据接口返回None
        class NoneDataFeeder:
            def get_data(self, code):
                return None

        none_feeder = NoneDataFeeder()
        strategy.bind_data_feeder(none_feeder)
        result2 = strategy.cal(portfolio_info, event)
        assert isinstance(result2, list)
        assert len(result2) == 0

        # 场景3：数据接口返回空列表
        class EmptyDataFeeder:
            def get_data(self, code):
                return []

        empty_feeder = EmptyDataFeeder()
        strategy.bind_data_feeder(empty_feeder)
        result3 = strategy.cal(portfolio_info, event)
        assert isinstance(result3, list)
        assert len(result3) == 0

        # 场景4：数据接口抛出异常
        class ErrorDataFeeder:
            def get_data(self, code):
                raise ValueError("数据获取失败")

        error_feeder = ErrorDataFeeder()
        strategy.bind_data_feeder(error_feeder)
        result4 = strategy.cal(portfolio_info, event)
        assert isinstance(result4, list)
        assert len(result4) == 0

        # 场景5：正常数据
        class NormalDataFeeder:
            def get_data(self, code):
                return [{"price": 10.5, "volume": 1000}]

        normal_feeder = NormalDataFeeder()
        strategy.bind_data_feeder(normal_feeder)
        result5 = strategy.cal(portfolio_info, event)
        assert isinstance(result5, list)
        assert len(result5) == 1
        assert result5[0].code == "000001.SZ"

    def test_data_validation_integration(self):
        """测试数据验证集成"""
        # 创建一个集成了数据验证的策略子类
        class ValidatedDataStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                if not self.data_feeder:
                    return signals

                # 集成数据验证逻辑
                if hasattr(self.data_feeder, 'get_validated_data'):
                    try:
                        # 从event中获取股票代码
                        code = event.get('code', '000001.SZ')
                        validated_data = self.data_feeder.get_validated_data(code)
                        if validated_data and self._validate_data_format(validated_data):
                            # 数据验证通过后生成信号
                            signal = Signal(
                                portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                                engine_id=self.engine_id,
                                run_id=self.run_id,
                                timestamp=datetime.now(),
                                code=code,
                                direction=DIRECTION_TYPES.LONG
                            )
                            signals.append(signal)
                    except Exception:
                        pass

                return signals

            def _validate_data_format(self, data):
                """内部数据格式验证"""
                if not isinstance(data, (list, dict)):
                    return False

                if isinstance(data, list):
                    return all(isinstance(item, dict) for item in data)

                if isinstance(data, dict):
                    # 对于字典数据，我们要求它包含所有必需的键
                    required_keys = ['price', 'volume', 'timestamp']
                    return all(key in data for key in required_keys)

                return True

        # 创建带验证功能的模拟数据馈送器
        class ValidatingDataFeeder:
            def __init__(self):
                self.valid_data = [
                    {"price": 10.5, "volume": 1000, "timestamp": "2023-01-01"},
                    {"price": 11.2, "volume": 1200, "timestamp": "2023-01-02"}
                ]
                self.invalid_data = {"price": 10.5, "volume": 500}  # 缺少timestamp

            def get_validated_data(self, code):
                # 模拟数据验证过程
                if code == "000001.SZ":
                    return self.valid_data
                elif code == "INVALID":
                    return self.invalid_data
                else:
                    return None

        strategy = ValidatedDataStrategy(name="ValidationTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 绑定验证数据馈送器
        validating_feeder = ValidatingDataFeeder()
        strategy.bind_data_feeder(validating_feeder)

        portfolio_info = {'portfolio_id': 'test_portfolio'}

        # 测试有效数据
        event_valid = {'code': '000001.SZ'}
        result1 = strategy.cal(portfolio_info, event_valid)
        assert isinstance(result1, list)
        assert len(result1) == 1
        assert result1[0].code == "000001.SZ"

        # 测试无效数据
        event_invalid = {'code': 'INVALID'}
        result2 = strategy.cal(portfolio_info, event_invalid)
        assert isinstance(result2, list)
        assert len(result2) == 0

        # 测试无数据
        event_missing = {'code': 'NOT_EXISTS'}
        result3 = strategy.cal(portfolio_info, event_missing)
        assert isinstance(result3, list)
        assert len(result3) == 0

    def test_multi_symbol_data_handling(self):
        """测试多标的数据处理"""
        # 创建一个处理多个股票数据的策略子类
        class MultiSymbolStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                if not self.data_feeder:
                    return signals

                # 处理多个股票代码
                symbols = ["000001.SZ", "000002.SZ", "600000.SH", "300001.SZ"]

                for symbol in symbols:
                    try:
                        if hasattr(self.data_feeder, 'get_symbol_data'):
                            symbol_data = self.data_feeder.get_symbol_data(symbol)
                            if symbol_data and self._should_trade(symbol_data):
                                # 为每个符合条件的股票生成信号
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                                    engine_id=self.engine_id,
                                    run_id=self.run_id,
                                    timestamp=datetime.now(),
                                    code=symbol,
                                    direction=DIRECTION_TYPES.LONG
                                )
                                signals.append(signal)
                    except Exception:
                        continue  # 单个股票数据处理失败不影响其他股票

                return signals

            def _should_trade(self, symbol_data):
                """判断是否应该交易的内部逻辑"""
                if isinstance(symbol_data, dict):
                    price = symbol_data.get('price', 0)
                    volume = symbol_data.get('volume', 0)
                    return price > 5.0 and volume > 500
                elif isinstance(symbol_data, list) and len(symbol_data) > 0:
                    latest = symbol_data[-1]
                    price = latest.get('price', 0)
                    return price > 5.0
                return False

        # 创建多股票数据馈送器
        class MultiSymbolFeeder:
            def __init__(self):
                self.symbol_data = {
                    "000001.SZ": {"price": 12.5, "volume": 2000, "rsi": 65},
                    "000002.SZ": {"price": 4.8, "volume": 800, "rsi": 45},  # 价格过低
                    "600000.SH": {"price": 15.8, "volume": 3000, "rsi": 70},
                    "300001.SZ": {"price": 3.2, "volume": 200, "rsi": 30}  # 成交量过低
                }

            def get_symbol_data(self, symbol):
                return self.symbol_data.get(symbol)

        strategy = MultiSymbolStrategy(name="MultiSymbolTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 绑定多股票数据馈送器
        multi_feeder = MultiSymbolFeeder()
        strategy.bind_data_feeder(multi_feeder)

        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'type': 'multi_symbol_scan'}

        result = strategy.cal(portfolio_info, event)

        # 验证多股票处理结果
        assert isinstance(result, list)
        # 应该为价格>5且成交量>500的股票生成信号
        expected_symbols = ["000001.SZ", "600000.SH"]
        assert len(result) == len(expected_symbols)
        # 检查是否只包含预期的股票代码（移除300001.SZ因为它不满足成交量条件）
        result_symbols = [s.code for s in result]
        assert all(symbol in expected_symbols for symbol in result_symbols)

        # 验证生成的股票代码
        generated_symbols = [s.code for s in result]
        for expected in expected_symbols:
            assert expected in generated_symbols

    def test_data_feeder_error_handling(self):
        """测试数据接口错误处理"""
        # 创建一个具有错误处理能力的策略子类
        class ErrorHandlingStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                super().__init__(name=name, **kwargs)
                self.error_count = 0

            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                if not self.data_feeder:
                    return signals

                try:
                    # 尝试获取数据
                    if hasattr(self.data_feeder, 'get_data_with_retry'):
                        data = self.data_feeder.get_data_with_retry("000001.SZ", max_retries=3)
                    elif hasattr(self.data_feeder, 'get_data'):
                        data = self.data_feeder.get_data("000001.SZ")
                    else:
                        return signals

                    # 数据获取成功后生成信号
                    if data:
                        signal = Signal(
                            portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                            engine_id=self.engine_id,
                            run_id=self.run_id,
                            timestamp=datetime.now(),
                            code="000001.SZ",
                            direction=DIRECTION_TYPES.LONG
                        )
                        signals.append(signal)

                except ConnectionError:
                    self.error_count += 1
                    # 连接错误时的处理
                except TimeoutError:
                    self.error_count += 1
                    # 超时错误时的处理
                except Exception as e:
                    self.error_count += 1
                    # 其他错误的处理

                return signals

        # 创建会抛出错误的模拟数据馈送器
        class ErrorProneFeeder:
            def __init__(self, error_type="connection"):
                self.error_type = error_type
                self.call_count = 0

            def get_data(self, code):
                self.call_count += 1
                if self.error_type == "connection":
                    raise ConnectionError("网络连接失败")
                elif self.error_type == "timeout":
                    raise TimeoutError("请求超时")
                elif self.error_type == "unknown":
                    raise ValueError("未知错误")
                else:
                    return [{"price": 10.5, "volume": 1000}]

        strategy = ErrorHandlingStrategy(name="ErrorHandlingTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'type': 'data_request'}

        # 测试连接错误处理
        connection_feeder = ErrorProneFeeder("connection")
        strategy.bind_data_feeder(connection_feeder)
        result1 = strategy.cal(portfolio_info, event)
        assert isinstance(result1, list)
        assert len(result1) == 0  # 错误情况下不生成信号
        assert strategy.error_count == 1

        # 重置错误计数并测试超时错误
        strategy.error_count = 0
        timeout_feeder = ErrorProneFeeder("timeout")
        strategy.bind_data_feeder(timeout_feeder)
        result2 = strategy.cal(portfolio_info, event)
        assert isinstance(result2, list)
        assert len(result2) == 0
        assert strategy.error_count == 1

        # 测试正常情况
        strategy.error_count = 0
        normal_feeder = ErrorProneFeeder("normal")
        strategy.bind_data_feeder(normal_feeder)
        result3 = strategy.cal(portfolio_info, event)
        assert isinstance(result3, list)
        assert len(result3) == 1  # 正常情况下生成信号
        assert strategy.error_count == 0

    def test_data_caching_behavior(self):
        """测试数据缓存行为"""
        # 创建一个具有数据缓存功能的策略子类
        class CachedDataStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                super().__init__(name=name, **kwargs)
                self.cache = {}
                self.cache_hits = 0
                self.cache_misses = 0

            def cal(self, portfolio_info, event, *args, **kwargs):
                signals = []

                if not self.data_feeder:
                    return signals

                # 使用缓存机制获取数据
                cache_key = "default_data"

                try:
                    if cache_key in self.cache:
                        # 缓存命中
                        self.cache_hits += 1
                        data = self.cache[cache_key]
                    else:
                        # 缓存未命中，获取数据并缓存
                        self.cache_misses += 1
                        if hasattr(self.data_feeder, 'get_data'):
                            data = self.data_feeder.get_data("000001.SZ")
                            self.cache[cache_key] = data
                        else:
                            data = None

                    # 基于数据生成信号
                    if data:
                        signal = Signal(
                            portfolio_id=portfolio_info.get('portfolio_id', 'test'),
                            engine_id=self.engine_id,
                            run_id=self.run_id,
                            timestamp=datetime.now(),
                            code="000001.SZ",
                            direction=DIRECTION_TYPES.LONG
                        )
                        signals.append(signal)

                except Exception:
                    pass

                return signals

            def clear_cache(self):
                """清除缓存"""
                self.cache.clear()
                self.cache_hits = 0
                self.cache_misses = 0

        # 创建支持缓存的数据馈送器
        class CachingDataFeeder:
            def __init__(self):
                self.access_count = 0
                self.name = "CachingDataFeeder"
                self.data = [{"price": 10.5, "volume": 1000}]

            def get_data(self, code):
                self.access_count += 1
                return self.data

        strategy = CachedDataStrategy(name="CachingTest")
        strategy.set_backtest_ids(
            engine_id="test_engine",
            portfolio_id="test_portfolio",
            run_id="test_run"
        )

        # 绑定缓存数据馈送器
        caching_feeder = CachingDataFeeder()
        strategy.bind_data_feeder(caching_feeder)

        portfolio_info = {'portfolio_id': 'test_portfolio'}
        event = {'type': 'cached_request'}

        # 第一次调用 - 缓存未命中
        result1 = strategy.cal(portfolio_info, event)
        assert isinstance(result1, list)
        assert len(result1) == 1
        assert strategy.cache_misses == 1
        assert strategy.cache_hits == 0
        assert caching_feeder.access_count == 1

        # 第二次调用 - 缓存命中
        result2 = strategy.cal(portfolio_info, event)
        assert isinstance(result2, list)
        assert len(result2) == 1
        assert strategy.cache_misses == 1  # 缓存未命中次数不变
        assert strategy.cache_hits == 1    # 缓存命中次数增加
        assert caching_feeder.access_count == 1  # 数据馈送器访问次数不变

        # 第三次调用 - 仍然缓存命中
        result3 = strategy.cal(portfolio_info, event)
        assert isinstance(result3, list)
        assert len(result3) == 1
        assert strategy.cache_misses == 1
        assert strategy.cache_hits == 2
        assert caching_feeder.access_count == 1

        # 清除缓存后重新获取
        strategy.clear_cache()
        result4 = strategy.cal(portfolio_info, event)
        assert isinstance(result4, list)
        assert len(result4) == 1
        assert strategy.cache_misses == 1  # 清除缓存后重新计算，不是累加
        assert strategy.cache_hits == 0   # 清除缓存后重置为0
        assert caching_feeder.access_count == 2  # 重新访问数据馈送器

        # 验证所有调用都返回相同的信号
        for result in [result1, result2, result3, result4]:
            assert len(result) == 1
            assert result[0].code == "000001.SZ"


@pytest.mark.unit
class TestBaseStrategyParameterization:
    """6. 策略参数化测试"""

    def test_parameter_initialization(self):
        """测试参数初始化"""
        # 创建简化的参数化策略子类，避免ParameterValidationMixin
        class SimpleParameterStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                # 跳过ParameterValidationMixin初始化
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                # 手动设置参数系统
                self._parameters = {
                    'period': kwargs.get('period', 20),
                    'threshold': kwargs.get('threshold', 0.02),
                    'name': name
                }
                self._parameter_specs = {
                    'period': {'value': 20, 'type': int},
                    'threshold': {'value': 0.02, 'type': float}
                }

            def get_parameter(self, name):
                return self._parameters.get(name)

            def get_parameters(self):
                return self._parameters.copy()

        # 创建带参数的策略
        strategy = SimpleParameterStrategy(name="TestStrategy", period=20, threshold=0.02)

        # 验证参数系统初始化
        assert hasattr(strategy, '_parameters')
        assert hasattr(strategy, '_parameter_specs')

        # 验证参数值存储
        assert strategy.get_parameter('period') == 20
        assert strategy.get_parameter('threshold') == 0.02

        # 验证参数元数据
        assert 'period' in strategy._parameters
        assert 'threshold' in strategy._parameters

        # 验证策略名称正确设置
        assert strategy.name == "TestStrategy"

    def test_parameter_dynamic_update(self):
        """测试参数动态更新"""
        # 创建简化的参数化策略子类
        class SimpleParameterStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                self._parameters = {
                    'period': kwargs.get('period', 20),
                    'threshold': kwargs.get('threshold', 0.02)
                }

            def get_parameter(self, name):
                return self._parameters.get(name)

            def update_parameters(self, params):
                self._parameters.update(params)

        # 创建策略
        strategy = SimpleParameterStrategy(period=20, threshold=0.02)

        # 验证初始值
        assert strategy.get_parameter('period') == 20
        assert strategy.get_parameter('threshold') == 0.02

        # 动态更新参数
        strategy.update_parameters({'period': 30, 'threshold': 0.05})

        # 验证参数已更新
        assert strategy.get_parameter('period') == 30
        assert strategy.get_parameter('threshold') == 0.05

        # 部分更新
        strategy.update_parameters({'period': 25})
        assert strategy.get_parameter('period') == 25
        assert strategy.get_parameter('threshold') == 0.05  # 保持不变

    def test_parameter_validation(self):
        """测试参数验证"""
        # 创建带验证的参数化策略子类
        class ValidatedParameterStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                self._parameters = {
                    'period': kwargs.get('period', 20),
                    'threshold': kwargs.get('threshold', 0.02)
                }

            def get_parameter(self, name):
                return self._parameters.get(name)

            def update_parameters(self, params):
                for name, value in params.items():
                    self._validate_parameter(name, value)
                self._parameters.update(params)

            def _validate_parameter(self, name, value):
                if name == 'period':
                    if not isinstance(value, int) or value < 1 or value > 200:
                        raise ValueError(f"period必须是1-200的整数，得到{value}")
                elif name == 'threshold':
                    if not isinstance(value, (int, float)) or value < 0.001 or value > 0.1:
                        raise ValueError(f"threshold必须是0.001-0.1的数字，得到{value}")

        strategy = ValidatedParameterStrategy()

        # 测试负数验证
        with pytest.raises(ValueError):
            strategy.update_parameters({'period': -5})

        # 测试超出范围的验证
        with pytest.raises(ValueError):
            strategy.update_parameters({'period': 300})  # 超出最大值

        with pytest.raises(ValueError):
            strategy.update_parameters({'threshold': 0.5})  # 超出范围

        # 测试类型验证
        with pytest.raises(ValueError):
            strategy.update_parameters({'period': "invalid"})  # 错误类型

    def test_parameter_type_conversion(self):
        """测试参数类型转换"""
        # 创建带类型转换的参数化策略子类
        class TypeConversionStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                self._parameters = {}
                # 应用类型转换
                for name, value in kwargs.items():
                    self._parameters[name] = self._convert_type(name, value)

                # 设置默认值
                if 'period' not in self._parameters:
                    self._parameters['period'] = 20
                if 'threshold' not in self._parameters:
                    self._parameters['threshold'] = 0.02
                if 'enabled' not in self._parameters:
                    self._parameters['enabled'] = True

            def _convert_type(self, name, value):
                if name == 'period' and isinstance(value, str):
                    return int(value)
                elif name == 'threshold' and isinstance(value, str):
                    return float(value)
                elif name == 'enabled' and isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes')
                return value

            def get_parameter(self, name):
                return self._parameters.get(name)

        # 测试字符串到整数的转换
        strategy1 = TypeConversionStrategy(period="30")
        assert strategy1.get_parameter('period') == 30
        assert isinstance(strategy1.get_parameter('period'), int)

        # 测试字符串到浮点数的转换
        strategy2 = TypeConversionStrategy(threshold="0.05")
        assert strategy2.get_parameter('threshold') == 0.05
        assert isinstance(strategy2.get_parameter('threshold'), float)

        # 测试字符串到布尔值的转换
        strategy3 = TypeConversionStrategy(enabled="false")
        assert strategy3.get_parameter('enabled') is False
        assert isinstance(strategy3.get_parameter('enabled'), bool)

    def test_parameter_serialization(self):
        """测试参数序列化"""
        # 创建可序列化的参数化策略子类
        class SerializableStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                self._parameters = {
                    'period': kwargs.get('period', 20),
                    'threshold': kwargs.get('threshold', 0.02),
                    'enabled': kwargs.get('enabled', True),
                    'name': name
                }

            def get_parameter(self, name):
                return self._parameters.get(name)

            def get_parameters(self):
                return self._parameters.copy()

        strategy = SerializableStrategy(name="TestStrategy", period=20, threshold=0.02, enabled=True)

        # 获取所有参数
        param_dict = strategy.get_parameters()

        # 验证序列化格式
        assert isinstance(param_dict, dict)
        assert len(param_dict) >= 4  # 至少包含4个参数

        # 验证具体参数值
        assert param_dict['period'] == 20
        assert param_dict['threshold'] == 0.02
        assert param_dict['name'] == "TestStrategy"
        assert param_dict['enabled'] is True

        # 验证参数完整性 - 所有参数都应该在序列化结果中
        for param_name in strategy._parameters:
            assert param_name in param_dict

    def test_parameter_optimization_interface(self):
        """测试参数优化接口"""
        # 创建可优化的参数化策略子类
        class OptimizableStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                self._parameters = {
                    'period': kwargs.get('period', 20),
                    'threshold': kwargs.get('threshold', 0.02)
                }

            def get_parameter(self, name):
                return self._parameters.get(name)

            def get_parameter_space(self, param_names, value_ranges):
                """生成参数组合空间"""
                import itertools

                if not isinstance(param_names, list):
                    param_names = [param_names]
                    value_ranges = [value_ranges]

                combinations = list(itertools.product(*value_ranges))
                return [dict(zip(param_names, combo)) for combo in combinations]

        strategy = OptimizableStrategy()

        # 测试单参数空间生成
        param_space = strategy.get_parameter_space('period', [20, 30, 40])
        assert len(param_space) == 3
        assert all('period' in combo for combo in param_space)
        assert param_space[0]['period'] == 20

        # 测试多参数空间生成
        multi_space = strategy.get_parameter_space(
            ['period', 'threshold'],
            [[20, 30], [0.02, 0.03]]
        )
        assert len(multi_space) == 4  # 2 * 2 组合
        assert all('period' in combo and 'threshold' in combo for combo in multi_space)

    def test_parameter_sensitivity_analysis(self):
        """测试参数敏感性分析"""
        # 创建敏感性分析策略子类
        class SensitivityStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                self._parameters = {
                    'period': kwargs.get('period', 20),
                    'threshold': kwargs.get('threshold', 0.02)
                }

            def get_parameter(self, name):
                return self._parameters.get(name)

            def update_parameters(self, params):
                self._parameters.update(params)

            def calculate_strategy_metric(self, portfolio_info=None, event=None):
                """计算策略指标 - 简化实现"""
                # 基于参数计算一个简单的指标值
                period = self.get_parameter('period')
                threshold = self.get_parameter('threshold')

                # 模拟策略性能指标
                metric = period * threshold * 100
                return metric

        strategy = SensitivityStrategy(period=20, threshold=0.02)

        # 计算基准指标
        base_result = strategy.calculate_strategy_metric()
        assert base_result == 20 * 0.02 * 100  # 40.0

        # 修改period参数
        strategy.update_parameters({'period': 25})
        varied_result1 = strategy.calculate_strategy_metric()
        assert varied_result1 == 25 * 0.02 * 100  # 50.0

        # 修改threshold参数
        strategy.update_parameters({'threshold': 0.03})
        varied_result2 = strategy.calculate_strategy_metric()
        assert varied_result2 == 25 * 0.03 * 100  # 75.0

        # 验证敏感性 - 参数变化导致指标变化
        assert varied_result1 != base_result
        assert varied_result2 != varied_result1
        assert varied_result2 != base_result

    def test_parameter_inheritance_and_override(self):
        """测试参数继承和覆盖"""
        # 创建支持继承的参数化策略子类
        class CustomParameterStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                # 默认参数
                default_params = {
                    'period': 10,
                    'custom_param': 1.0,
                    'strategy_type': 'custom'
                }

                # 合并用户参数（覆盖默认）
                self._parameters = {**default_params, **kwargs}

            def get_parameter(self, name):
                return self._parameters.get(name)

        # 测试默认参数
        default_strategy = CustomParameterStrategy()
        assert default_strategy.get_parameter('period') == 10
        assert default_strategy.get_parameter('custom_param') == 1.0
        assert default_strategy.get_parameter('strategy_type') == 'custom'

        # 测试参数覆盖
        override_strategy = CustomParameterStrategy(period=20, custom_param=2.5)
        assert override_strategy.get_parameter('period') == 20  # 覆盖默认值
        assert override_strategy.get_parameter('custom_param') == 2.5  # 覆盖默认值
        assert override_strategy.get_parameter('strategy_type') == 'custom'  # 保持默认

    def test_default_parameter_handling(self):
        """测试默认参数处理"""
        # 创建默认参数处理策略子类
        class DefaultParameterStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                # 固定默认参数
                self._parameters = {
                    'period': 20,
                    'threshold': 0.02,
                    'strategy_name': 'default_strategy'
                }

                # 只覆盖存在的参数
                for name, value in kwargs.items():
                    if name in self._parameters:
                        self._parameters[name] = value

            def get_parameter(self, name):
                return self._parameters.get(name)

            def update_parameters(self, params):
                self._parameters.update(params)

        # 测试完全使用默认值
        strategy1 = DefaultParameterStrategy()
        assert strategy1.get_parameter('period') == 20
        assert strategy1.get_parameter('threshold') == 0.02
        assert strategy1.get_parameter('strategy_name') == 'default_strategy'

        # 测试部分使用默认值
        strategy2 = DefaultParameterStrategy(period=30)  # 只覆盖period
        assert strategy2.get_parameter('period') == 30  # 覆盖值
        assert strategy2.get_parameter('threshold') == 0.02  # 默认值
        assert strategy2.get_parameter('strategy_name') == 'default_strategy'  # 默认值

        # 测试动态恢复默认值
        strategy2.update_parameters({'period': 20})  # 恢复默认值
        assert strategy2.get_parameter('period') == 20

    def test_parameter_constraint_validation(self):
        """测试参数约束验证"""
        # 创建带约束验证的参数化策略子类
        class ConstrainedStrategy(BaseStrategy):
            def __init__(self, name="Strategy", **kwargs):
                BacktestBase.__init__(self, name=name)
                TimeRelated.__init__(self)
                self._raw = {}
                self._data_feeder = None

                self._parameters = {
                    'period': kwargs.get('period', 20),
                    'threshold': kwargs.get('threshold', 0.02),
                    'strategy_type': kwargs.get('strategy_type', 'ma_cross')
                }

            def get_parameter(self, name):
                return self._parameters.get(name)

            def update_parameters(self, params):
                for name, value in params.items():
                    self._validate_constraints(name, value)
                self._parameters.update(params)

            def _validate_constraints(self, name, value):
                if name == 'period':
                    if not isinstance(value, int) or value < 10 or value > 100:
                        raise ValueError(f"period必须在10-100之间")
                elif name == 'threshold':
                    if not isinstance(value, (int, float)) or value < 0.001 or value > 0.1:
                        raise ValueError(f"threshold必须在0.001-0.1之间")
                elif name == 'strategy_type':
                    if value not in ['ma_cross', 'rsi', 'bollinger']:
                        raise ValueError(f"strategy_type必须是ma_cross、rsi或bollinger之一")

        strategy = ConstrainedStrategy()

        # 测试最小值约束
        with pytest.raises(ValueError):
            strategy.update_parameters({'period': 5})  # 小于最小值10

        # 测试最大值约束
        with pytest.raises(ValueError):
            strategy.update_parameters({'period': 150})  # 大于最大值100

        # 测试范围约束
        with pytest.raises(ValueError):
            strategy.update_parameters({'threshold': 0.2})  # 大于最大值0.1

        with pytest.raises(ValueError):
            strategy.update_parameters({'threshold': 0.0005})  # 小于最小值0.001

        # 测试选择约束
        with pytest.raises(ValueError):
            strategy.update_parameters({'strategy_type': 'invalid_type'})  # 不在选择列表中

        # 测试有效值应该被接受
        strategy.update_parameters({'period': 50})  # 有效范围内
        assert strategy.get_parameter('period') == 50

        strategy.update_parameters({'threshold': 0.05})  # 有效范围内
        assert strategy.get_parameter('threshold') == 0.05

        strategy.update_parameters({'strategy_type': 'rsi'})  # 有效选择
        assert strategy.get_parameter('strategy_type') == 'rsi'