#!/usr/bin/env python3
"""
Test cases for Weighted Moving Average (WMA)
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ginkgo.backtest.computation.indicators.weighted_moving_average import WeightedMovingAverage


class TestWeightedMovingAverage(unittest.TestCase):
    """测试加权移动平均线"""
    
    def setUp(self):
        """设置测试数据"""
        self.test_prices_5 = [100.0, 101.0, 102.0, 103.0, 104.0]
        self.test_prices_3 = [100.0, 102.0, 104.0]
        
    def test_wma_basic_calculation(self):
        """测试基本WMA计算"""
        result = WeightedMovingAverage.cal(5, self.test_prices_5)
        
        # 手动计算WMA验证
        weights = np.array([1, 2, 3, 4, 5], dtype=float)
        weights = weights / weights.sum()
        expected = np.sum(np.array(self.test_prices_5) * weights)
        
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_wma_weight_distribution(self):
        """测试权重分布"""
        # WMA应该给最新数据更高权重
        # 测试：[100, 101, 102, 103, 104] 权重 [1, 2, 3, 4, 5]
        result = WeightedMovingAverage.cal(5, self.test_prices_5)
        
        # 手动计算验证权重分布
        total_weight = 1 + 2 + 3 + 4 + 5  # 15
        expected = (100*1 + 101*2 + 102*3 + 103*4 + 104*5) / total_weight
        
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_wma_three_period(self):
        """测试3周期WMA"""
        result = WeightedMovingAverage.cal(3, self.test_prices_3)
        
        # 权重 [1, 2, 3]，总权重 6
        expected = (100*1 + 102*2 + 104*3) / 6
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_wma_single_period(self):
        """测试周期为1的WMA"""
        result = WeightedMovingAverage.cal(1, [105.0])
        # 单个数据的WMA应该等于该数据本身
        self.assertAlmostEqual(result, 105.0, places=6)
    
    def test_wma_vs_sma_comparison(self):
        """测试WMA与SMA的比较"""
        from ginkgo.backtest.computation.indicators.simple_moving_average import SimpleMovingAverage
        
        # 使用上升趋势数据
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        
        wma_result = WeightedMovingAverage.cal(5, prices)
        sma_result = SimpleMovingAverage.cal(5, prices)
        
        # 在上升趋势中，WMA应该大于SMA（因为给最新的高价格更多权重）
        self.assertGreater(wma_result, sma_result)
        
        # 使用下降趋势数据
        decreasing_prices = [104.0, 103.0, 102.0, 101.0, 100.0]
        
        wma_decreasing = WeightedMovingAverage.cal(5, decreasing_prices)
        sma_decreasing = SimpleMovingAverage.cal(5, decreasing_prices)
        
        # 在下降趋势中，WMA应该小于SMA（因为给最新的低价格更多权重）
        self.assertLess(wma_decreasing, sma_decreasing)
    
    def test_wma_constant_prices(self):
        """测试价格不变的WMA"""
        constant_prices = [100.0] * 5
        result = WeightedMovingAverage.cal(5, constant_prices)
        # 价格相同时，WMA应该等于价格
        self.assertAlmostEqual(result, 100.0, places=6)
    
    def test_wma_wrong_length(self):
        """测试错误数据长度"""
        # 数据不足
        result = WeightedMovingAverage.cal(5, [100.0, 101.0])
        self.assertTrue(pd.isna(result))
        
        # 数据过多
        result = WeightedMovingAverage.cal(3, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_wma_with_nan(self):
        """测试包含NaN的数据"""
        prices_with_nan = [100.0, float('nan'), 102.0, 103.0, 104.0]
        result = WeightedMovingAverage.cal(5, prices_with_nan)
        self.assertTrue(pd.isna(result))
    
    def test_wma_zero_period(self):
        """测试周期为0"""
        result = WeightedMovingAverage.cal(0, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_wma_negative_period(self):
        """测试负周期"""
        result = WeightedMovingAverage.cal(-5, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_wma_weight_calculation(self):
        """测试权重计算的正确性"""
        period = 4
        prices = [100.0, 101.0, 102.0, 103.0]
        
        result = WeightedMovingAverage.cal(period, prices)
        
        # 权重应该是 [1, 2, 3, 4]，标准化后 [1/10, 2/10, 3/10, 4/10]
        weights_sum = sum(range(1, period + 1))  # 1+2+3+4 = 10
        expected = sum(prices[i] * (i + 1) for i in range(period)) / weights_sum
        
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_wma_sensitivity_to_recent_data(self):
        """测试WMA对最新数据的敏感性"""
        # 前4个价格相同，最后一个价格大幅变化
        base_prices = [100.0, 100.0, 100.0, 100.0]
        
        # 最后价格上涨
        prices_up = base_prices + [110.0]
        wma_up = WeightedMovingAverage.cal(5, prices_up)
        
        # 最后价格下跌
        prices_down = base_prices + [90.0]
        wma_down = WeightedMovingAverage.cal(5, prices_down)
        
        # WMA应该明显反映最新价格的变化
        self.assertGreater(wma_up, 100.0)
        self.assertLess(wma_down, 100.0)
        
        # 上涨和下跌的差异应该明显
        self.assertGreater(wma_up - 100.0, 100.0 - wma_down)  # 因为权重向最新倾斜
    
    def test_wma_matrix_calculation(self):
        """测试WMA矩阵计算"""
        dates = pd.date_range('2023-01-01', periods=10)
        data = {
            'stock1': [100 + i for i in range(10)],
            'stock2': [200 + i*2 for i in range(10)]
        }
        matrix = pd.DataFrame(data, index=dates)
        
        result = WeightedMovingAverage.cal_matrix(5, matrix)
        
        # 检查结果维度
        self.assertEqual(result.shape, matrix.shape)
        
        # 检查前4行应该是NaN（不足5个数据）
        self.assertTrue(pd.isna(result.iloc[3, 0]))
        
        # 检查第5行的值（手动计算验证）
        stock1_prices = [100, 101, 102, 103, 104]
        weights = np.array([1, 2, 3, 4, 5], dtype=float)
        weights = weights / weights.sum()
        expected_stock1 = np.sum(np.array(stock1_prices) * weights)
        
        self.assertAlmostEqual(result.iloc[4, 0], expected_stock1, places=6)
    
    def test_wma_edge_cases(self):
        """测试边界情况"""
        # 零价格
        prices_with_zero = [0.0, 1.0, 2.0, 3.0, 4.0]
        result = WeightedMovingAverage.cal(5, prices_with_zero)
        self.assertFalse(pd.isna(result))
        
        # 负价格
        negative_prices = [-5.0, -4.0, -3.0, -2.0, -1.0]
        result = WeightedMovingAverage.cal(5, negative_prices)
        self.assertFalse(pd.isna(result))
        self.assertLess(result, 0)  # 结果应该为负
    
    def test_wma_large_period(self):
        """测试大周期WMA"""
        large_period = 20
        prices = [100.0 + i*0.5 for i in range(large_period)]
        
        result = WeightedMovingAverage.cal(large_period, prices)
        self.assertFalse(pd.isna(result))
        
        # 结果应该在合理范围内
        min_price = min(prices)
        max_price = max(prices)
        self.assertGreaterEqual(result, min_price)
        self.assertLessEqual(result, max_price)


if __name__ == '__main__':
    unittest.main(verbosity=2)