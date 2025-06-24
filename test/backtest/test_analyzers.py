import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.backtest.analyzers.sharpe_ratio import SharpeRatio
from ginkgo.backtest.analyzers.max_drawdown import MaxDrawdown
from ginkgo.backtest.analyzers.annualized_returns import AnnualizedReturns
from ginkgo.backtest.analyzers.profit import Profit
from ginkgo.backtest.analyzers.winloss_ratio import WinLossRatio


class AnalyzersTest(unittest.TestCase):
    """
    测试分析器模块
    """

    def setUp(self):
        """准备测试数据"""
        # 创建模拟的回测数据
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        
        # 模拟价格数据 - 有一定波动的上升趋势
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
        prices = [100]
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        self.price_data = pd.DataFrame({
            'timestamp': dates,
            'close': prices[1:],  # 去掉初始价格
            'returns': returns
        })
        
        # 模拟组合净值数据
        self.portfolio_data = pd.DataFrame({
            'timestamp': dates,
            'net_value': np.cumprod(1 + returns) * 100000,  # 起始资金10万
            'returns': returns
        })

    def test_BaseAnalyzer_Init(self):
        """测试基础分析器初始化"""
        analyzer = BaseAnalyzer()
        self.assertIsNotNone(analyzer)
        
        # 检查基本属性
        self.assertTrue(hasattr(analyzer, 'name'))

    def test_SharpeRatio_Calculation(self):
        """测试夏普比率计算"""
        analyzer = SharpeRatio()
        
        # 使用模拟数据计算夏普比率
        returns = self.portfolio_data['returns'].dropna()
        result = analyzer.analyze(returns)
        
        # 夏普比率应该是数值类型
        self.assertIsInstance(result, (int, float))
        
        # 对于正常市场数据，夏普比率应该在合理范围内
        self.assertGreater(result, -5)  # 不应该太负
        self.assertLess(result, 10)     # 不应该太高

    def test_SharpeRatio_ZeroReturns(self):
        """测试零收益率的夏普比率"""
        analyzer = SharpeRatio()
        
        # 创建全零收益率数据
        zero_returns = pd.Series([0.0] * 100)
        result = analyzer.analyze(zero_returns)
        
        # 零收益率的夏普比率应该是0或NaN
        self.assertTrue(result == 0 or pd.isna(result))

    def test_MaxDrawdown_Calculation(self):
        """测试最大回撤计算"""
        analyzer = MaxDrawdown()
        
        # 使用净值数据计算最大回撤
        net_values = self.portfolio_data['net_value']
        result = analyzer.analyze(net_values)
        
        # 最大回撤应该是负数或零
        self.assertLessEqual(result, 0)
        
        # 最大回撤不应该超过-100%
        self.assertGreaterEqual(result, -1)

    def test_MaxDrawdown_MonotonicIncrease(self):
        """测试单调递增序列的最大回撤"""
        analyzer = MaxDrawdown()
        
        # 创建单调递增的净值序列
        increasing_values = pd.Series(range(1, 101))
        result = analyzer.analyze(increasing_values)
        
        # 单调递增序列的最大回撤应该是0
        self.assertEqual(result, 0)

    def test_AnnualizedReturns_Calculation(self):
        """测试年化收益率计算"""
        analyzer = AnnualizedReturns()
        
        # 使用一年的数据计算年化收益率
        returns = self.portfolio_data['returns']
        result = analyzer.analyze(returns, periods=252)  # 252个交易日
        
        # 年化收益率应该是数值类型
        self.assertIsInstance(result, (int, float))
        
        # 对于正常市场数据，年化收益率应该在合理范围内
        self.assertGreater(result, -1)    # 不应该低于-100%
        self.assertLess(result, 5)        # 不应该高于500%

    def test_Profit_Calculation(self):
        """测试利润计算"""
        analyzer = Profit()
        
        # 使用净值数据计算总利润
        net_values = self.portfolio_data['net_value']
        initial_value = net_values.iloc[0]
        final_value = net_values.iloc[-1]
        
        result = analyzer.analyze(net_values)
        
        # 利润应该等于最终净值减去初始净值
        expected_profit = final_value - initial_value
        self.assertAlmostEqual(result, expected_profit, places=2)

    def test_WinLossRatio_Calculation(self):
        """测试胜负比计算"""
        analyzer = WinLossRatio()
        
        # 使用收益率数据计算胜负比
        returns = self.portfolio_data['returns']
        result = analyzer.analyze(returns)
        
        # 胜负比应该是正数
        self.assertGreaterEqual(result, 0)
        
        # 对于随机数据，胜负比应该在合理范围内
        self.assertLess(result, 10)  # 不应该太高

    def test_WinLossRatio_AllWins(self):
        """测试全胜情况的胜负比"""
        analyzer = WinLossRatio()
        
        # 创建全正收益率数据
        all_wins = pd.Series([0.01, 0.02, 0.015, 0.008, 0.012])
        result = analyzer.analyze(all_wins)
        
        # 全胜情况下胜负比应该是无穷大或非常大的数
        self.assertTrue(result == float('inf') or result > 100)

    def test_WinLossRatio_AllLosses(self):
        """测试全负情况的胜负比"""
        analyzer = WinLossRatio()
        
        # 创建全负收益率数据
        all_losses = pd.Series([-0.01, -0.02, -0.015, -0.008, -0.012])
        result = analyzer.analyze(all_losses)
        
        # 全负情况下胜负比应该是0
        self.assertEqual(result, 0)

    def test_Analyzers_EmptyData(self):
        """测试空数据处理"""
        analyzers = [SharpeRatio(), MaxDrawdown(), AnnualizedReturns(), Profit(), WinLossRatio()]
        empty_data = pd.Series([])
        
        for analyzer in analyzers:
            with self.assertRaises((ValueError, IndexError, ZeroDivisionError)):
                analyzer.analyze(empty_data)

    def test_Analyzers_NaNData(self):
        """测试包含NaN的数据处理"""
        analyzers = [SharpeRatio(), MaxDrawdown(), AnnualizedReturns(), Profit(), WinLossRatio()]
        nan_data = pd.Series([1, 2, np.nan, 4, 5])
        
        for analyzer in analyzers:
            try:
                result = analyzer.analyze(nan_data)
                # 如果成功计算，结果应该不是NaN（除非算法设计如此）
                if not pd.isna(result):
                    self.assertIsInstance(result, (int, float))
            except (ValueError, TypeError):
                # 某些分析器可能无法处理NaN数据，这是可接受的
                pass

    def test_Analyzers_ConsistentInterface(self):
        """测试分析器接口一致性"""
        analyzers = [SharpeRatio(), MaxDrawdown(), AnnualizedReturns(), Profit(), WinLossRatio()]
        test_data = self.portfolio_data['returns']
        
        for analyzer in analyzers:
            # 每个分析器都应该有analyze方法
            self.assertTrue(hasattr(analyzer, 'analyze'))
            self.assertTrue(callable(analyzer.analyze))
            
            # 每个分析器都应该有name属性
            self.assertTrue(hasattr(analyzer, 'name'))
            
            # analyze方法应该能接受pandas Series
            try:
                result = analyzer.analyze(test_data)
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"{analyzer.__class__.__name__} analyze方法失败: {e}")


