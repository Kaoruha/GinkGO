#!/usr/bin/env python3
"""
Test cases for Average True Range (ATR)
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ginkgo.backtest.computation.indicators.average_true_range import AverageTrueRange


class TestAverageTrueRange(unittest.TestCase):
    """测试平均真实范围"""
    
    def setUp(self):
        """设置测试数据"""
        # ATR需要period+1个数据点（需要前一日收盘价）
        self.high_prices = [105.0] + [105.0 + i for i in range(1, 15)]      # 15个数据点
        self.low_prices = [95.0] + [95.0 + i for i in range(1, 15)]         # 15个数据点
        self.close_prices = [100.0] + [100.0 + i for i in range(1, 15)]     # 15个数据点
        
        # 简单测试数据
        self.simple_high = [102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
        self.simple_low = [98.0, 99.0, 100.0, 101.0, 102.0, 103.0]
        self.simple_close = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        
    def test_atr_basic_calculation(self):
        """测试基本ATR计算"""
        result = AverageTrueRange.cal(14, self.high_prices, self.low_prices, self.close_prices)
        
        # ATR应该是正数
        self.assertGreater(result, 0)
        self.assertFalse(pd.isna(result))
    
    def test_atr_simple_case(self):
        """测试简单情况的ATR计算"""
        result = AverageTrueRange.cal(5, self.simple_high, self.simple_low, self.simple_close)
        
        # 手动验证计算
        # True Range计算：
        # Day 1: max(103-99, |103-100|, |99-100|) = max(4, 3, 1) = 4
        # Day 2: max(104-100, |104-101|, |100-101|) = max(4, 3, 1) = 4  
        # Day 3: max(105-101, |105-102|, |101-102|) = max(4, 3, 1) = 4
        # Day 4: max(106-102, |106-103|, |102-103|) = max(4, 3, 1) = 4
        # Day 5: max(107-103, |107-104|, |103-104|) = max(4, 3, 1) = 4
        # ATR = (4+4+4+4+4)/5 = 4.0
        
        self.assertAlmostEqual(result, 4.0, places=6)
    
    def test_atr_with_gaps(self):
        """测试有跳空的ATR计算"""
        # 创建有跳空的数据
        high_with_gap = [102.0, 110.0, 111.0, 112.0, 113.0, 114.0]   # 第二天跳高开盘
        low_with_gap = [98.0, 108.0, 109.0, 110.0, 111.0, 112.0]
        close_with_gap = [100.0, 109.0, 110.0, 111.0, 112.0, 113.0]
        
        result = AverageTrueRange.cal(5, high_with_gap, low_with_gap, close_with_gap)
        
        # 有跳空时ATR应该更大
        self.assertGreater(result, 3.0)
        self.assertFalse(pd.isna(result))
    
    def test_atr_no_volatility(self):
        """测试无波动的情况"""
        # 所有价格相同
        constant_high = [100.0] * 6
        constant_low = [100.0] * 6  
        constant_close = [100.0] * 6
        
        result = AverageTrueRange.cal(5, constant_high, constant_low, constant_close)
        
        # 无波动时ATR应该为0
        self.assertAlmostEqual(result, 0.0, places=6)
    
    def test_atr_wrong_length(self):
        """测试错误数据长度"""
        # 数据不足
        result = AverageTrueRange.cal(14, self.simple_high, self.simple_low, self.simple_close)
        self.assertTrue(pd.isna(result))
        
        # 数据过多
        result = AverageTrueRange.cal(3, self.high_prices, self.low_prices, self.close_prices)
        self.assertTrue(pd.isna(result))
    
    def test_atr_mismatched_lengths(self):
        """测试数据长度不匹配"""
        high_short = [105.0, 106.0, 107.0]
        low_normal = [95.0] + [95.0 + i for i in range(1, 15)]
        close_normal = [100.0] + [100.0 + i for i in range(1, 15)]
        
        result = AverageTrueRange.cal(14, high_short, low_normal, close_normal)
        self.assertTrue(pd.isna(result))
    
    def test_atr_with_nan(self):
        """测试包含NaN的数据"""
        high_with_nan = self.high_prices.copy()
        high_with_nan[5] = float('nan')
        
        result = AverageTrueRange.cal(14, high_with_nan, self.low_prices, self.close_prices)
        self.assertTrue(pd.isna(result))
    
    def test_atr_zero_period(self):
        """测试周期为0"""
        result = AverageTrueRange.cal(0, self.high_prices, self.low_prices, self.close_prices)
        self.assertTrue(pd.isna(result))
    
    def test_atr_negative_period(self):
        """测试负周期"""
        result = AverageTrueRange.cal(-5, self.high_prices, self.low_prices, self.close_prices)
        self.assertTrue(pd.isna(result))
    
    def test_atr_true_range_components(self):
        """测试真实范围的三个组成部分"""
        # 测试真实范围计算的三种情况
        
        # 情况1：当日高低差最大
        high_case1 = [100.0, 110.0]  # 高价110
        low_case1 = [100.0, 100.0]   # 低价100  
        close_case1 = [100.0, 105.0] # 前收100，当前收105
        
        result1 = AverageTrueRange.cal(1, high_case1, low_case1, close_case1)
        self.assertAlmostEqual(result1, 10.0, places=6)  # max(10, 5, 0) = 10
        
        # 情况2：当日高价与前收差最大
        high_case2 = [100.0, 115.0]  
        low_case2 = [100.0, 110.0]   
        close_case2 = [100.0, 112.0] 
        
        result2 = AverageTrueRange.cal(1, high_case2, low_case2, close_case2)
        self.assertAlmostEqual(result2, 15.0, places=6)  # max(5, 15, 10) = 15
        
        # 情况3：当日低价与前收差最大
        high_case3 = [100.0, 95.0]   
        low_case3 = [100.0, 90.0]    
        close_case3 = [100.0, 92.0]  
        
        result3 = AverageTrueRange.cal(1, high_case3, low_case3, close_case3)
        self.assertAlmostEqual(result3, 10.0, places=6)  # max(5, 5, 10) = 10
    
    def test_atr_increasing_volatility(self):
        """测试递增波动率"""
        # 创建波动率递增的数据
        high_increasing = [100.0]
        low_increasing = [100.0] 
        close_increasing = [100.0]
        
        for i in range(1, 15):
            volatility = i  # 波动率递增
            high_increasing.append(100.0 + volatility)
            low_increasing.append(100.0 - volatility)
            close_increasing.append(100.0)
        
        result = AverageTrueRange.cal(14, high_increasing, low_increasing, close_increasing)
        
        # ATR应该反映平均波动率
        self.assertGreater(result, 10.0)  # 平均波动率应该大于10
        self.assertLessEqual(result, 15.0)    # 但小于等于最大波动率
    
    def test_atr_matrix_calculation(self):
        """测试ATR矩阵计算"""
        # 创建长格式数据
        data = []
        stocks = ['STOCK_A', 'STOCK_B']
        dates = pd.date_range('2023-01-01', periods=20)
        
        for stock in stocks:
            for i, date in enumerate(dates):
                data.append({
                    'code': stock,
                    'timestamp': date,
                    'high': 100.0 + i + 2,
                    'low': 100.0 + i - 2,
                    'close': 100.0 + i,
                    'volume': 1000
                })
        
        long_format_data = pd.DataFrame(data)
        result = AverageTrueRange.cal_matrix(5, long_format_data)
        
        # 检查结果包含atr列
        self.assertIn('atr', result.columns)
        
        # 检查ATR值的有效性
        valid_atr = result['atr'].dropna()
        for atr_val in valid_atr:
            self.assertGreater(atr_val, 0)
    
    def test_atr_edge_cases(self):
        """测试边界情况"""
        # 极小数值
        small_high = [0.001, 0.002, 0.003, 0.004, 0.005, 0.006]
        small_low = [0.0005, 0.0015, 0.0025, 0.0035, 0.0045, 0.0055]
        small_close = [0.0008, 0.0018, 0.0028, 0.0038, 0.0048, 0.0058]
        
        result = AverageTrueRange.cal(5, small_high, small_low, small_close)
        self.assertGreater(result, 0)
        self.assertFalse(pd.isna(result))
        
        # 极大数值
        large_high = [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6, 1.5e6]
        large_low = [0.9e6, 1.0e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6]
        large_close = [0.95e6, 1.05e6, 1.15e6, 1.25e6, 1.35e6, 1.45e6]
        
        result = AverageTrueRange.cal(5, large_high, large_low, large_close)
        self.assertGreater(result, 0)
        self.assertFalse(pd.isna(result))
    
    def test_atr_realistic_data(self):
        """测试真实市场数据模拟"""
        # 模拟真实的股价数据
        np.random.seed(42)
        
        high_realistic = [100.0]
        low_realistic = [100.0]
        close_realistic = [100.0]
        
        for i in range(14):
            # 模拟日内波动 
            daily_range = np.random.uniform(1.0, 5.0)
            prev_close = close_realistic[-1]
            
            # 生成当日的开盘价（可能跳空）
            gap = np.random.normal(0, 0.5)
            open_price = prev_close + gap
            
            # 生成高低价
            high_price = open_price + np.random.uniform(0, daily_range)
            low_price = open_price - np.random.uniform(0, daily_range)
            
            # 生成收盘价
            close_price = np.random.uniform(low_price, high_price)
            
            high_realistic.append(high_price)
            low_realistic.append(low_price)
            close_realistic.append(close_price)
        
        result = AverageTrueRange.cal(14, high_realistic, low_realistic, close_realistic)
        
        # ATR应该在合理范围内
        self.assertGreater(result, 0.5)  # 至少有一些波动
        self.assertLess(result, 10.0)    # 但不会过度波动
    
    def test_atr_performance(self):
        """测试ATR计算性能"""
        import time
        
        # 创建大量测试数据
        large_high = [100.0 + i + 2 for i in range(500)]
        large_low = [100.0 + i - 2 for i in range(500)]
        large_close = [100.0 + i for i in range(500)]
        
        start_time = time.time()
        for _ in range(50):
            result = AverageTrueRange.cal(14, large_high[-15:], large_low[-15:], large_close[-15:])
        end_time = time.time()
        
        # 50次计算应该很快完成
        self.assertLess(end_time - start_time, 0.5)
        self.assertFalse(pd.isna(result))


if __name__ == '__main__':
    unittest.main(verbosity=2)