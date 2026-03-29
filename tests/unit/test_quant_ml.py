"""
机器学习模块单元测试
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

# 测试模型导入
try:
    from ginkgo.quant_ml.models.lightgbm import LightGBMModel
    from ginkgo.quant_ml.models.xgboost import XGBoostModel
    from ginkgo.quant_ml.models.sklearn import RandomForestModel, LinearModel
    from ginkgo.quant_ml.features import FeatureProcessor, AlphaFactors
    from ginkgo.quant_ml.containers import create_model, MODEL_TYPE_MAPPING
    ML_MODULES_AVAILABLE = True
except ImportError as e:
    ML_MODULES_AVAILABLE = False
    print(f"ML模块不可用: {e}")


@unittest.skipIf(not ML_MODULES_AVAILABLE, "机器学习模块不可用")
class TestMLModels(unittest.TestCase):
    """测试机器学习模型"""
    
    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        
        # 创建模拟的OHLCV数据
        dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
        n_samples = len(dates)
        
        # 模拟价格数据
        base_price = 100
        price_changes = np.random.normal(0, 0.02, n_samples).cumsum()
        prices = base_price * np.exp(price_changes)
        
        self.test_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * np.random.uniform(0.98, 1.02, n_samples),
            'high': prices * np.random.uniform(1.00, 1.05, n_samples),
            'low': prices * np.random.uniform(0.95, 1.00, n_samples),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, n_samples)
        })
        
        # 确保高低价格合理
        self.test_data['high'] = np.maximum(self.test_data[['open', 'close', 'high']].max(axis=1), self.test_data['high'])
        self.test_data['low'] = np.minimum(self.test_data[['open', 'close', 'low']].min(axis=1), self.test_data['low'])
        
        # 创建特征和目标变量
        self.X = pd.DataFrame(np.random.random((100, 10)), columns=[f'feature_{i}' for i in range(10)])
        self.y = pd.DataFrame(np.random.random((100, 1)), columns=['target'])
    
    def test_lightgbm_model(self):
        """测试LightGBM模型"""
        try:
            model = LightGBMModel(name="TestLGB", task="regression")
            
            # 测试初始状态
            self.assertFalse(model.is_trained)
            self.assertEqual(model.name, "TestLGB")
            
            # 测试训练
            model.fit(self.X, self.y)
            self.assertTrue(model.is_trained)
            
            # 测试预测
            predictions = model.predict(self.X.head(10))
            self.assertIsInstance(predictions, pd.DataFrame)
            self.assertEqual(len(predictions), 10)
            
            # 测试特征重要性
            importance = model.get_feature_importance()
            self.assertIsInstance(importance, pd.Series)
            self.assertEqual(len(importance), 10)
            
        except ImportError:
            self.skipTest("LightGBM不可用")
    
    def test_xgboost_model(self):
        """测试XGBoost模型"""
        try:
            model = XGBoostModel(name="TestXGB", task="regression")
            
            # 测试初始状态
            self.assertFalse(model.is_trained)
            
            # 测试训练
            model.fit(self.X, self.y)
            self.assertTrue(model.is_trained)
            
            # 测试预测
            predictions = model.predict(self.X.head(10))
            self.assertIsInstance(predictions, pd.DataFrame)
            self.assertEqual(len(predictions), 10)
            
        except ImportError:
            self.skipTest("XGBoost不可用")
    
    def test_random_forest_model(self):
        """测试随机森林模型"""
        try:
            model = RandomForestModel(name="TestRF", task="regression", n_estimators=50)
            
            # 测试训练
            model.fit(self.X, self.y)
            self.assertTrue(model.is_trained)
            
            # 测试预测
            predictions = model.predict(self.X.head(10))
            self.assertIsInstance(predictions, pd.DataFrame)
            
            # 测试特征重要性
            importance = model.get_feature_importance()
            self.assertIsInstance(importance, pd.Series)
            
        except ImportError:
            self.skipTest("scikit-learn不可用")
    
    def test_model_factory(self):
        """测试模型工厂"""
        # 测试模型创建
        for model_type in MODEL_TYPE_MAPPING.keys():
            try:
                model = create_model(model_type)
                self.assertIsNotNone(model)
                self.assertFalse(model.is_trained)
            except ImportError:
                # 如果依赖库不可用，跳过
                continue
    
    def test_model_save_load(self):
        """测试模型保存和加载"""
        try:
            model = RandomForestModel(name="TestSaveLoad", n_estimators=10)
            model.fit(self.X, self.y)
            
            # 保存模型
            with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
                temp_path = f.name
            
            try:
                model.save(temp_path)
                self.assertTrue(os.path.exists(temp_path))
                
                # 加载模型
                loaded_model = RandomForestModel.load(temp_path)
                self.assertTrue(loaded_model.is_trained)
                
                # 测试预测结果一致性
                original_pred = model.predict(self.X.head(5))
                loaded_pred = loaded_model.predict(self.X.head(5))
                
                np.testing.assert_array_almost_equal(
                    original_pred.values, loaded_pred.values, decimal=5
                )
                
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except ImportError:
            self.skipTest("scikit-learn不可用")


@unittest.skipIf(not ML_MODULES_AVAILABLE, "机器学习模块不可用")
class TestFeatureProcessor(unittest.TestCase):
    """测试特征处理器"""
    
    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        
        # 创建测试数据
        self.X = pd.DataFrame({
            'feature_1': np.random.normal(0, 1, 100),
            'feature_2': np.random.normal(5, 2, 100),
            'feature_3': np.random.uniform(-1, 1, 100)
        })
        
        # 添加一些缺失值
        self.X.loc[5:10, 'feature_1'] = np.nan
        
        self.y = pd.DataFrame(np.random.random((100, 1)), columns=['target'])
    
    def test_feature_processor_init(self):
        """测试特征处理器初始化"""
        try:
            processor = FeatureProcessor(
                scaling_method="standard",
                imputation_method="mean"
            )
            self.assertFalse(processor.is_fitted)
            self.assertEqual(processor.scaling_method, "standard")
            
        except ImportError:
            self.skipTest("scikit-learn不可用")
    
    def test_feature_processing_pipeline(self):
        """测试特征处理流水线"""
        try:
            processor = FeatureProcessor(
                scaling_method="standard",
                imputation_method="mean"
            )
            
            # 拟合和转换
            X_processed = processor.fit_transform(self.X, self.y)
            
            self.assertTrue(processor.is_fitted)
            self.assertEqual(X_processed.shape, self.X.shape)
            
            # 检查是否没有缺失值
            self.assertFalse(X_processed.isnull().any().any())
            
            # 检查标准化效果（均值接近0，标准差接近1）
            means = X_processed.mean()
            stds = X_processed.std()
            
            for mean in means:
                self.assertAlmostEqual(mean, 0, places=1)
            for std in stds:
                self.assertAlmostEqual(std, 1, places=1)
                
        except ImportError:
            self.skipTest("scikit-learn不可用")


@unittest.skipIf(not ML_MODULES_AVAILABLE, "机器学习模块不可用")  
class TestAlphaFactors(unittest.TestCase):
    """测试Alpha因子计算"""
    
    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        
        # 创建模拟的OHLCV数据
        dates = pd.date_range(start='2023-01-01', end='2023-03-31', freq='D')
        n_samples = len(dates)
        
        # 模拟价格数据
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
        self.test_data['high'] = np.maximum(self.test_data[['open', 'close']].max(axis=1), self.test_data['high'])
        self.test_data['low'] = np.minimum(self.test_data[['open', 'close']].min(axis=1), self.test_data['low'])
    
    def test_alpha_factors_init(self):
        """测试Alpha因子计算器初始化"""
        factors = AlphaFactors()
        self.assertIsInstance(factors, AlphaFactors)
    
    def test_basic_factors(self):
        """测试基础因子计算"""
        factors = AlphaFactors()
        result = factors.calculate_basic_factors(self.test_data)
        
        # 检查是否添加了新列
        self.assertGreater(len(result.columns), len(self.test_data.columns))
        
        # 检查特定因子
        expected_factors = ['price_range', 'returns_1d', 'volume_ratio']
        for factor in expected_factors:
            self.assertIn(factor, result.columns)
        
        # 检查数值范围合理性
        self.assertTrue((result['price_range'] >= 0).all())  # 价格幅度应为非负
    
    def test_technical_indicators(self):
        """测试技术指标计算"""
        factors = AlphaFactors()
        result = factors.calculate_technical_indicators(self.test_data)
        
        # 检查移动平均线
        expected_ma = ['ma_5', 'ma_10', 'ma_20']
        for ma in expected_ma:
            self.assertIn(ma, result.columns)
        
        # 检查RSI
        self.assertIn('rsi_14', result.columns)
        if 'rsi_14' in result.columns:
            rsi_values = result['rsi_14'].dropna()
            if len(rsi_values) > 0:
                self.assertTrue((rsi_values >= 0).all())
                self.assertTrue((rsi_values <= 100).all())
    
    def test_all_factors(self):
        """测试全部因子计算"""
        factors = AlphaFactors()
        result = factors.calculate_all_factors(self.test_data)
        
        # 应该添加很多因子
        self.assertGreater(len(result.columns), len(self.test_data.columns) + 20)
        
        # 检查没有无穷值
        for col in result.select_dtypes(include=[np.number]).columns:
            self.assertFalse(np.isinf(result[col]).any())
    
    def test_factor_groups(self):
        """测试因子分组"""
        factors = AlphaFactors()
        groups = factors.get_factor_groups()
        
        self.assertIsInstance(groups, dict)
        self.assertIn('basic', groups)
        self.assertIn('technical', groups)
        self.assertIn('volatility', groups)
        
        # 每个组都应该有因子
        for group_name, factor_list in groups.items():
            self.assertIsInstance(factor_list, list)
            self.assertGreater(len(factor_list), 0)


class TestMLIntegration(unittest.TestCase):
    """测试ML模块集成"""
    
    def test_imports(self):
        """测试模块导入"""
        try:
            from ginkgo.quant_ml import ml_container
            self.assertIsNotNone(ml_container)
        except ImportError:
            self.skipTest("ML容器不可用")
    
    def test_container_model_creation(self):
        """测试容器模型创建"""
        try:
            from ginkgo.quant_ml.containers import MODEL_TYPE_MAPPING
            self.assertGreater(len(MODEL_TYPE_MAPPING), 0)
            
            # 检查基本模型类型
            expected_types = ["lightgbm", "xgboost", "random_forest"]
            for model_type in expected_types:
                self.assertIn(model_type, MODEL_TYPE_MAPPING)
                
        except ImportError:
            self.skipTest("ML容器不可用")


if __name__ == '__main__':
    unittest.main()