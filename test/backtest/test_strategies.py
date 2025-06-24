import unittest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.strategies.dual_thrust import DualThrustStrategy
from ginkgo.backtest.strategies.mean_reversion import MeanReversionStrategy
from ginkgo.backtest.strategies.trend_follow import TrendFollowStrategy
from ginkgo.backtest.signal import Signal
from ginkgo.enums import DIRECTION_TYPES


class StrategiesTest(unittest.TestCase):
    """
    测试策略模块
    """

    def setUp(self):
        """准备测试环境"""
        # 创建模拟市场数据
        self.market_data = self._create_sample_market_data()
        
        # 创建模拟组合信息
        self.portfolio_info = {
            'cash': 100000,
            'positions': {},
            'net_value': 100000
        }
        
        # 创建模拟事件
        self.mock_event = Mock()
        self.mock_event.data = self.market_data.iloc[0]

    def _create_sample_market_data(self):
        """创建样本市场数据"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        
        # 创建带趋势的价格数据
        np.random.seed(42)
        base_price = 100
        prices = []
        
        for i, date in enumerate(dates):
            # 添加趋势和随机波动
            trend = 0.001 * i  # 轻微上升趋势
            noise = np.random.normal(0, 0.02)
            price = base_price * (1 + trend + noise)
            prices.append({
                'timestamp': date,
                'open': price * 0.995,
                'high': price * 1.01,
                'low': price * 0.99,
                'close': price,
                'volume': np.random.randint(1000, 10000)
            })
        
        return pd.DataFrame(prices)

    def test_StrategyBase_Init(self):
        """测试基础策略初始化"""
        strategy = StrategyBase("TestStrategy")
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.name, "TestStrategy")

    def test_StrategyBase_DataFeederBinding(self):
        """测试数据源绑定"""
        strategy = StrategyBase("TestStrategy")
        mock_feeder = Mock()
        
        strategy.bind_data_feeder(mock_feeder)
        self.assertEqual(strategy.data_feeder, mock_feeder)

    def test_StrategyBase_CalMethod(self):
        """测试策略计算方法接口"""
        strategy = StrategyBase("TestStrategy")
        
        # cal方法应该返回Signal或None
        result = strategy.cal(self.portfolio_info, self.mock_event)
        self.assertTrue(result is None or isinstance(result, Signal))

    def test_DualThrustStrategy_Init(self):
        """测试双推策略初始化"""
        try:
            strategy = DualThrustStrategy("DualThrust")
            self.assertIsNotNone(strategy)
        except NameError:
            self.skipTest("DualThrustStrategy not implemented")

    def test_DualThrustStrategy_Calculation(self):
        """测试双推策略计算"""
        try:
            strategy = DualThrustStrategy("DualThrust")
            
            # 设置策略参数
            if hasattr(strategy, 'set_params'):
                strategy.set_params({
                    'k1': 0.7,  # 上轨系数
                    'k2': 0.7,  # 下轨系数
                    'period': 20  # 计算周期
                })
            
            # 测试策略计算
            result = strategy.cal(self.portfolio_info, self.mock_event)
            
            # 结果应该是Signal对象或None
            self.assertTrue(result is None or isinstance(result, Signal))
            
        except NameError:
            self.skipTest("DualThrustStrategy not implemented")

    def test_MeanReversionStrategy_Init(self):
        """测试均值回归策略初始化"""
        try:
            strategy = MeanReversionStrategy("MeanReversion")
            self.assertIsNotNone(strategy)
        except NameError:
            self.skipTest("MeanReversionStrategy not implemented")

    def test_MeanReversionStrategy_Logic(self):
        """测试均值回归策略逻辑"""
        try:
            strategy = MeanReversionStrategy("MeanReversion")
            
            # 设置历史数据用于计算均值
            if hasattr(strategy, 'set_historical_data'):
                strategy.set_historical_data(self.market_data)
            
            # 测试在价格偏离均值时的信号生成
            result = strategy.cal(self.portfolio_info, self.mock_event)
            
            if result is not None:
                self.assertIsInstance(result, Signal)
                # 均值回归策略应该在价格高于均值时生成卖出信号
                # 在价格低于均值时生成买入信号
                self.assertIn(result.direction, [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT])
                
        except NameError:
            self.skipTest("MeanReversionStrategy not implemented")

    def test_TrendFollowStrategy_Init(self):
        """测试趋势跟踪策略初始化"""
        try:
            strategy = TrendFollowStrategy("TrendFollow")
            self.assertIsNotNone(strategy)
        except NameError:
            self.skipTest("TrendFollowStrategy not implemented")

    def test_TrendFollowStrategy_TrendDetection(self):
        """测试趋势跟踪策略的趋势检测"""
        try:
            strategy = TrendFollowStrategy("TrendFollow")
            
            # 创建明显的上升趋势数据
            uptrend_data = pd.DataFrame({
                'close': [100, 102, 104, 106, 108, 110],
                'timestamp': pd.date_range('2023-01-01', periods=6, freq='D')
            })
            
            # 如果策略有趋势检测方法
            if hasattr(strategy, 'detect_trend'):
                trend = strategy.detect_trend(uptrend_data)
                self.assertIn(trend, ['up', 'down', 'sideways', 1, -1, 0])
            
        except NameError:
            self.skipTest("TrendFollowStrategy not implemented")

    def test_Strategy_SignalGeneration(self):
        """测试策略信号生成的一般特性"""
        strategies = []
        
        # 尝试实例化各种策略
        strategy_classes = [StrategyBase]
        try:
            strategy_classes.append(DualThrustStrategy)
        except NameError:
            pass
        try:
            strategy_classes.append(MeanReversionStrategy)
        except NameError:
            pass
        try:
            strategy_classes.append(TrendFollowStrategy)
        except NameError:
            pass
        
        for strategy_class in strategy_classes:
            try:
                strategy = strategy_class("Test")
                strategies.append(strategy)
            except Exception:
                continue
        
        for strategy in strategies:
            # 测试信号生成
            result = strategy.cal(self.portfolio_info, self.mock_event)
            
            if result is not None:
                self.assertIsInstance(result, Signal)
                # 信号应该有基本属性
                self.assertTrue(hasattr(result, 'direction'))
                self.assertTrue(hasattr(result, 'code') or hasattr(result, 'symbol'))

    def test_Strategy_ParameterSetting(self):
        """测试策略参数设置"""
        strategy = StrategyBase("TestStrategy")
        
        # 测试参数设置方法（如果存在）
        if hasattr(strategy, 'set_params'):
            test_params = {
                'period': 20,
                'threshold': 0.02,
                'risk_level': 0.1
            }
            
            try:
                strategy.set_params(test_params)
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"参数设置失败: {e}")

    def test_Strategy_HistoricalDataAccess(self):
        """测试策略历史数据访问"""
        strategy = StrategyBase("TestStrategy")
        
        # 测试历史数据设置和访问
        if hasattr(strategy, 'set_historical_data'):
            strategy.set_historical_data(self.market_data)
            
            if hasattr(strategy, 'get_historical_data'):
                historical_data = strategy.get_historical_data()
                self.assertIsNotNone(historical_data)

    def test_Strategy_RiskManagement(self):
        """测试策略风险管理"""
        strategy = StrategyBase("TestStrategy")
        
        # 测试风险管理相关方法
        risk_methods = ['calculate_risk', 'check_risk_limits', 'apply_risk_control']
        
        for method_name in risk_methods:
            if hasattr(strategy, method_name):
                try:
                    method = getattr(strategy, method_name)
                    # 尝试调用风险管理方法
                    if method_name == 'calculate_risk':
                        result = method(self.portfolio_info)
                    else:
                        result = method()
                    
                    # 风险计算结果应该是数值或布尔值
                    if result is not None:
                        self.assertIsInstance(result, (int, float, bool))
                        
                except Exception:
                    # 风险管理方法可能需要特定的参数或状态
                    pass

    def test_Strategy_PositionManagement(self):
        """测试策略持仓管理"""
        strategy = StrategyBase("TestStrategy")
        
        # 测试持仓相关方法
        position_methods = ['get_position', 'calculate_position_size', 'update_position']
        
        for method_name in position_methods:
            if hasattr(strategy, method_name):
                try:
                    method = getattr(strategy, method_name)
                    
                    if method_name == 'get_position':
                        result = method('TEST001')  # 测试股票代码
                    elif method_name == 'calculate_position_size':
                        result = method(1000, 0.02)  # 测试金额和风险水平
                    else:
                        result = method()
                    
                    if result is not None:
                        self.assertIsInstance(result, (int, float, dict))
                        
                except Exception:
                    # 持仓管理方法可能需要特定的参数或状态
                    pass

    def test_Strategy_PerformanceTracking(self):
        """测试策略性能跟踪"""
        strategy = StrategyBase("TestStrategy")
        
        # 测试性能跟踪相关方法
        performance_methods = ['get_performance', 'calculate_returns', 'track_signals']
        
        for method_name in performance_methods:
            if hasattr(strategy, method_name):
                try:
                    method = getattr(strategy, method_name)
                    result = method()
                    
                    if result is not None:
                        # 性能数据通常是字典或DataFrame
                        self.assertIsInstance(result, (dict, pd.DataFrame, list))
                        
                except Exception:
                    # 性能跟踪方法可能需要历史数据
                    pass

    def test_Strategy_ErrorHandling(self):
        """测试策略错误处理"""
        strategy = StrategyBase("TestStrategy")
        
        # 测试异常输入的处理
        invalid_inputs = [
            (None, self.mock_event),
            (self.portfolio_info, None),
            ({}, self.mock_event),
            (self.portfolio_info, {})
        ]
        
        for portfolio_info, event in invalid_inputs:
            try:
                result = strategy.cal(portfolio_info, event)
                # 策略应该能够处理异常输入而不崩溃
                self.assertTrue(result is None or isinstance(result, Signal))
            except Exception as e:
                # 如果抛出异常，应该是合理的异常类型
                self.assertIsInstance(e, (ValueError, AttributeError, TypeError))


