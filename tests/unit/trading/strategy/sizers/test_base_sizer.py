"""
BaseSizer仓位管理器TDD测试

通过TDD方式开发BaseSizer的核心逻辑测试套件
聚焦于基类设计、抽象方法和扩展性验证
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

# 导入BaseSizer相关组件
from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.entities.signal import Signal
from ginkgo.entities.order import Order
from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from datetime import datetime


def _set_context(obj, engine_id="test_engine", portfolio_id="test_portfolio", task_id="test_run"):
    """Set mock context so that engine_id/portfolio_id/task_id are available."""
    ctx = MagicMock()
    ctx.engine_id = engine_id
    ctx.portfolio_id = portfolio_id
    ctx.task_id = task_id
    obj._context = ctx


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    return Signal(
        portfolio_id='test_portfolio', engine_id='test_engine', task_id='test_run',
        timestamp=datetime.now(), code=code, direction=direction
    )


@pytest.mark.unit
class TestBaseSizerConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        sizer = BaseSizer()

        # 验证name默认为"sizer" (lowercase, from NamedMixin)
        assert sizer.name == "sizer"

        # 验证_data_feeder初始化为None
        assert sizer._data_feeder is None

        # 验证继承自ContextMixin的属性
        assert getattr(sizer, 'engine_id', None) is None
        assert getattr(sizer, 'portfolio_id', None) is None
        assert getattr(sizer, 'task_id', None) is None

    def test_custom_name_constructor(self):
        """测试自定义名称构造"""
        custom_name = "FixedSizer"
        sizer = BaseSizer(name=custom_name)

        # 验证name被正确设置
        assert sizer.name == custom_name

    def test_backtest_base_inheritance(self):
        """测试ContextMixin继承"""
        sizer = BaseSizer()

        # 验证正确继承ContextMixin的方法
        assert callable(getattr(sizer, 'bind_engine', None))
        assert callable(getattr(sizer, 'set_name', None))

        # 验证ID管理属性 (None when no context)
        assert sizer.engine_id is None
        assert sizer.portfolio_id is None
        assert sizer.task_id is None

        # 验证设置context后ID可用
        _set_context(sizer)
        assert sizer.engine_id == "test_engine"
        assert sizer.portfolio_id == "test_portfolio"
        assert sizer.task_id == "test_run"


@pytest.mark.unit
class TestDataFeederBinding:
    """2. 数据馈送器绑定测试"""

    def test_bind_data_feeder_method(self):
        """测试绑定数据馈送器"""
        # 创建一个简单的数据馈送器对象
        class SimpleDataFeeder:
            def __init__(self):
                self.name = "TestFeeder"

        data_feeder = SimpleDataFeeder()
        sizer = BaseSizer()

        # 绑定数据馈送器
        sizer.bind_data_feeder(data_feeder)

        # 验证_data_feeder被正确设置
        assert sizer._data_feeder is data_feeder
        assert sizer._data_feeder.name == "TestFeeder"

    def test_data_feeder_access_after_binding(self):
        """测试绑定后数据馈送器访问"""
        # 创建BaseFeeder实例
        data_feeder = BaseFeeder(name="TestFeeder", bar_service=None)
        sizer = BaseSizer()

        # 绑定数据馈送器
        sizer.bind_data_feeder(data_feeder)

        # 验证_data_feeder不为None
        assert sizer._data_feeder is not None

        # 验证通过sizer的_data_feeder可以调用数据获取方法
        assert callable(sizer._data_feeder.get_daybar)
        assert callable(sizer._data_feeder.is_code_on_market)
        assert sizer._data_feeder.name == "TestFeeder"

    def test_data_feeder_none_before_binding(self):
        """测试绑定前数据馈送器为None"""
        sizer = BaseSizer()

        # 验证初始化后_data_feeder为None
        assert sizer._data_feeder is None


@pytest.mark.unit
class TestCalMethod:
    """3. cal()方法测试"""

    def test_cal_returns_none_by_default(self):
        """测试cal()返回None (base implementation)"""
        sizer = BaseSizer()
        signal = _make_signal()

        # BaseSizer.cal() returns None by default
        result = sizer.cal({}, signal)
        assert result is None

    def test_cal_accepts_portfolio_info_parameter(self):
        """测试cal接受portfolio_info参数"""
        sizer = BaseSizer()
        signal = _make_signal()

        # 测试不同格式的portfolio_info
        portfolio_infos = [
            {},  # 空字典
            {'uuid': 'test_portfolio'},  # 简单字典
            {'cash': 100000, 'positions': {}},  # 包含现金和持仓信息
            {'uuid': 'test', 'cash': 50000, 'now': datetime.now()}  # 完整信息
        ]

        # 验证所有格式的portfolio_info都被接受
        for portfolio_info in portfolio_infos:
            result = sizer.cal(portfolio_info, signal)
            assert result is None

    def test_cal_accepts_signal_parameter(self):
        """测试cal接受signal参数"""
        sizer = BaseSizer()
        portfolio_info = {'uuid': 'test_portfolio'}

        # 测试不同类型的Signal对象
        signals = [
            _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG),
            _make_signal(code="000002.SZ", direction=DIRECTION_TYPES.SHORT),
            _make_signal(code="600000.SH", direction=DIRECTION_TYPES.LONG),
        ]

        # 验证所有Signal对象都被接受
        for signal in signals:
            result = sizer.cal(portfolio_info, signal)
            assert result is None

    def test_cal_return_type_optional_order(self):
        """测试cal返回类型为Optional[Order]"""
        sizer = BaseSizer()

        # 验证cal方法存在且可调用
        assert callable(getattr(sizer, 'cal', None))

        # 创建一个子类来演示返回类型规范
        class TestSizer(BaseSizer):
            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                # 可以返回Order对象
                return Order(portfolio_id=signal.portfolio_id,
                           engine_id=signal.engine_id,
                           task_id=signal.task_id,
                           code=signal.code,
                           direction=signal.direction,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=100,
                           limit_price=10.0)

        # 验证子类可以返回Order对象
        test_sizer = TestSizer()
        portfolio_info = {'uuid': 'test'}
        signal = _make_signal()

        result = test_sizer.cal(portfolio_info, signal)
        assert isinstance(result, Order)

        # 创建另一个子类演示返回None的情况
        class NoTradeSizer(BaseSizer):
            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                # 可以返回None（不交易）
                return None

        no_trade_sizer = NoTradeSizer()
        result2 = no_trade_sizer.cal(portfolio_info, signal)
        assert result2 is None


@pytest.mark.unit
class TestSizerExtensibility:
    """4. 仓位管理器扩展性测试"""

    def test_subclass_can_override_cal(self):
        """测试子类可以重写cal方法"""
        # 创建自定义Sizer子类
        class CustomSizer(BaseSizer):
            def __init__(self, fixed_volume=100):
                super().__init__(name="CustomSizer")
                self.fixed_volume = fixed_volume
                self.call_count = 0

            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                self.call_count += 1
                # 自定义仓位计算逻辑：固定数量
                return Order(portfolio_id=signal.portfolio_id,
                           engine_id=signal.engine_id,
                           task_id=signal.task_id,
                           code=signal.code,
                           direction=signal.direction,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=self.fixed_volume,
                           limit_price=10.0)

        # 测试子类
        custom_sizer = CustomSizer(fixed_volume=200)
        portfolio_info = {'uuid': 'test', 'cash': 10000}
        signal = _make_signal()

        # 验证子类cal()被正确调用
        result = custom_sizer.cal(portfolio_info, signal)

        # 验证自定义仓位计算逻辑
        assert isinstance(result, Order)
        assert result.code == "000001.SZ"
        assert result.direction == DIRECTION_TYPES.LONG
        assert result.volume == 200
        assert custom_sizer.call_count == 1

        # 验证可以多次调用
        result2 = custom_sizer.cal(portfolio_info, signal)
        assert result2.volume == 200
        assert custom_sizer.call_count == 2

    def test_subclass_implements_fixed_volume_logic(self):
        """测试子类实现固定仓位逻辑"""
        # 创建FixedSizer风格的子类
        class FixedSizer(BaseSizer):
            def __init__(self, volume=100):
                super().__init__(name="FixedSizer")
                self.volume = volume

            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                # 卖出信号不受现金限制
                if signal.direction == DIRECTION_TYPES.SHORT:
                    return Order(portfolio_id=signal.portfolio_id,
                               engine_id=signal.engine_id,
                               task_id=signal.task_id,
                               code=signal.code,
                               direction=signal.direction,
                               order_type=ORDER_TYPES.LIMITORDER,
                               status=ORDERSTATUS_TYPES.NEW,
                               volume=self.volume,
                               limit_price=10.0)

                # 买入信号需要现金检查
                cash = portfolio_info.get('cash', 0)
                if cash <= 0:
                    return None  # 没有现金时不交易

                # 返回固定数量的Order
                return Order(portfolio_id=signal.portfolio_id,
                           engine_id=signal.engine_id,
                           task_id=signal.task_id,
                           code=signal.code,
                           direction=signal.direction,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=self.volume,
                           limit_price=10.0)

        # 测试固定仓位逻辑
        fixed_sizer = FixedSizer(volume=500)
        portfolio_info = {'cash': 10000, 'uuid': 'test_portfolio'}
        signal = _make_signal()

        result = fixed_sizer.cal(portfolio_info, signal)

        # 验证返回固定volume的Order
        assert isinstance(result, Order)
        assert result.code == "000001.SZ"
        assert result.direction == DIRECTION_TYPES.LONG
        assert result.volume == 500

        # 测试没有现金的情况
        portfolio_info_no_cash = {'cash': 0, 'uuid': 'test_portfolio'}
        result_no_cash = fixed_sizer.cal(portfolio_info_no_cash, signal)
        assert result_no_cash is None

        # 测试卖出信号（不受现金限制）
        sell_signal = _make_signal(code="000002.SZ", direction=DIRECTION_TYPES.SHORT)
        portfolio_info_empty = {'uuid': 'test_portfolio'}
        result_sell = fixed_sizer.cal(portfolio_info_empty, sell_signal)
        assert isinstance(result_sell, Order)
        assert result_sell.direction == DIRECTION_TYPES.SHORT
        assert result_sell.volume == 500

    def test_subclass_inherits_backtest_capabilities(self):
        """测试子类继承ContextMixin能力"""
        # 创建自定义Sizer子类
        class TestSizer(BaseSizer):
            def __init__(self):
                super().__init__(name="TestSizer")

            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                return None  # 简单实现，重点测试继承功能

        test_sizer = TestSizer()

        # 验证子类有context属性
        assert getattr(test_sizer, 'engine_id', None) is None
        assert getattr(test_sizer, 'portfolio_id', None) is None
        assert getattr(test_sizer, 'task_id', None) is None

        # 验证子类可以接收engine_id/portfolio_id/task_id注入 via context
        _set_context(test_sizer,
                     engine_id="test_engine_001",
                     portfolio_id="test_portfolio_001",
                     task_id="test_run_001")

        # 验证ID正确设置
        assert test_sizer.engine_id == "test_engine_001"
        assert test_sizer.portfolio_id == "test_portfolio_001"
        assert test_sizer.task_id == "test_run_001"

    def test_sizer_polymorphism(self):
        """测试仓位管理器多态性"""
        # 创建多个自定义Sizer子类
        class ConservativeSizer(BaseSizer):
            def __init__(self):
                super().__init__(name="ConservativeSizer")

            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                # 保守策略：小仓位
                return Order(portfolio_id=signal.portfolio_id,
                           engine_id=signal.engine_id,
                           task_id=signal.task_id,
                           code=signal.code,
                           direction=signal.direction,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=100,
                           limit_price=10.0)

        class AggressiveSizer(BaseSizer):
            def __init__(self):
                super().__init__(name="AggressiveSizer")

            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                # 激进策略：大仓位
                return Order(portfolio_id=signal.portfolio_id,
                           engine_id=signal.engine_id,
                           task_id=signal.task_id,
                           code=signal.code,
                           direction=signal.direction,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=1000,
                           limit_price=10.0)

        class NoTradeSizer(BaseSizer):
            def __init__(self):
                super().__init__(name="NoTradeSizer")

            def cal(self, portfolio_info, signal: Signal, *args, **kwargs):
                # 不交易策略
                return None

        # 验证都符合BaseSizer接口
        conservative_sizer = ConservativeSizer()
        aggressive_sizer = AggressiveSizer()
        no_trade_sizer = NoTradeSizer()
        base_sizer = BaseSizer()

        # 验证都可以作为BaseSizer类型使用（里氏替换原则）
        sizers = [conservative_sizer, aggressive_sizer, no_trade_sizer]

        # 统一处理不同的Sizer实现
        portfolio_info = {'uuid': 'test_portfolio', 'cash': 10000}
        signal = _make_signal()

        results = []
        for sizer in sizers:
            # 验证每个sizer都有cal方法
            assert callable(getattr(sizer, 'cal', None))

            # 验证可以统一调用
            result = sizer.cal(portfolio_info, signal)
            results.append(result)

        # 验证不同实现产生不同结果
        assert isinstance(results[0], Order)  # ConservativeSizer
        assert results[0].volume == 100

        assert isinstance(results[1], Order)  # AggressiveSizer
        assert results[1].volume == 1000

        assert results[2] is None  # NoTradeSizer

        # 验证多态性：可以统一作为BaseSizer处理
        for sizer in sizers:
            assert isinstance(sizer, BaseSizer)
            # 验证都可以调用继承的方法
            assert callable(getattr(sizer, 'bind_data_feeder', None))
            assert isinstance(sizer.name, str)

        # 验证BaseSizer本身也符合接口（返回None）
        result = base_sizer.cal(portfolio_info, signal)
        assert result is None
