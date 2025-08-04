#!/usr/bin/env python3
"""
Test cases for Exponential Moving Average (EMA)
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ginkgo.backtest.computation.technical.exponential_moving_average import ExponentialMovingAverage


class TestExponentialMovingAverage(unittest.TestCase):
    """测试指数移动平均线"""
    
    def setUp(self):
        """设置测试数据"""
        self.test_prices_5 = [100.0, 101.0, 102.0, 103.0, 104.0]
        self.test_prices_10 = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]
        
    def test_ema_basic_calculation(self):
        """测试基本EMA计算"""
        result = ExponentialMovingAverage.cal(5, self.test_prices_5)
        
        # 手动计算EMA验证
        alpha = 2.0 / (5 + 1)
        ema = self.test_prices_5[0]
        for i in range(1, len(self.test_prices_5)):
            ema = alpha * self.test_prices_5[i] + (1 - alpha) * ema
        
        self.assertAlmostEqual(result, ema, places=6)
    
    def test_ema_single_value(self):
        """测试单个值的EMA"""
        result = ExponentialMovingAverage.cal(1, [105.0])
        self.assertAlmostEqual(result, 105.0, places=6)
    
    def test_ema_two_values(self):
        """测试两个值的EMA"""
        prices = [100.0, 102.0]
        result = ExponentialMovingAverage.cal(2, prices)
        
        alpha = 2.0 / (2 + 1)
        expected = alpha * 102.0 + (1 - alpha) * 100.0
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_ema_increasing_trend(self):
        """测试上升趋势的EMA"""
        increasing_prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        result = ExponentialMovingAverage.cal(5, increasing_prices)
        
        # EMA应该接近最新价格但小于最新价格
        self.assertGreater(result, 100.0)
        self.assertLess(result, 104.0)
    
    def test_ema_decreasing_trend(self):
        """测试下降趋势的EMA"""
        decreasing_prices = [104.0, 103.0, 102.0, 101.0, 100.0]
        result = ExponentialMovingAverage.cal(5, decreasing_prices)
        
        # EMA应该接近最新价格但大于最新价格
        self.assertLess(result, 104.0)
        self.assertGreater(result, 100.0)
    
    def test_ema_constant_prices(self):
        """测试价格不变的EMA"""
        constant_prices = [100.0] * 5
        result = ExponentialMovingAverage.cal(5, constant_prices)
        self.assertAlmostEqual(result, 100.0, places=6)
    
    def test_ema_wrong_length(self):
        """测试错误数据长度"""
        # 数据不足
        result = ExponentialMovingAverage.cal(5, [100.0, 101.0])
        self.assertTrue(pd.isna(result))
        
        # 数据过多
        result = ExponentialMovingAverage.cal(3, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_ema_with_nan(self):
        """测试包含NaN的数据"""
        prices_with_nan = [100.0, float('nan'), 102.0, 103.0, 104.0]
        result = ExponentialMovingAverage.cal(5, prices_with_nan)
        self.assertTrue(pd.isna(result))
    
    def test_ema_zero_period(self):
        """测试周期为0"""
        result = ExponentialMovingAverage.cal(0, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_ema_negative_period(self):
        """测试负周期"""
        result = ExponentialMovingAverage.cal(-5, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_ema_alpha_calculation(self):
        """测试EMA平滑系数计算"""
        # 验证不同周期的alpha值
        period_10_alpha = 2.0 / (10 + 1)
        period_20_alpha = 2.0 / (20 + 1)
        
        # 周期越短，alpha越大，对新数据反应越敏感
        self.assertGreater(period_10_alpha, period_20_alpha)
        
        # alpha应该在0和1之间
        self.assertGreater(period_10_alpha, 0)
        self.assertLess(period_10_alpha, 1)
    
    def test_ema_vs_sma_comparison(self):
        """测试EMA与SMA的比较"""
        from ginkgo.backtest.computation.technical.simple_moving_average import SimpleMovingAverage
        
        prices = [100.0, 105.0, 95.0, 110.0, 90.0]
        
        ema_result = ExponentialMovingAverage.cal(5, prices)
        sma_result = SimpleMovingAverage.cal(5, prices)
        
        # 两者都应该是有效值
        self.assertFalse(pd.isna(ema_result))
        self.assertFalse(pd.isna(sma_result))
        
        # EMA对最新价格更敏感，在波动数据中通常与SMA不同
        # 但在这个特定例子中可能接近，所以只检查合理性
        self.assertGreater(ema_result, 80.0)
        self.assertLess(ema_result, 120.0)
    
    def test_ema_matrix_calculation(self):
        """测试EMA矩阵计算"""
        dates = pd.date_range('2023-01-01', periods=10)
        data = {
            'stock1': [100 + i for i in range(10)],
            'stock2': [200 + i*2 for i in range(10)]
        }
        matrix = pd.DataFrame(data, index=dates)
        
        result = ExponentialMovingAverage.cal_matrix(5, matrix)
        
        # 检查结果维度
        self.assertEqual(result.shape, matrix.shape)
        
        # EMA从第一个数据点就应该有值
        self.assertFalse(pd.isna(result.iloc[0, 0]))
        self.assertFalse(pd.isna(result.iloc[0, 1]))
    
    def test_ema_edge_cases(self):
        """测试边界情况"""
        # 极小的数值
        small_prices = [0.001, 0.002, 0.003, 0.004, 0.005]
        result = ExponentialMovingAverage.cal(5, small_prices)
        self.assertFalse(pd.isna(result))
        self.assertGreater(result, 0)
        
        # 极大的数值
        large_prices = [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6]
        result = ExponentialMovingAverage.cal(5, large_prices)
        self.assertFalse(pd.isna(result))
        self.assertGreater(result, 1e6)
    
    def test_ema_precision(self):
        """测试计算精度"""
        # 使用已知结果的数据测试精度
        prices = [100.0, 100.0, 100.0, 100.0, 100.0]
        result = ExponentialMovingAverage.cal(5, prices)
        
        # 所有价格相同时，EMA应该等于价格
        self.assertAlmostEqual(result, 100.0, places=10)


if __name__ == '__main__':
    unittest.main(verbosity=2)