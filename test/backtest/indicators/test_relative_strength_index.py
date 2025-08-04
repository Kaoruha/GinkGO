#!/usr/bin/env python3
"""
Test cases for Relative Strength Index (RSI)
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ginkgo.backtest.computation.indicators.relative_strength_index import RelativeStrengthIndex


class TestRelativeStrengthIndex(unittest.TestCase):
    """测试相对强弱指数"""
    
    def setUp(self):
        """设置测试数据"""
        # RSI需要period+1个数据点
        self.test_prices_rsi14 = [100.0] + [100.0 + i for i in range(1, 15)]  # 15个数据点
        self.test_prices_rsi5 = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]   # 6个数据点
        
    def test_rsi_basic_calculation(self):
        """测试基本RSI计算"""
        # 使用递增价格，RSI应该接近100
        result = RelativeStrengthIndex.cal(14, self.test_prices_rsi14)
        
        # 所有变化都是正的，RSI应该很高
        self.assertGreater(result, 90)
        self.assertLessEqual(result, 100)
        self.assertFalse(pd.isna(result))
    
    def test_rsi_decreasing_prices(self):
        """测试下降价格的RSI"""
        # 创建下降价格序列
        decreasing_prices = [114.0] + [114.0 - i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, decreasing_prices)
        
        # 所有变化都是负的，RSI应该接近0
        self.assertLess(result, 10)
        self.assertGreaterEqual(result, 0)
    
    def test_rsi_no_change(self):
        """测试价格无变化的情况"""
        constant_prices = [100.0] * 15
        result = RelativeStrengthIndex.cal(14, constant_prices)
        
        # 价格无变化，RSI应该是50
        self.assertAlmostEqual(result, 50.0, places=1)
    
    def test_rsi_mixed_changes(self):
        """测试混合涨跌的情况"""
        # 交替上涨下跌
        mixed_prices = [100.0]
        for i in range(14):
            if i % 2 == 0:
                mixed_prices.append(mixed_prices[-1] + 1)
            else:
                mixed_prices.append(mixed_prices[-1] - 0.5)
        
        result = RelativeStrengthIndex.cal(14, mixed_prices)
        
        # 应该在30-70之间（中性区域）
        self.assertGreater(result, 30)
        self.assertLess(result, 70)
    
    def test_rsi_period_5(self):
        """测试周期为5的RSI"""
        result = RelativeStrengthIndex.cal(5, self.test_prices_rsi5)
        
        # 应该返回有效值
        self.assertFalse(pd.isna(result))
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 100)
    
    def test_rsi_wrong_length(self):
        """测试错误数据长度"""
        # 数据不足（需要period+1个数据）
        result = RelativeStrengthIndex.cal(14, [100.0, 101.0, 102.0])
        self.assertTrue(pd.isna(result))
        
        # 数据过多
        result = RelativeStrengthIndex.cal(5, self.test_prices_rsi14)
        self.assertTrue(pd.isna(result))
    
    def test_rsi_with_nan(self):
        """测试包含NaN的数据"""
        prices_with_nan = [100.0] + [100.0 + i if i != 7 else float('nan') for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, prices_with_nan)
        self.assertTrue(pd.isna(result))
    
    def test_rsi_zero_period(self):
        """测试周期为0"""
        result = RelativeStrengthIndex.cal(0, self.test_prices_rsi14)
        self.assertTrue(pd.isna(result))
    
    def test_rsi_negative_period(self):
        """测试负周期"""
        result = RelativeStrengthIndex.cal(-14, self.test_prices_rsi14)
        self.assertTrue(pd.isna(result))
    
    def test_rsi_extreme_gains(self):
        """测试极端上涨情况"""
        # 大幅上涨
        extreme_up_prices = [100.0] + [100.0 + i*10 for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, extreme_up_prices)
        
        # 应该接近100
        self.assertGreater(result, 95)
        self.assertLessEqual(result, 100)
    
    def test_rsi_extreme_losses(self):
        """测试极端下跌情况"""
        # 大幅下跌
        extreme_down_prices = [200.0] + [200.0 - i*10 for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, extreme_down_prices)
        
        # 应该接近0
        self.assertLess(result, 5)
        self.assertGreaterEqual(result, 0)
    
    def test_rsi_calculation_logic(self):
        """测试RSI计算逻辑的正确性"""
        # 使用已知数据验证计算
        prices = [100.0, 102.0, 101.0, 103.0, 102.0, 104.0]  # 5+1个数据
        result = RelativeStrengthIndex.cal(5, prices)
        
        # 手动计算验证
        price_diffs = [2.0, -1.0, 2.0, -1.0, 2.0]  # 价格变化
        gains = [2.0, 0.0, 2.0, 0.0, 2.0]         # 上涨
        losses = [0.0, 1.0, 0.0, 1.0, 0.0]        # 下跌
        
        avg_gain = sum(gains) / 5    # 1.2
        avg_loss = sum(losses) / 5   # 0.4
        
        rs = avg_gain / avg_loss     # 3.0
        expected_rsi = 100 - (100 / (1 + rs))  # 75.0
        
        self.assertAlmostEqual(result, expected_rsi, places=1)
    
    def test_rsi_boundary_values(self):
        """测试RSI边界值"""
        # 测试RSI永远在0-100之间
        test_cases = [
            [100.0] + [100.0 + i*0.1 for i in range(1, 15)],  # 小幅上涨
            [100.0] + [100.0 - i*0.1 for i in range(1, 15)],  # 小幅下跌
            [100.0] + [100.0 + (i%2)*2 - 1 for i in range(1, 15)],  # 锯齿形
        ]
        
        for prices in test_cases:
            result = RelativeStrengthIndex.cal(14, prices)
            self.assertGreaterEqual(result, 0, f"RSI should be >= 0, got {result}")
            self.assertLessEqual(result, 100, f"RSI should be <= 100, got {result}")
    
    def test_rsi_zero_average_loss(self):
        """测试平均损失为零的情况"""
        # 只有上涨，没有下跌
        only_gains = [100.0] + [100.0 + i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, only_gains)
        
        # 应该返回100或接近100
        self.assertGreater(result, 95)
        self.assertLessEqual(result, 100)
    
    def test_rsi_zero_average_gain(self):
        """测试平均收益为零的情况"""
        # 只有下跌，没有上涨
        only_losses = [114.0] + [114.0 - i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, only_losses)
        
        # 应该返回0或接近0
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 5)
    
    def test_rsi_matrix_calculation(self):
        """测试RSI矩阵计算"""
        # 创建长格式数据
        data = []
        stocks = ['STOCK_A', 'STOCK_B']
        dates = pd.date_range('2023-01-01', periods=20)
        
        for stock in stocks:
            base_price = 100.0
            for date in dates:
                data.append({
                    'code': stock,
                    'timestamp': date,
                    'close': base_price,
                    'volume': 1000
                })
                base_price += 1  # 每日上涨1元
        
        long_format_data = pd.DataFrame(data)
        result = RelativeStrengthIndex.cal_matrix(14, long_format_data)
        
        # 检查结果包含rsi列
        self.assertIn('rsi', result.columns)
        
        # 检查RSI值的有效性
        valid_rsi = result['rsi'].dropna()
        for rsi_val in valid_rsi:
            self.assertGreaterEqual(rsi_val, 0)
            self.assertLessEqual(rsi_val, 100)
    
    def test_rsi_performance(self):
        """测试RSI计算性能"""
        import time
        
        # 创建大量测试数据
        large_prices = [100.0]
        for i in range(499):  # 500个数据点
            change = (-1) ** i * (i % 5)  # 交替变化
            large_prices.append(large_prices[-1] + change)
        
        start_time = time.time()
        for _ in range(50):
            result = RelativeStrengthIndex.cal(14, large_prices[-15:])
        end_time = time.time()
        
        # 50次计算应该很快完成
        self.assertLess(end_time - start_time, 0.5)
        self.assertFalse(pd.isna(result))


if __name__ == '__main__':
    unittest.main(verbosity=2)