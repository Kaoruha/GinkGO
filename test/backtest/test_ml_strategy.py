"""
ML策略单元测试

测试机器学习策略基类和具体实现的功能
"""

import unittest
import pandas as pd
import numpy as np
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 测试导入
try:
    from ginkgo.backtest.strategy.strategies.ml_strategy_base import StrategyMLBase
    from ginkgo.backtest.strategy.strategies.ml_predictor import StrategyMLPredictor
    from ginkgo.backtest.entities.signal import Signal
    from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
    ML_STRATEGIES_AVAILABLE = True
except ImportError as e:
    ML_STRATEGIES_AVAILABLE = False
    print(f"ML策略模块不可用: {e}")


class MockModel:
    """模拟ML模型用于测试"""
    
    def __init__(self, name="MockModel"):
        self.name = name
        self.is_trained = True
        self._metadata = {
            'name': name,
            'model_type': 'test',
            'feature_count': 10
        }
        
    def predict(self, X):
        # 返回模拟预测结果
        return pd.DataFrame(np.random.normal(0, 0.02, (len(X), 1)), columns=['prediction'])
    
    def get_metadata(self):
        return self._metadata.copy()
    
    @classmethod
    def load(cls, filepath):
        return cls()


class MockEvent:
    """模拟市场事件"""
    
    def __init__(self, code="000001.SZ", timestamp=None):
        self.code = code
        self.timestamp = timestamp or datetime.now()


class MockFeatureProcessor:
    """模拟特征处理器"""
    
    def __init__(self):
        self.is_fitted = True
        
    def transform(self, X):
        return X


class MockAlphaFactors:
    """模拟Alpha因子计算器"""
    
    def calculate_all_factors(self, df):
        # 添加一些模拟因子
        result = df.copy()
        result['ma_5'] = result['close'].rolling(5).mean()
        result['rsi_14'] = 50 + np.random.normal(0, 10, len(result))
        result['volatility'] = result['close'].pct_change().rolling(20).std()
        return result


@unittest.skipIf(not ML_STRATEGIES_AVAILABLE, "ML策略模块不可用")
class TestStrategyMLBase(unittest.TestCase):
    """测试ML策略基类"""
    
    def setUp(self):
        """设置测试环境"""
        self.portfolio_info = {
            "uuid": "test_portfolio",
            "now": datetime.now(),
            "positions": {}
        }
        
        self.test_event = MockEvent()
        
        # 创建测试数据
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        n_samples = len(dates)
        
        base_price = 100
        price_changes = np.random.normal(0, 0.01, n_samples).cumsum()
        prices = base_price * np.exp(price_changes)
        
        self.test_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * np.random.uniform(0.995, 1.005, n_samples),
            'high': prices * np.random.uniform(1.000, 1.020, n_samples),
            'low': prices * np.random.uniform(0.980, 1.000, n_samples),
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, n_samples)
        })
        
        # 确保价格逻辑正确
        self.test_data['high'] = np.maximum(
            self.test_data[['open', 'close']].max(axis=1), 
            self.test_data['high']
        )
        self.test_data['low'] = np.minimum(
            self.test_data[['open', 'close']].min(axis=1), 
            self.test_data['low']
        )

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    def test_ml_strategy_initialization(self):
        """测试ML策略初始化"""
        strategy = StrategyMLBase(
            name="TestMLStrategy",
            signal_threshold=0.02,
            enable_monitoring=True
        )
        
        self.assertEqual(strategy.name, "TestMLStrategy")
        self.assertEqual(strategy._signal_threshold, 0.02)
        self.assertTrue(strategy._enable_monitoring)
        self.assertFalse(strategy.is_model_loaded())

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)  
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    @patch('os.path.exists')
    def test_model_loading(self, mock_exists):
        """测试模型加载"""
        mock_exists.return_value = True
        
        strategy = StrategyMLBase(name="TestStrategy")
        
        # 测试成功加载
        result = strategy.load_model("test_model.pkl")
        self.assertTrue(result)
        self.assertTrue(strategy.is_model_loaded())
        
        # 测试获取模型信息
        model_info = strategy.get_model_info()
        self.assertIn('name', model_info)
        self.assertIn('model_type', model_info)

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    @patch('ginkgo.data.get_bars')
    def test_feature_extraction(self, mock_get_bars):
        """测试特征提取"""
        mock_get_bars.return_value = self.test_data
        
        strategy = StrategyMLBase(name="TestStrategy")
        
        # 测试特征提取
        features = strategy.extract_features("000001.SZ", datetime.now())
        
        self.assertIsNotNone(features)
        self.assertIsInstance(features, pd.DataFrame)
        self.assertGreater(features.shape[1], self.test_data.shape[1])  # 应该有更多特征

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    @patch('os.path.exists')
    def test_prediction(self, mock_exists):
        """测试预测功能"""
        mock_exists.return_value = True
        
        strategy = StrategyMLBase(name="TestStrategy")
        strategy.load_model("test_model.pkl")
        
        # 创建测试特征数据
        features = pd.DataFrame(np.random.random((1, 10)), columns=[f'feature_{i}' for i in range(10)])
        
        # 测试预测
        result = strategy.predict(features, "000001.SZ")
        
        self.assertIsNotNone(result)
        self.assertIn('prediction', result)
        self.assertIn('confidence', result)
        self.assertIn('code', result)

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    @patch('os.path.exists')
    def test_signal_generation(self, mock_exists):
        """测试信号生成"""
        mock_exists.return_value = True
        
        strategy = StrategyMLBase(name="TestStrategy", signal_threshold=0.01)
        strategy.load_model("test_model.pkl")
        
        # 测试买入信号
        prediction_result = {
            'prediction': 0.05,  # 5% 预测收益
            'confidence': 0.8,
            'code': '000001.SZ'
        }
        
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        
        self.assertGreater(len(signals), 0)
        self.assertIsInstance(signals[0], Signal)
        self.assertEqual(signals[0].direction, DIRECTION_TYPES.LONG)

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    def test_performance_monitoring(self):
        """测试性能监控"""
        strategy = StrategyMLBase(name="TestStrategy", enable_monitoring=True)
        
        # 添加一些预测历史
        for i in range(25):
            strategy.update_performance_monitoring(
                "000001.SZ", 
                np.random.normal(0, 0.02),
                np.random.normal(0, 0.02)
            )
        
        metrics = strategy.get_performance_metrics()
        
        self.assertIn('direction_accuracy', metrics)
        self.assertIn('information_coefficient', metrics)
        self.assertIn('prediction_count', metrics)

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    @patch('ginkgo.data.get_bars')
    @patch('os.path.exists')
    def test_cal_method(self, mock_exists, mock_get_bars):
        """测试主计算方法"""
        mock_exists.return_value = True
        mock_get_bars.return_value = self.test_data
        
        strategy = StrategyMLBase(name="TestStrategy")
        strategy.load_model("test_model.pkl")
        
        # 测试事件驱动计算
        signals = strategy.cal(self.portfolio_info, self.test_event)
        
        self.assertIsInstance(signals, list)
        # 由于是随机预测，不一定有信号，但不应该出错


@unittest.skipIf(not ML_STRATEGIES_AVAILABLE, "ML策略模块不可用")
class TestStrategyMLPredictor(unittest.TestCase):
    """测试ML预测策略"""
    
    def setUp(self):
        """设置测试环境"""
        self.portfolio_info = {
            "uuid": "test_portfolio",
            "now": datetime.now(),
            "positions": {}
        }
        
        self.test_event = MockEvent()

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    def test_ml_predictor_initialization(self):
        """测试ML预测策略初始化"""
        strategy = StrategyMLPredictor(
            name="TestMLPredictor",
            prediction_horizon=10,
            confidence_threshold=0.8,
            return_threshold=0.03,
            risk_management=True
        )
        
        self.assertEqual(strategy.name, "TestMLPredictor")
        self.assertEqual(strategy._prediction_horizon, 10)
        self.assertEqual(strategy._confidence_threshold, 0.8)
        self.assertEqual(strategy._return_threshold, 0.03)
        self.assertTrue(strategy._risk_management)

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    def test_signal_generation_with_thresholds(self):
        """测试带阈值的信号生成"""
        strategy = StrategyMLPredictor(
            name="TestPredictor",
            confidence_threshold=0.7,
            return_threshold=0.02
        )
        
        # 测试高置信度、高收益预测
        prediction_result = {
            'prediction': 0.05,  # 5% 预测收益
            'confidence': 0.9,   # 90% 置信度
            'code': '000001.SZ'
        }
        
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        
        self.assertGreater(len(signals), 0)
        self.assertEqual(signals[0].direction, DIRECTION_TYPES.LONG)
        
        # 测试低置信度情况
        prediction_result['confidence'] = 0.5
        
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        
        self.assertEqual(len(signals), 0)  # 应该没有信号

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    def test_risk_management(self):
        """测试风险管理"""
        strategy = StrategyMLPredictor(
            name="TestPredictor",
            risk_management=True,
            stop_loss_ratio=0.05,
            take_profit_ratio=0.10
        )
        
        # 模拟持仓情况
        strategy._entry_prices["000001.SZ"] = 100.0
        strategy._position_directions["000001.SZ"] = DIRECTION_TYPES.LONG
        
        # 创建包含当前价格的投资组合信息
        portfolio_with_position = self.portfolio_info.copy()
        portfolio_with_position["positions"] = {
            "000001.SZ": Mock(price=95.0, cost=100.0)  # 5% 亏损
        }
        
        # 测试止损
        risk_signals = strategy._check_risk_management(portfolio_with_position, "000001.SZ")
        
        self.assertGreater(len(risk_signals), 0)
        self.assertEqual(risk_signals[0].direction, DIRECTION_TYPES.SHORT)
        self.assertIn("STOP_LOSS", risk_signals[0].reason)

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    def test_position_tracking(self):
        """测试持仓跟踪"""
        strategy = StrategyMLPredictor(name="TestPredictor")
        
        # 模拟进场
        strategy._entry_prices["000001.SZ"] = 100.0
        strategy._entry_times["000001.SZ"] = datetime.now() - timedelta(days=5)
        strategy._position_directions["000001.SZ"] = DIRECTION_TYPES.LONG
        
        # 获取持仓信息
        position_info = strategy.get_position_info()
        
        self.assertIn("000001.SZ", position_info)
        self.assertEqual(position_info["000001.SZ"]["entry_price"], 100.0)
        self.assertEqual(position_info["000001.SZ"]["direction"], DIRECTION_TYPES.LONG)
        self.assertGreaterEqual(position_info["000001.SZ"]["duration"], 5)

    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel', MockModel)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.FeatureProcessor', MockFeatureProcessor)
    @patch('ginkgo.backtest.strategy.strategies.ml_strategy_base.AlphaFactors', MockAlphaFactors)
    def test_strategy_summary(self):
        """测试策略摘要"""
        strategy = StrategyMLPredictor(
            name="TestPredictor",
            prediction_horizon=5,
            confidence_threshold=0.8,
            return_threshold=0.02
        )
        
        summary = strategy.get_strategy_summary()
        
        self.assertIn('name', summary)
        self.assertIn('prediction_horizon', summary)
        self.assertIn('confidence_threshold', summary)
        self.assertIn('return_threshold', summary)
        self.assertIn('model_loaded', summary)
        self.assertIn('active_positions', summary)


class TestMLStrategyIntegration(unittest.TestCase):
    """测试ML策略集成"""
    
    def test_imports(self):
        """测试模块导入"""
        try:
            from ginkgo.backtest.strategy.strategies import ML_STRATEGIES_AVAILABLE
            if ML_STRATEGIES_AVAILABLE:
                from ginkgo.backtest.strategy.strategies import StrategyMLBase, StrategyMLPredictor
                self.assertIsNotNone(StrategyMLBase)
                self.assertIsNotNone(StrategyMLPredictor)
            else:
                self.skipTest("ML策略模块不可用")
        except ImportError:
            self.skipTest("策略模块导入失败")

    def test_strategy_inheritance(self):
        """测试策略继承关系"""
        if ML_STRATEGIES_AVAILABLE:
            from ginkgo.backtest.strategy.strategies import StrategyMLBase, StrategyMLPredictor, StrategyBase
            
            # 检查继承关系
            self.assertTrue(issubclass(StrategyMLBase, StrategyBase))
            self.assertTrue(issubclass(StrategyMLPredictor, StrategyMLBase))


if __name__ == '__main__':
    unittest.main()