#!/usr/bin/env python3
"""
Test cases for Bollinger Bands
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ginkgo.trading.computation.technical.bollinger_bands import BollingerBands


class TestBollingerBands(unittest.TestCase):
    """测试布林带"""
    
    def setUp(self):
        """设置测试数据"""
        self.test_prices_5 = [100.0, 101.0, 102.0, 103.0, 104.0]
        self.test_prices_20 = [100.0 + i*0.5 for i in range(20)]
        self.volatile_prices = [100.0, 105.0, 95.0, 110.0, 90.0]
        
    def test_bollinger_bands_basic_calculation(self):
        """测试基本布林带计算"""
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, self.test_prices_5)
        
        # 中轨应该等于SMA
        expected_middle = sum(self.test_prices_5) / 5
        self.assertAlmostEqual(middle, expected_middle, places=6)
        
        # 上轨应该大于中轨，下轨应该小于中轨
        self.assertGreater(upper, middle)
        self.assertLess(lower, middle)
        
        # 位置应该在0-1之间
        self.assertGreaterEqual(position, 0.0)
        self.assertLessEqual(position, 1.0)
        
        # 所有值都应该是有效数字
        self.assertFalse(any(pd.isna(val) for val in [upper, middle, lower, position]))
    
    def test_bollinger_bands_return_type(self):
        """测试返回值类型"""
        result = BollingerBands.cal(5, 2.0, self.test_prices_5)
        
        # 应该返回4个元素的元组
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        
        # 所有元素都应该是数字
        for val in result:
            self.assertIsInstance(val, (int, float))
    
    def test_bollinger_bands_no_volatility(self):
        """测试无波动的情况"""
        constant_prices = [100.0] * 5
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, constant_prices)
        
        # 无波动时上下轨应该等于中轨
        self.assertAlmostEqual(upper, middle, places=6)
        self.assertAlmostEqual(lower, middle, places=6)
        self.assertAlmostEqual(middle, 100.0, places=6)
        
        # 位置应该是0.5（中间位置）
        self.assertAlmostEqual(position, 0.5, places=6)
    
    def test_bollinger_bands_high_volatility(self):
        """测试高波动情况"""
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, self.volatile_prices)
        
        # 高波动时带宽应该较大
        band_width = upper - lower
        self.assertGreater(band_width, 10.0)  # 基于测试数据的预期
        
        # 位置应该合理
        self.assertGreaterEqual(position, 0.0)
        self.assertLessEqual(position, 1.0)
    
    def test_bollinger_bands_different_std_multipliers(self):
        """测试不同标准差倍数"""
        upper_1, middle_1, lower_1, pos_1 = BollingerBands.cal(5, 1.0, self.test_prices_5)
        upper_2, middle_2, lower_2, pos_2 = BollingerBands.cal(5, 2.0, self.test_prices_5)
        upper_3, middle_3, lower_3, pos_3 = BollingerBands.cal(5, 3.0, self.test_prices_5)
        
        # 中轨应该相同
        self.assertAlmostEqual(middle_1, middle_2, places=6)
        self.assertAlmostEqual(middle_2, middle_3, places=6)
        
        # 倍数越大，带宽越宽
        self.assertGreater(upper_3 - lower_3, upper_2 - lower_2)
        self.assertGreater(upper_2 - lower_2, upper_1 - lower_1)
        
        # 上轨递增，下轨递减
        self.assertGreater(upper_3, upper_2)
        self.assertGreater(upper_2, upper_1)
        self.assertLess(lower_3, lower_2)
        self.assertLess(lower_2, lower_1)
    
    def test_bollinger_bands_position_calculation(self):
        """测试价格位置计算"""
        # 测试价格在不同位置的情况
        
        # 价格在下轨
        prices_at_lower = [95.0, 96.0, 97.0, 98.0, 95.0]  # 最后价格较低
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_at_lower)
        self.assertLess(position, 0.3)  # 应该接近下轨
        
        # 价格在上轨
        prices_at_upper = [100.0, 101.0, 102.0, 103.0, 105.0]  # 最后价格较高
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_at_upper)
        self.assertGreater(position, 0.7)  # 应该接近上轨
    
    def test_bollinger_bands_wrong_length(self):
        """测试错误数据长度"""
        # 数据不足
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, [100.0, 101.0, 102.0])
        self.assertTrue(all(pd.isna(val) for val in [upper, middle, lower, position]))
        
        # 数据过多
        upper, middle, lower, position = BollingerBands.cal(3, 2.0, self.test_prices_5)
        self.assertTrue(all(pd.isna(val) for val in [upper, middle, lower, position]))
    
    def test_bollinger_bands_with_nan(self):
        """测试包含NaN的数据"""
        prices_with_nan = [100.0, float('nan'), 102.0, 103.0, 104.0]
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_with_nan)
        self.assertTrue(all(pd.isna(val) for val in [upper, middle, lower, position]))
    
    def test_bollinger_bands_invalid_parameters(self):
        """测试无效参数"""
        # 周期为0
        upper, middle, lower, position = BollingerBands.cal(0, 2.0, self.test_prices_5)
        self.assertTrue(all(pd.isna(val) for val in [upper, middle, lower, position]))
        
        # 负周期
        upper, middle, lower, position = BollingerBands.cal(-5, 2.0, self.test_prices_5)
        self.assertTrue(all(pd.isna(val) for val in [upper, middle, lower, position]))
        
        # 标准差倍数为0
        upper, middle, lower, position = BollingerBands.cal(5, 0.0, self.test_prices_5)
        self.assertTrue(all(pd.isna(val) for val in [upper, middle, lower, position]))
        
        # 负标准差倍数
        upper, middle, lower, position = BollingerBands.cal(5, -2.0, self.test_prices_5)
        self.assertTrue(all(pd.isna(val) for val in [upper, middle, lower, position]))
    
    def test_bollinger_bands_mathematical_properties(self):
        """测试布林带的数学特性"""
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, self.test_prices_5)
        
        # 验证标准差计算
        mean_price = sum(self.test_prices_5) / 5
        variance = sum((p - mean_price) ** 2 for p in self.test_prices_5) / 5
        std_dev = variance ** 0.5
        
        expected_upper = mean_price + 2.0 * std_dev
        expected_lower = mean_price - 2.0 * std_dev
        
        self.assertAlmostEqual(upper, expected_upper, places=6)
        self.assertAlmostEqual(lower, expected_lower, places=6)
        self.assertAlmostEqual(middle, mean_price, places=6)
    
    def test_bollinger_bands_position_edge_cases(self):
        """测试位置计算的边界情况"""
        # 价格恰好在上轨
        prices = [100.0, 100.0, 100.0, 100.0, 110.0]  # 最后价格跳跃
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices)
        
        # 位置应该接近1.0
        self.assertGreater(position, 0.8)
        
        # 价格恰好在下轨附近
        prices_low = [100.0, 100.0, 100.0, 100.0, 90.0]
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_low)
        
        # 位置应该接近0.0
        self.assertLess(position, 0.2)
    
    def test_bollinger_bands_vs_sma(self):
        """测试布林带中轨与SMA的一致性"""
        from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage
        
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, self.test_prices_5)
        sma_result = SimpleMovingAverage.cal(5, self.test_prices_5)
        
        # 中轨应该等于SMA
        self.assertAlmostEqual(middle, sma_result, places=6)
    
    def test_bollinger_bands_matrix_calculation(self):
        """测试布林带矩阵计算"""
        dates = pd.date_range('2023-01-01', periods=25)
        data = {
            'stock1': [100 + i*0.5 + np.random.normal(0, 1) for i in range(25)],
            'stock2': [200 + i*0.3 + np.random.normal(0, 0.5) for i in range(25)]
        }
        matrix = pd.DataFrame(data, index=dates)
        
        result = BollingerBands.cal_matrix(20, 2.0, matrix)
        
        # 检查结果维度
        self.assertEqual(result.shape, matrix.shape)
        
        # 布林带矩阵计算返回简化结果（中轨）
        self.assertFalse(result.empty)
    
    def test_bollinger_bands_extreme_values(self):
        """测试极值情况"""
        # 极小数值
        small_prices = [0.001, 0.002, 0.003, 0.004, 0.005]
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, small_prices)
        
        self.assertFalse(any(pd.isna(val) for val in [upper, middle, lower, position]))
        self.assertGreater(upper, middle)
        self.assertLess(lower, middle)
        
        # 极大数值
        large_prices = [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6]
        upper, middle, lower, position = BollingerBands.cal(5, 2.0, large_prices)
        
        self.assertFalse(any(pd.isna(val) for val in [upper, middle, lower, position]))
        self.assertGreater(upper, middle)
        self.assertLess(lower, middle)
    
    def test_bollinger_bands_realistic_scenario(self):
        """测试真实场景"""
        # 模拟股价趋势 + 随机波动
        np.random.seed(42)
        realistic_prices = []
        base_price = 100.0
        
        for i in range(20):
            # 添加趋势和随机波动
            trend = i * 0.2  # 轻微上升趋势
            noise = np.random.normal(0, 1)  # 随机波动
            price = base_price + trend + noise
            realistic_prices.append(price)
        
        upper, middle, lower, position = BollingerBands.cal(20, 2.0, realistic_prices)
        
        # 检查结果合理性
        self.assertFalse(any(pd.isna(val) for val in [upper, middle, lower, position]))
        self.assertGreater(upper, middle)
        self.assertLess(lower, middle)
        self.assertGreaterEqual(position, 0.0)
        self.assertLessEqual(position, 1.0)
        
        # 检查带宽合理性
        band_width = upper - lower
        self.assertGreater(band_width, 0)
        self.assertLess(band_width, 50)  # 不应该过度宽泛
    
    def test_bollinger_bands_performance(self):
        """测试性能"""
        import time
        
        large_prices = [100.0 + i*0.1 + np.random.normal(0, 0.5) for i in range(1000)]
        
        start_time = time.time()
        for _ in range(100):
            result = BollingerBands.cal(20, 2.0, large_prices[-20:])
        end_time = time.time()
        
        # 100次计算应该在1秒内完成
        self.assertLess(end_time - start_time, 1.0)
        self.assertFalse(any(pd.isna(val) for val in result))


if __name__ == '__main__':
    unittest.main(verbosity=2)