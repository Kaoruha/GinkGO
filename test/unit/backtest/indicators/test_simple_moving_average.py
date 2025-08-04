#!/usr/bin/env python3
"""
Test cases for Simple Moving Average (SMA)
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ginkgo.backtest.computation.technical.simple_moving_average import SimpleMovingAverage


class TestSimpleMovingAverage(unittest.TestCase):
    """测试简单移动平均线"""
    
    def setUp(self):
        """设置测试数据"""
        self.test_prices_5 = [100.0, 101.0, 102.0, 103.0, 104.0]
        self.test_prices_10 = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]
        
    def test_sma_basic_calculation(self):
        """测试基本SMA计算"""
        result = SimpleMovingAverage.cal(5, self.test_prices_5)
        expected = sum(self.test_prices_5) / 5
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_sma_different_periods(self):
        """测试不同周期的SMA计算"""
        # 测试周期3
        result_3 = SimpleMovingAverage.cal(3, self.test_prices_5[:3])
        expected_3 = sum(self.test_prices_5[:3]) / 3
        self.assertAlmostEqual(result_3, expected_3, places=6)
        
        # 测试周期10
        result_10 = SimpleMovingAverage.cal(10, self.test_prices_10)
        expected_10 = sum(self.test_prices_10) / 10
        self.assertAlmostEqual(result_10, expected_10, places=6)
    
    def test_sma_wrong_length(self):
        """测试错误数据长度"""
        # 传入数据少于所需周期
        result = SimpleMovingAverage.cal(5, self.test_prices_5[:3])
        self.assertTrue(pd.isna(result))
        
        # 传入数据多于所需周期
        result = SimpleMovingAverage.cal(3, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_sma_with_nan(self):
        """测试包含NaN的数据"""
        prices_with_nan = [100.0, float('nan'), 102.0, 103.0, 104.0]
        result = SimpleMovingAverage.cal(5, prices_with_nan)
        self.assertTrue(pd.isna(result))
    
    def test_sma_zero_period(self):
        """测试周期为0的情况"""
        result = SimpleMovingAverage.cal(0, self.test_prices_5)
        self.assertTrue(pd.isna(result))
        
    def test_sma_negative_period(self):
        """测试负周期"""
        result = SimpleMovingAverage.cal(-5, self.test_prices_5)
        self.assertTrue(pd.isna(result))
    
    def test_sma_single_price(self):
        """测试单个价格的SMA"""
        result = SimpleMovingAverage.cal(1, [105.0])
        self.assertAlmostEqual(result, 105.0, places=6)
    
    def test_sma_zero_prices(self):
        """测试包含零价格的数据"""
        prices_with_zero = [0.0, 101.0, 102.0, 103.0, 104.0]
        result = SimpleMovingAverage.cal(5, prices_with_zero)
        expected = sum(prices_with_zero) / 5
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_sma_negative_prices(self):
        """测试包含负价格的数据"""
        prices_with_negative = [-100.0, 101.0, 102.0, 103.0, 104.0]
        result = SimpleMovingAverage.cal(5, prices_with_negative)
        expected = sum(prices_with_negative) / 5
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_sma_matrix_wide_format(self):
        """测试宽格式矩阵计算"""
        # 创建测试矩阵数据
        dates = pd.date_range('2023-01-01', periods=10)
        data = {
            'stock1': [100 + i for i in range(10)],
            'stock2': [200 + i*2 for i in range(10)]
        }
        matrix = pd.DataFrame(data, index=dates)
        
        result = SimpleMovingAverage.cal_matrix(5, matrix)
        
        # 检查结果维度
        self.assertEqual(result.shape, matrix.shape)
        
        # 检查前4行应该是NaN（不足5个数据）
        self.assertTrue(pd.isna(result.iloc[3, 0]))
        
        # 检查第5行的值
        expected_stock1 = sum(range(100, 105)) / 5
        self.assertAlmostEqual(result.iloc[4, 0], expected_stock1, places=6)
    
    def test_sma_matrix_empty_data(self):
        """测试空矩阵"""
        empty_matrix = pd.DataFrame()
        result = SimpleMovingAverage.cal_matrix(5, empty_matrix)
        self.assertTrue(result.empty)
    
    def test_sma_matrix_insufficient_data(self):
        """测试数据不足的矩阵"""
        small_matrix = pd.DataFrame({
            'stock1': [100, 101, 102],
            'stock2': [200, 201, 202]
        })
        
        result = SimpleMovingAverage.cal_matrix(5, small_matrix)
        
        # 数据不足时应该返回NaN
        self.assertTrue(pd.isna(result.iloc[0, 0]))
        self.assertTrue(pd.isna(result.iloc[1, 0]))
        self.assertTrue(pd.isna(result.iloc[2, 0]))
    
    def test_sma_performance(self):
        """测试性能"""
        import time
        
        large_prices = [100.0 + i*0.1 for i in range(1000)]
        
        start_time = time.time()
        for _ in range(100):
            result = SimpleMovingAverage.cal(20, large_prices[-20:])
        end_time = time.time()
        
        # 100次计算应该在1秒内完成
        self.assertLess(end_time - start_time, 1.0)
        self.assertFalse(pd.isna(result))


if __name__ == '__main__':
    unittest.main(verbosity=2)