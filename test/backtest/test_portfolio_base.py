import unittest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from ginkgo.libs import GLOG
from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.backtest.entities.order import Order
from ginkgo.backtest.strategy.strategies import StrategyBase
from ginkgo.libs.data.math import cal_fee
from ginkgo.enums import DIRECTION_TYPES, FREQUENCY_TYPES, RECORDSTAGE_TYPES
from ginkgo.backtest.execution.engines import BaseEngine, EventEngine
from ginkgo.backtest.execution.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.execution.portfolios import PortfolioT1Backtest
from ginkgo.backtest.entities.position import Position
from ginkgo.backtest.execution.events import EventPriceUpdate, EventSignalGeneration
from ginkgo.backtest.entities.signal import Signal
from ginkgo.libs.data.math import cal_fee
from ginkgo.backtest.selectors import FixedSelector
from ginkgo.backtest.analyzers import BaseAnalyzer
from ginkgo.backtest.entities.bar import Bar
from ginkgo.backtest.sizers import BaseSizer, FixedSizer
from ginkgo.backtest.risk_managements import BaseRiskManagement
from ginkgo.backtest.feeders.base_feeder import BaseFeeder


class PortfolioBaseTest(unittest.TestCase):
    """
    UnitTest for Signal.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(PortfolioBaseTest, self).__init__(*args, **kwargs)
        self.params = [
            {},
        ]

    def test_portfolio_init(self) -> None:
        # BasePortfolio是抽象类，使用具体实现测试
        p = PortfolioT1Backtest()

    def test_portfolio_addstrategy(self) -> None:
        p = PortfolioT1Backtest()
        s = StrategyBase()
        p.add_strategy(s)
        self.assertEqual(1, len(p.strategies))
        s2 = StrategyBase()
        p.add_strategy(s2)
        self.assertEqual(2, len(p.strategies))

    def test_portfolio_addposition(self) -> None:
        # 由于BasePortfolio是抽象类，使用具体实现进行测试
        p = PortfolioT1Backtest()
        pos1 = Position(
            portfolio_id=p.uuid,
            engine_id=p.engine_id,
            code="test_code",
            cost=10,
            volume=1000,
            frozen_volume=0,
            frozen_money=0,
            price=10,
            fee=0,
        )
        p.add_position(pos1)
        r = p.positions["test_code"]
        self.assertEqual("test_code", r.code)
        self.assertEqual(10, r.price)
        self.assertEqual(10, r.cost)
        self.assertEqual(1000, r.volume)
        pos2 = Position(
            portfolio_id=p.uuid,
            engine_id=p.engine_id,
            code="test_code2",
            cost=10,
            volume=1000,
            frozen_volume=0,
            frozen_money=0,
            price=10,
            fee=0,
        )
        p.add_position(pos2)
        self.assertEqual(2, len(p.positions))
    
    # =========================
    # 新增：ABC合约强制实现测试
    # =========================
    
    def test_abstract_base_class_contract(self):
        """测试BasePortfolio的抽象基类合约"""
        # BasePortfolio是抽象类，不能直接实例化
        with self.assertRaises(TypeError):
            BasePortfolio()
    
    def test_abstract_methods_must_be_implemented(self):
        """测试抽象方法必须被子类实现"""
        
        # 创建不完整实现的子类
        class IncompletePortfolio(BasePortfolio):
            # 故意不实现某些必需方法
            def get_position(self, code: str):
                return None
            # 缺少其他抽象方法的实现
        
        # 尝试实例化应该失败
        with self.assertRaises(TypeError):
            IncompletePortfolio()
    
    def test_concrete_implementation_works(self):
        """测试完整实现的具体类可以正常工作"""
        # PortfolioT1Backtest是完整实现
        portfolio = PortfolioT1Backtest()
        self.assertIsNotNone(portfolio)
        self.assertIsInstance(portfolio, BasePortfolio)
    
    def test_not_implemented_methods_raise_errors(self):
        """测试未实现方法抛出NotImplemented错误"""
        
        # 创建最小实现来测试特定方法
        class MinimalPortfolio(BasePortfolio):
            def get_position(self, code: str):
                raise NotImplemented("Test method")
            
            def on_price_recived(self, price):
                raise NotImplemented("Test method")
            
            def on_signal(self, code: str):
                raise NotImplemented("Test method")
            
            def on_order_filled(self, order):
                raise NotImplemented("Test method")
            
            def on_order_canceled(self, order):
                raise NotImplemented("Test method")
        
        portfolio = MinimalPortfolio()
        
        # 测试各个方法都抛出NotImplemented错误
        with self.assertRaises(Exception):  # NotImplemented应该是Exception子类
            portfolio.get_position("TEST")
        
        with self.assertRaises(Exception):
            portfolio.on_price_recived(Mock())
        
        with self.assertRaises(Exception):
            portfolio.on_signal("TEST")
        
        with self.assertRaises(Exception):
            portfolio.on_order_filled(Mock())
        
        with self.assertRaises(Exception):
            portfolio.on_order_canceled(Mock())
    
    # =========================
    # 新增：分析器Hook机制测试
    # =========================
    
    def test_analyzer_registration_and_hook_creation(self):
        """测试分析器注册和Hook创建"""
        portfolio = PortfolioT1Backtest()
        
        # 创建测试分析器
        class TestAnalyzer(BaseAnalyzer):
            def __init__(self, name):
                super().__init__(name)
                self.activation_calls = []
                self.record_calls = []
                # 配置激活和记录阶段
                self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
                self.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
                self.set_record_stage(RECORDSTAGE_TYPES.ORDERFILLED)
            
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                self.activation_calls.append((stage, portfolio_info.copy()))
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                self.record_calls.append((stage, portfolio_info.copy()))
        
        analyzer = TestAnalyzer("test_analyzer")
        
        # 注册分析器
        portfolio.add_analyzer(analyzer)
        
        # 验证分析器已注册
        self.assertIn("test_analyzer", portfolio.analyzers)
        self.assertEqual(portfolio.analyzers["test_analyzer"], analyzer)
        
        # 验证分析器属性已设置
        self.assertEqual(analyzer.portfolio_id, portfolio.portfolio_id)
        self.assertEqual(analyzer.engine_id, portfolio.engine_id)
        
        # 验证Hook已创建
        self.assertGreater(len(portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.NEWDAY]), 0)
        self.assertGreater(len(portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.SIGNALGENERATION]), 0)
        self.assertGreater(len(portfolio._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERFILLED]), 0)
    
    def test_hook_lambda_closure_fix(self):
        """测试Hook机制的Lambda闭包修复"""
        portfolio = PortfolioT1Backtest()
        
        # 创建多个测试分析器
        analyzers = []
        for i in range(3):
            class TestAnalyzer(BaseAnalyzer):
                def __init__(self, name, test_id):
                    super().__init__(name)
                    self.test_id = test_id
                    self.activation_calls = []
                    self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
                    self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
                
                def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                    self.activation_calls.append(self.test_id)
                
                def _do_record(self, stage, portfolio_info, *args, **kwargs):
                    pass
            
            analyzer = TestAnalyzer(f"analyzer_{i}", i)
            analyzers.append(analyzer)
            portfolio.add_analyzer(analyzer)
        
        # 模拟执行Hook
        portfolio_info = {"worth": 10000, "cash": 5000}
        
        # 执行所有NEWDAY阶段的activate hooks
        for hook_func in portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.NEWDAY]:
            hook_func(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 验证每个分析器都被正确调用（闭包变量正确捕获）
        for i, analyzer in enumerate(analyzers):
            self.assertEqual(len(analyzer.activation_calls), 1)
            self.assertEqual(analyzer.activation_calls[0], i)  # 应该是各自的test_id
    
    def test_analyzer_hook_error_handling(self):
        """测试分析器Hook中的错误处理"""
        portfolio = PortfolioT1Backtest()
        
        # 创建会抛出错误的分析器
        class ErrorAnalyzer(BaseAnalyzer):
            def __init__(self, name):
                super().__init__(name)
                self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
                self.error_handled = False
            
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                raise ValueError("Test error in analyzer")
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        error_analyzer = ErrorAnalyzer("error_analyzer")
        
        # Mock错误处理方法
        portfolio._handle_analyzer_error = Mock()
        
        portfolio.add_analyzer(error_analyzer)
        
        portfolio_info = {"worth": 10000}
        
        # 执行Hook应该捕获错误并调用错误处理
        hook_func = portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.NEWDAY][0]
        result = hook_func(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 验证错误被处理
        self.assertFalse(result)  # Hook应该返回False表示执行失败
        portfolio._handle_analyzer_error.assert_called_once()
    
    def test_duplicate_analyzer_registration_prevention(self):
        """测试防止重复注册同名分析器"""
        portfolio = PortfolioT1Backtest()
        
        class TestAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        analyzer1 = TestAnalyzer("duplicate_name")
        analyzer2 = TestAnalyzer("duplicate_name")
        
        # 第一次注册应该成功
        portfolio.add_analyzer(analyzer1)
        self.assertIn("duplicate_name", portfolio.analyzers)
        self.assertEqual(portfolio.analyzers["duplicate_name"], analyzer1)
        
        # 第二次注册同名分析器应该被拒绝
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_analyzer(analyzer2)
            # 应该记录警告日志
            mock_log.assert_called_with("WARN", unittest.mock.ANY)
        
        # 分析器应该仍然是第一个
        self.assertEqual(portfolio.analyzers["duplicate_name"], analyzer1)
    
    def test_analyzer_without_activate_method(self):
        """测试没有activate方法的分析器处理"""
        portfolio = PortfolioT1Backtest()
        
        # 创建没有activate方法的对象
        class InvalidAnalyzer:
            def __init__(self, name):
                self.name = name
        
        invalid_analyzer = InvalidAnalyzer("invalid")
        
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_analyzer(invalid_analyzer)
            # 应该记录警告日志
            mock_log.assert_called_with("WARN", unittest.mock.ANY)
        
        # 分析器不应该被添加
        self.assertNotIn("invalid", portfolio.analyzers)
    
    # =========================
    # 新增：分析器管理和查询测试
    # =========================
    
    def test_analyzer_retrieval(self):
        """测试分析器检索功能"""
        portfolio = PortfolioT1Backtest()
        
        class TestAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        analyzer = TestAnalyzer("retrieval_test")
        portfolio.add_analyzer(analyzer)
        
        # 成功获取存在的分析器
        retrieved = portfolio.analyzer("retrieval_test")
        self.assertEqual(retrieved, analyzer)
        
        # 获取不存在的分析器应该记录错误并返回None
        with patch.object(portfolio, 'log') as mock_log:
            result = portfolio.analyzer("nonexistent")
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)
            self.assertIsNone(result)
    
    def test_analyzer_properties_binding(self):
        """测试分析器属性绑定"""
        portfolio = PortfolioT1Backtest()
        # 设置portfolio的engine_id
        portfolio._engine_id = "test_engine_123"
        
        class TestAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        analyzer = TestAnalyzer("property_binding_test")
        
        # 在添加前，分析器不应该有这些属性
        initial_portfolio_id = getattr(analyzer, 'portfolio_id', None)
        initial_engine_id = getattr(analyzer, 'engine_id', None)
        
        portfolio.add_analyzer(analyzer)
        
        # 添加后，属性应该被正确设置
        self.assertEqual(analyzer.portfolio_id, portfolio.portfolio_id)
        self.assertEqual(analyzer.engine_id, portfolio.engine_id)
    
    # =========================
    # 新增：投资组合基础功能增强测试
    # =========================
    
    def test_portfolio_financial_operations(self):
        """测试投资组合财务操作"""
        portfolio = PortfolioT1Backtest()
        
        # 测试初始状态
        initial_cash = portfolio.cash
        self.assertGreater(initial_cash, 0)
        
        # 测试添加现金
        added_cash = Decimal("5000")
        new_cash = portfolio.add_cash(added_cash)
        self.assertEqual(new_cash, initial_cash + added_cash)
        
        # 测试添加费用
        fee = Decimal("100")
        total_fee = portfolio.add_fee(fee)
        self.assertEqual(total_fee, fee)
        
        # 测试无效操作（负数）
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_cash(-1000)
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)
        
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_fee(-50)
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)
    
    def test_portfolio_configuration_validation(self):
        """测试投资组合配置验证"""
        portfolio = PortfolioT1Backtest()
        
        # 未设置必要组件时应该返回False
        self.assertFalse(portfolio.is_all_set())
        
        # 设置必要组件
        portfolio.bind_sizer(FixedSizer())
        portfolio.bind_selector(FixedSelector())
        portfolio.add_strategy(StrategyBase())
        
        # 现在应该返回True
        self.assertTrue(portfolio.is_all_set())
    
    def test_engine_binding_and_event_handling(self):
        """测试引擎绑定和事件处理"""
        portfolio = PortfolioT1Backtest()
        mock_engine = Mock()
        mock_put_func = Mock()
        
        # 绑定引擎
        portfolio.bind_engine(mock_engine)
        portfolio._engine_put = mock_put_func
        
        # 测试事件发送
        test_event = Mock()
        portfolio.put(test_event)
        mock_put_func.assert_called_once_with(test_event)
        
        # 测试未绑定引擎时的错误处理
        portfolio._engine_put = None
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.put(test_event)
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)
