"""
ML策略单元测试

测试机器学习策略基类和具体实现的功能。
基于当前源码实际接口编写。
"""

import unittest
import pandas as pd
import numpy as np
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from ginkgo.trading.strategies.ml_strategy_base import MLStrategyBase
from ginkgo.trading.strategies.ml_predictor import StrategyMLPredictor
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES


def _make_test_data(n_days=100):
    """生成测试用 OHLCV 数据"""
    dates = pd.date_range(start="2023-01-01", periods=n_days, freq="D")
    np.random.seed(42)
    base_price = 100
    price_changes = np.random.normal(0, 0.01, n_days).cumsum()
    prices = base_price * np.exp(price_changes)

    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": prices * np.random.uniform(0.995, 1.005, n_days),
            "high": prices * np.random.uniform(1.000, 1.020, n_days),
            "low": prices * np.random.uniform(0.980, 1.000, n_days),
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, n_days),
        }
    )
    df["high"] = np.maximum(df[["open", "close"]].max(axis=1), df["high"])
    df["low"] = np.minimum(df[["open", "close"]].min(axis=1), df["low"])
    return df


class _MockModel:
    """模拟 ML 模型"""

    def __init__(self, name="MockModel"):
        self.name = name
        self.is_trained = True
        self._metadata = {"name": name, "model_type": "test", "feature_count": 10}

    def predict(self, X):
        return pd.DataFrame(
            np.random.normal(0, 0.02, (len(X), 1)), columns=["prediction"]
        )

    def get_metadata(self):
        return self._metadata.copy()

    @classmethod
    def load(cls, filepath, **kwargs):
        return cls()


class _MockFeatureProcessor:
    def __init__(self, **kwargs):
        self.is_fitted = True

    def transform(self, X):
        return X


class _MockAlphaFactors:
    def __init__(self, **kwargs):
        pass

    def calculate_all_factors(self, df):
        result = df.copy()
        if "close" in result.columns:
            result["ma_5"] = result["close"].rolling(5).mean()
            result["rsi_14"] = 50 + np.random.normal(0, 10, len(result))
            result["volatility"] = result["close"].pct_change().rolling(20).std()
        return result


# 统一 patch 目标：源码实际导入路径
ML_BASE_PATCHES = [
    patch("ginkgo.trading.strategies.ml_strategy_base.BaseModel", _MockModel),
    patch(
        "ginkgo.trading.strategies.ml_strategy_base.FeatureProcessor",
        _MockFeatureProcessor,
    ),
    patch(
        "ginkgo.trading.strategies.ml_strategy_base.AlphaFactors", _MockAlphaFactors
    ),
]


def _with_mocks(fn):
    """装饰器：为测试方法应用 ML 模块 mock"""

    def wrapper(self):
        with ML_BASE_PATCHES[0], ML_BASE_PATCHES[1], ML_BASE_PATCHES[2]:
            fn(self)

    wrapper.__name__ = fn.__name__
    return wrapper


class TestMLStrategyBase(unittest.TestCase):
    """测试 ML 策略基类"""

    def setUp(self):
        self.portfolio_info = {
            "uuid": "test_portfolio",
            "now": datetime.now(),
            "positions": {},
        }
        self.test_event = Mock(code="000001.SZ", timestamp=datetime.now())
        self.test_data = _make_test_data()

    @_with_mocks
    def test_initialization_defaults(self):
        """测试默认参数初始化"""
        strategy = MLStrategyBase()
        self.assertEqual(strategy.name, "MLStrategy")
        self.assertEqual(strategy._signal_threshold, 0.01)
        self.assertTrue(strategy._enable_monitoring)
        self.assertFalse(strategy.is_model_loaded())

    @_with_mocks
    def test_initialization_custom_params(self):
        """测试自定义参数初始化"""
        strategy = MLStrategyBase(
            name="CustomML",
            signal_threshold=0.05,
            lookback_days=120,
            enable_monitoring=False,
        )
        self.assertEqual(strategy.name, "CustomML")
        self.assertEqual(strategy._signal_threshold, 0.05)
        self.assertEqual(strategy._lookback_days, 120)
        self.assertFalse(strategy._enable_monitoring)

    @_with_mocks
    def test_model_loading_success(self):
        """测试模型成功加载"""
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            model_path = f.name

        try:
            strategy = MLStrategyBase(name="TestStrategy")
            result = strategy.load_model(model_path)
            self.assertTrue(result)
            self.assertTrue(strategy.is_model_loaded())
        finally:
            os.unlink(model_path)

    @_with_mocks
    def test_model_loading_nonexistent_path(self):
        """测试加载不存在的模型文件"""
        strategy = MLStrategyBase(name="TestStrategy")
        result = strategy.load_model("/nonexistent/model.pkl")
        self.assertFalse(result)
        self.assertFalse(strategy.is_model_loaded())

    @_with_mocks
    def test_get_model_info(self):
        """测试获取模型信息"""
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            model_path = f.name

        try:
            strategy = MLStrategyBase(name="TestStrategy")
            strategy.load_model(model_path)

            info = strategy.get_model_info()
            self.assertIn("name", info)
            self.assertIn("model_type", info)
            self.assertIn("feature_count", info)
        finally:
            os.unlink(model_path)

    @_with_mocks
    def test_predict_without_model(self):
        """测试未加载模型时预测返回 None"""
        strategy = MLStrategyBase(name="TestStrategy")
        features = pd.DataFrame(np.random.random((1, 10)))
        result = strategy.predict(features, "000001.SZ")
        self.assertIsNone(result)

    @_with_mocks
    def test_predict_with_model(self):
        """测试带模型的预测"""
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            model_path = f.name

        try:
            strategy = MLStrategyBase(name="TestStrategy")
            strategy.load_model(model_path)

            features = pd.DataFrame(
                np.random.random((1, 10)),
                columns=[f"feature_{i}" for i in range(10)],
            )
            result = strategy.predict(features, "000001.SZ")
            self.assertIsNotNone(result)
            self.assertIn("prediction", result)
            self.assertIn("confidence", result)
            self.assertIn("code", result)
            self.assertEqual(result["code"], "000001.SZ")
        finally:
            os.unlink(model_path)

    @_with_mocks
    def test_signal_generation_long(self):
        """测试生成买入信号"""
        strategy = MLStrategyBase(name="TestStrategy", signal_threshold=0.01)
        # 绑定 portfolio_id 等上下文，否则 Signal 初始化会失败
        mock_ctx = Mock(portfolio_id="test_portfolio", engine_id="test_engine", task_id="test_task")
        strategy._context = mock_ctx

        prediction_result = {
            "prediction": 0.05,
            "confidence": 0.8,
            "code": "000001.SZ",
        }
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        self.assertGreater(len(signals), 0)
        self.assertIsInstance(signals[0], Signal)
        self.assertEqual(signals[0].direction, DIRECTION_TYPES.LONG)

    @_with_mocks
    def test_signal_generation_below_threshold(self):
        """测试低于阈值不生成信号"""
        strategy = MLStrategyBase(name="TestStrategy", signal_threshold=0.1)
        prediction_result = {
            "prediction": 0.01,
            "confidence": 0.8,
            "code": "000001.SZ",
        }
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        self.assertEqual(len(signals), 0)

    @_with_mocks
    def test_performance_monitoring(self):
        """测试性能监控"""
        strategy = MLStrategyBase(name="TestStrategy", enable_monitoring=True)
        # 需要至少 20 条记录（含 actual_return）才能计算指标
        for i in range(25):
            strategy.update_performance_monitoring(
                "000001.SZ",
                np.random.normal(0, 0.02),
                np.random.normal(0, 0.02),
            )
        metrics = strategy.get_performance_metrics()
        self.assertIn("direction_accuracy", metrics)
        self.assertIn("information_coefficient", metrics)
        self.assertIn("prediction_count", metrics)

    @_with_mocks
    def test_performance_monitoring_disabled(self):
        """测试禁用监控时不记录"""
        strategy = MLStrategyBase(name="TestStrategy", enable_monitoring=False)
        strategy.update_performance_monitoring("000001.SZ", 0.01, 0.02)
        self.assertEqual(len(strategy._prediction_history), 0)

    @_with_mocks
    def test_extract_features_with_data(self):
        """测试传入数据时特征提取"""
        strategy = MLStrategyBase(name="TestStrategy")
        features = strategy.extract_features(
            "000001.SZ", datetime.now(), history_data=self.test_data
        )
        self.assertIsNotNone(features)
        self.assertIsInstance(features, pd.DataFrame)
        # AlphaFactors 应添加额外列
        self.assertGreater(features.shape[1], self.test_data.shape[1])

    @_with_mocks
    def test_extract_features_caching(self):
        """测试特征缓存"""
        strategy = MLStrategyBase(name="TestStrategy")
        dt = datetime(2023, 6, 1)
        # 第一次调用
        f1 = strategy.extract_features(
            "000001.SZ", dt, history_data=self.test_data
        )
        # 第二次调用（应命中缓存）
        f2 = strategy.extract_features(
            "000001.SZ", dt, history_data=self.test_data
        )
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)

    @_with_mocks
    def test_cal_method_no_model(self):
        """测试未加载模型时 cal 返回空列表"""
        strategy = MLStrategyBase(name="TestStrategy")
        signals = strategy.cal(self.portfolio_info, self.test_event)
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 0)

    @_with_mocks
    def test_cal_method_with_model(self):
        """测试 cal 主计算方法"""
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            model_path = f.name

        try:
            strategy = MLStrategyBase(name="TestStrategy", signal_threshold=0.01)
            strategy.load_model(model_path)

            # 绑定上下文，否则 Signal 初始化会失败
            mock_ctx = Mock(portfolio_id="test_portfolio", engine_id="test_engine", task_id="test_task")
            strategy._context = mock_ctx

            # mock data_feeder
            strategy._data_feeder = Mock()
            strategy._data_feeder.get_historical_data.return_value = self.test_data

            signals = strategy.cal(self.portfolio_info, self.test_event)
            self.assertIsInstance(signals, list)
        finally:
            os.unlink(model_path)

    @_with_mocks
    def test_set_signal_threshold(self):
        """测试动态修改信号阈值"""
        strategy = MLStrategyBase(name="TestStrategy")
        strategy.set_signal_threshold(0.05)
        self.assertEqual(strategy._signal_threshold, 0.05)

    @_with_mocks
    def test_strategy_summary(self):
        """测试策略摘要"""
        strategy = MLStrategyBase(name="TestStrategy")
        summary = strategy.get_strategy_summary()
        self.assertIn("name", summary)
        self.assertIn("model_loaded", summary)
        self.assertIn("signal_threshold", summary)
        self.assertIn("performance_metrics", summary)

    @_with_mocks
    def test_reload_model(self):
        """测试模型重载"""
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            model_path = f.name

        try:
            strategy = MLStrategyBase(name="TestStrategy", model_path=model_path)
            self.assertTrue(strategy.is_model_loaded())
            result = strategy.reload_model()
            self.assertTrue(result)
        finally:
            os.unlink(model_path)

    @_with_mocks
    def test_reload_model_no_path(self):
        """测试无路径时重载失败"""
        strategy = MLStrategyBase(name="TestStrategy")
        result = strategy.reload_model()
        self.assertFalse(result)


class TestStrategyMLPredictor(unittest.TestCase):
    """测试 ML 预测策略"""

    def setUp(self):
        self.portfolio_info = {
            "uuid": "test_portfolio",
            "now": datetime.now(),
            "positions": {},
        }

    @_with_mocks
    def test_initialization_defaults(self):
        """测试默认参数初始化"""
        strategy = StrategyMLPredictor()
        self.assertEqual(strategy.name, "MLPredictor")
        self.assertEqual(strategy._prediction_horizon, 5)
        self.assertEqual(strategy._confidence_threshold, 0.7)
        self.assertEqual(strategy._return_threshold, 0.02)

    @_with_mocks
    def test_initialization_custom_params(self):
        """测试自定义参数初始化"""
        strategy = StrategyMLPredictor(
            name="CustomPredictor",
            prediction_horizon=10,
            confidence_threshold=0.8,
            return_threshold=0.03,
        )
        self.assertEqual(strategy.name, "CustomPredictor")
        self.assertEqual(strategy._prediction_horizon, 10)
        self.assertEqual(strategy._confidence_threshold, 0.8)
        self.assertEqual(strategy._return_threshold, 0.03)

    @_with_mocks
    def test_signal_generation_high_confidence(self):
        """测试高置信度生成买入信号"""
        strategy = StrategyMLPredictor(
            name="TestPredictor",
            confidence_threshold=0.7,
            return_threshold=0.02,
        )
        mock_ctx = Mock(portfolio_id="test_portfolio", engine_id="test_engine", task_id="test_task")
        strategy._context = mock_ctx

        prediction_result = {
            "prediction": 0.05,
            "confidence": 0.9,
            "code": "000001.SZ",
        }
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        self.assertGreater(len(signals), 0)
        self.assertEqual(signals[0].direction, DIRECTION_TYPES.LONG)

    @_with_mocks
    def test_signal_generation_low_confidence(self):
        """测试低置信度不生成信号"""
        strategy = StrategyMLPredictor(
            name="TestPredictor",
            confidence_threshold=0.7,
            return_threshold=0.02,
        )
        prediction_result = {
            "prediction": 0.05,
            "confidence": 0.5,
            "code": "000001.SZ",
        }
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        self.assertEqual(len(signals), 0)

    @_with_mocks
    def test_signal_generation_below_return_threshold(self):
        """测试低于收益率阈值不生成信号"""
        strategy = StrategyMLPredictor(
            name="TestPredictor",
            confidence_threshold=0.5,
            return_threshold=0.05,
        )
        prediction_result = {
            "prediction": 0.02,
            "confidence": 0.9,
            "code": "000001.SZ",
        }
        signals = strategy.generate_signals_from_prediction(
            self.portfolio_info, "000001.SZ", prediction_result
        )
        self.assertEqual(len(signals), 0)

    @_with_mocks
    def test_short_signal_with_position(self):
        """测试持仓时生成卖出信号"""
        portfolio_with_position = self.portfolio_info.copy()
        portfolio_with_position["positions"] = {"000001.SZ": Mock()}

        strategy = StrategyMLPredictor(
            name="TestPredictor",
            confidence_threshold=0.5,
            return_threshold=0.02,
        )
        mock_ctx = Mock(portfolio_id="test_portfolio", engine_id="test_engine", task_id="test_task")
        strategy._context = mock_ctx

        prediction_result = {
            "prediction": -0.05,
            "confidence": 0.9,
            "code": "000001.SZ",
        }
        signals = strategy.generate_signals_from_prediction(
            portfolio_with_position, "000001.SZ", prediction_result
        )
        self.assertGreater(len(signals), 0)
        self.assertEqual(signals[0].direction, DIRECTION_TYPES.SHORT)

    @_with_mocks
    def test_strategy_summary(self):
        """测试策略摘要包含预测器特有字段"""
        strategy = StrategyMLPredictor(
            name="TestPredictor",
            prediction_horizon=5,
            confidence_threshold=0.8,
            return_threshold=0.02,
        )
        summary = strategy.get_strategy_summary()
        self.assertIn("name", summary)
        self.assertIn("prediction_horizon", summary)
        self.assertEqual(summary["prediction_horizon"], 5)
        self.assertIn("confidence_threshold", summary)
        self.assertEqual(summary["confidence_threshold"], 0.8)
        self.assertIn("return_threshold", summary)
        self.assertEqual(summary["return_threshold"], 0.02)
        self.assertIn("model_loaded", summary)

    @_with_mocks
    def test_str_representation(self):
        """测试字符串表示"""
        strategy = StrategyMLPredictor(name="TestPredictor")
        s = str(strategy)
        self.assertIn("TestPredictor", s)
        self.assertIn("MLPredictor", s)

    @_with_mocks
    def test_short_selling_not_allowed(self):
        """测试默认不允许做空"""
        strategy = StrategyMLPredictor(name="TestPredictor")
        self.assertFalse(strategy._is_short_selling_allowed())


class TestMLStrategyIntegration(unittest.TestCase):
    """测试 ML 策略集成"""

    def test_imports(self):
        """测试模块导入"""
        from ginkgo.trading.strategies import MLStrategyBase, StrategyMLPredictor

        self.assertIsNotNone(MLStrategyBase)
        self.assertIsNotNone(StrategyMLPredictor)

    def test_strategy_inheritance(self):
        """测试策略继承关系"""
        from ginkgo.trading.strategies import (
            MLStrategyBase,
            StrategyMLPredictor,
            BaseStrategy,
        )

        self.assertTrue(issubclass(MLStrategyBase, BaseStrategy))
        self.assertTrue(issubclass(StrategyMLPredictor, MLStrategyBase))


if __name__ == "__main__":
    unittest.main()
