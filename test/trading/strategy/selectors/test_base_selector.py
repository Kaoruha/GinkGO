"""
BaseSelector选择器TDD测试

通过TDD方式开发BaseSelector的核心逻辑测试套件
聚焦于基类设计和扩展性验证
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 导入BaseSelector相关组件
from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.trading.feeders.base_feeder import BaseFeeder
from datetime import datetime


@pytest.mark.unit
class TestBaseSelectorConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        selector = BaseSelector()

        # 验证name默认为"BaseSelector"
        assert selector.name == "BaseSelector"

        # 验证_data_feeder初始化为None
        assert selector._data_feeder is None

        # 验证继承自BacktestBase的属性
        assert hasattr(selector, 'engine_id')
        assert hasattr(selector, 'portfolio_id')
        assert hasattr(selector, 'run_id')

    def test_custom_name_constructor(self):
        """测试自定义名称构造"""
        custom_name = "CustomSelector"
        selector = BaseSelector(name=custom_name)

        # 验证name被正确设置
        assert selector.name == custom_name

    def test_backtest_base_inheritance(self):
        """测试BacktestBase继承"""
        selector = BaseSelector()

        # 验证正确继承BacktestBase的方法
        assert hasattr(selector, 'set_backtest_ids')
        assert hasattr(selector, 'get_id_dict')
        assert hasattr(selector, 'bind_engine')
        assert hasattr(selector, 'set_name')
        assert hasattr(selector, 'log')

        # 验证ID管理属性
        assert selector.engine_id == ""
        assert selector.portfolio_id == ""
        assert selector.run_id == ""

        # 验证日志功能
        assert hasattr(selector, 'loggers')
        assert len(selector.loggers) > 0  # 默认添加了GLOG


@pytest.mark.unit
class TestDataFeederBinding:
    """2. 数据馈送器绑定测试"""

    def test_bind_data_feeder_method(self):
        """测试绑定数据馈送器"""
        # 创建一个简单的数据馈送器对象进行测试
        class SimpleDataFeeder:
            def __init__(self):
                self.name = "TestFeeder"

        data_feeder = SimpleDataFeeder()
        selector = BaseSelector()

        # 绑定数据馈送器
        selector.bind_data_feeder(data_feeder)

        # 验证_data_feeder被正确设置
        assert selector._data_feeder is data_feeder
        assert selector._data_feeder.name == "TestFeeder"

    def test_data_feeder_access_after_binding(self):
        """测试绑定后数据馈送器访问"""
        # 创建BaseFeeder实例
        data_feeder = BaseFeeder(name="TestFeeder", bar_service=None)
        selector = BaseSelector()

        # 绑定数据馈送器
        selector.bind_data_feeder(data_feeder)

        # 验证_data_feeder不为None
        assert selector._data_feeder is not None

        # 验证通过selector的_data_feeder可以调用数据获取方法
        # 这里测试调用接口的存在性和基本调用能力
        test_date = datetime(2023, 1, 1)
        test_code = "000001.SZ"

        # 验证方法可以被调用（不测试具体返回数据，因为那需要真实数据库）
        assert callable(selector._data_feeder.get_daybar)
        assert callable(selector._data_feeder.is_code_on_market)

    def test_data_feeder_none_before_binding(self):
        """测试绑定前数据馈送器为None"""
        selector = BaseSelector()

        # 验证初始化后_data_feeder为None
        assert selector._data_feeder is None


@pytest.mark.unit
class TestPickMethod:
    """3. pick()方法基础行为测试"""

    def test_pick_returns_list(self):
        """测试pick返回列表类型"""
        selector = BaseSelector()

        # 调用pick方法
        result = selector.pick()

        # 验证返回类型为list
        assert isinstance(result, list)

        # 验证默认返回空列表
        assert result == []

    def test_pick_accepts_time_parameter(self):
        """测试pick接受时间参数"""
        selector = BaseSelector()

        # 测试不同的时间参数类型
        test_time1 = datetime(2023, 1, 1)
        test_time2 = "2023-01-01"
        test_time3 = None

        # 验证time参数被接受不报错
        result1 = selector.pick(time=test_time1)
        result2 = selector.pick(time=test_time2)
        result3 = selector.pick(time=test_time3)

        # 验证基类行为不变（仍然返回空列表）
        assert result1 == []
        assert result2 == []
        assert result3 == []

    def test_pick_supports_kwargs_extensibility(self):
        """测试pick支持kwargs扩展"""
        selector = BaseSelector()

        # 测试各种自定义参数
        result1 = selector.pick(time=datetime(2023, 1, 1), market="SZ", limit=10)
        result2 = selector.pick(custom_param="test", filter_type="active", min_price=10.0)
        result3 = selector.pick(**{"sector": "technology", "market_cap": "large"})

        # 验证所有参数都被接受，基类行为不变
        assert result1 == []
        assert result2 == []
        assert result3 == []


@pytest.mark.unit
class TestSelectorExtensibility:
    """4. 选择器扩展性测试"""

    def test_subclass_can_override_pick(self):
        """测试子类可以重写pick方法"""
        # 创建自定义Selector子类
        class CustomSelector(BaseSelector):
            def __init__(self, name="CustomSelector"):
                super().__init__(name=name)
                self.call_count = 0  # 记录调用次数

            def pick(self, time=None, *args, **kwargs):
                self.call_count += 1
                # 返回固定的股票列表
                return ["000001.SZ", "000002.SZ"]

        # 测试子类
        custom_selector = CustomSelector()

        # 验证子类pick()被正确调用
        result = custom_selector.pick()

        # 验证返回自定义的股票列表
        assert result == ["000001.SZ", "000002.SZ"]
        assert custom_selector.call_count == 1

        # 验证可以多次调用
        result2 = custom_selector.pick()
        assert result2 == ["000001.SZ", "000002.SZ"]
        assert custom_selector.call_count == 2

    def test_subclass_inherits_backtest_capabilities(self):
        """测试子类继承回测能力"""
        # 创建自定义Selector子类
        class TestSelector(BaseSelector):
            def __init__(self):
                super().__init__(name="TestSelector")

        test_selector = TestSelector()

        # 验证子类有set_backtest_ids()方法
        assert hasattr(test_selector, 'set_backtest_ids')
        assert callable(test_selector.set_backtest_ids)

        # 验证子类可以接收engine_id/portfolio_id/run_id注入
        test_ids = test_selector.set_backtest_ids(
            engine_id="test_engine_001",
            portfolio_id="test_portfolio_001",
            run_id="test_run_001"
        )

        # 验证ID正确设置
        assert test_selector.engine_id == "test_engine_001"
        assert test_selector.portfolio_id == "test_portfolio_001"
        assert test_selector.run_id == "test_run_001"

        # 验证返回的ID字典
        expected_ids = {
            'engine_id': "test_engine_001",
            'portfolio_id': "test_portfolio_001",
            'run_id': "test_run_001"
        }
        assert test_ids == expected_ids

        # 验证子类有日志能力(self.log)
        assert hasattr(test_selector, 'log')
        assert callable(test_selector.log)
        assert hasattr(test_selector, 'loggers')

    def test_selector_polymorphism(self):
        """测试选择器多态性"""
        # 创建多个自定义Selector子类
        class BankSelector(BaseSelector):
            def pick(self, time=None, *args, **kwargs):
                return ["000001.SZ", "000002.SZ"]  # 银行股

        class TechSelector(BaseSelector):
            def pick(self, time=None, *args, **kwargs):
                return ["000001.SZ", "300750.SZ"]  # 科技股

        # 验证都符合BaseSelector接口
        bank_selector = BankSelector(name="BankSelector")
        tech_selector = TechSelector(name="TechSelector")
        base_selector = BaseSelector(name="BaseSelector")

        # 验证都可以作为BaseSelector类型使用（里氏替换原则）
        selectors = [bank_selector, tech_selector, base_selector]

        # 统一处理不同的Selector实现
        results = []
        for selector in selectors:
            # 验证每个selector都有pick方法
            assert hasattr(selector, 'pick')
            assert callable(selector.pick)

            # 验证可以统一调用
            result = selector.pick()
            results.append(result)

        # 验证结果
        assert results[0] == ["000001.SZ", "000002.SZ"]  # BankSelector
        assert results[1] == ["000001.SZ", "300750.SZ"]  # TechSelector
        assert results[2] == []  # BaseSelector

        # 验证多态性：可以统一作为BaseSelector处理
        for selector in selectors:
            assert isinstance(selector, BaseSelector)
            # 验证都可以调用继承的方法
            assert hasattr(selector, 'set_backtest_ids')
            assert hasattr(selector, 'bind_data_feeder')
