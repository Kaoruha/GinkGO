"""
模型适配器

提供不同ML模型框架的统一适配能力，支持sklearn、pytorch、tensorflow等模型的统一接口。
"""

from typing import Dict, Any, List, Type, Optional, Union
import pandas as pd
import numpy as np

from .base_adapter import BaseAdapter, AdapterError
from ginkgo.core.interfaces.model_interface import IModel
from ginkgo.enums import MODEL_TYPES
from ginkgo.libs import GLOG


class ModelAdapter(BaseAdapter):
    """ML模型适配器"""
    
    def __init__(self, name: str = "ModelAdapter"):
        super().__init__(name)
        self._framework_adapters = {
            'sklearn': SklearnModelAdapter,
            'pytorch': PyTorchModelAdapter,
            'tensorflow': TensorFlowModelAdapter,
            'xgboost': XGBoostModelAdapter,
            'lightgbm': LightGBMModelAdapter
        }
    
    def can_adapt(self, source: Any, target_type: Type = None) -> bool:
        """检查是否可以适配"""
        # 检查是否为已知的ML模型类型
        source_type = type(source).__module__
        
        if 'sklearn' in source_type:
            return True
        elif 'torch' in source_type or 'pytorch' in source_type:
            return True
        elif 'tensorflow' in source_type or 'keras' in source_type:
            return True
        elif 'xgboost' in source_type:
            return True
        elif 'lightgbm' in source_type:
            return True
        elif isinstance(source, IModel):
            return True
        
        return False
    
    def adapt(self, source: Any, target_type: Type = None, **kwargs) -> IModel:
        """
        模型适配主方法
        
        Args:
            source: 源模型对象
            target_type: 目标模型接口类型
            **kwargs: 适配参数
            
        Returns:
            IModel: 适配后的模型对象
        """
        if not self.can_adapt(source, target_type):
            raise AdapterError(f"无法适配模型: {type(source).__name__}")
        
        try:
            # 如果已经是IModel接口，直接返回
            if isinstance(source, IModel):
                return source
            
            # 检测模型框架并选择适配器
            framework = self._detect_framework(source)
            if framework in self._framework_adapters:
                adapter_class = self._framework_adapters[framework]
                adapter = adapter_class()
                return adapter.adapt(source, **kwargs)
            else:
                # 使用通用适配器
                return GenericModelAdapter(source, **kwargs)
                
        except Exception as e:
            raise AdapterError(f"模型适配失败: {e}")
    
    def _detect_framework(self, model: Any) -> str:
        """检测模型框架"""
        model_type = type(model).__module__
        
        if 'sklearn' in model_type:
            return 'sklearn'
        elif 'torch' in model_type or 'pytorch' in model_type:
            return 'pytorch'
        elif 'tensorflow' in model_type or 'keras' in model_type:
            return 'tensorflow'
        elif 'xgboost' in model_type:
            return 'xgboost'
        elif 'lightgbm' in model_type:
            return 'lightgbm'
        else:
            return 'generic'
    
    def register_framework_adapter(self, framework: str, adapter_class: Type) -> None:
        """注册框架适配器"""
        self._framework_adapters[framework] = adapter_class


class SklearnModelAdapter(IModel):
    """Sklearn模型适配器"""
    
    def __init__(self, sklearn_model: Any = None, name: str = "SklearnModel"):
        super().__init__(name, MODEL_TYPES.TABULAR)
        self.sklearn_model = sklearn_model
        
        if sklearn_model:
            # 从sklearn模型中提取信息
            self.name = f"Sklearn{type(sklearn_model).__name__}"
            if hasattr(sklearn_model, 'get_params'):
                self._hyperparameters = sklearn_model.get_params()
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'SklearnModelAdapter':
        """训练模型"""
        if self.sklearn_model is None:
            raise ValueError("sklearn模型未设置")
        
        try:
            # 记录特征名称
            self._feature_names = list(X.columns)
            if y is not None:
                self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # 训练模型
            if y is not None:
                self.sklearn_model.fit(X, y)
            else:
                # 无监督学习
                self.sklearn_model.fit(X)
            
            # 更新状态
            self.update_status(self.ModelStatus.TRAINED)
            
            return self
            
        except Exception as e:
            self.update_status(self.ModelStatus.UNTRAINED)
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> Union[pd.DataFrame, np.ndarray]:
        """预测"""
        if not self.is_trained:
            raise RuntimeError("模型未训练")
        
        predictions = self.sklearn_model.predict(X)
        
        # 转换为DataFrame
        if isinstance(predictions, np.ndarray):
            if predictions.ndim == 1:
                return pd.DataFrame(predictions, index=X.index, columns=['prediction'])
            else:
                columns = [f'prediction_{i}' for i in range(predictions.shape[1])]
                return pd.DataFrame(predictions, index=X.index, columns=columns)
        
        return predictions
    
    def predict_proba(self, X: pd.DataFrame, **kwargs) -> Union[pd.DataFrame, np.ndarray]:
        """预测概率"""
        if not hasattr(self.sklearn_model, 'predict_proba'):
            raise NotImplementedError("模型不支持概率预测")
        
        probabilities = self.sklearn_model.predict_proba(X)
        
        # 转换为DataFrame
        if hasattr(self.sklearn_model, 'classes_'):
            columns = [f'prob_{cls}' for cls in self.sklearn_model.classes_]
        else:
            columns = [f'prob_{i}' for i in range(probabilities.shape[1])]
        
        return pd.DataFrame(probabilities, index=X.index, columns=columns)
    
    def score(self, X: pd.DataFrame, y: pd.DataFrame, **kwargs) -> float:
        """评分"""
        return self.sklearn_model.score(X, y)
    
    def get_feature_importance(self) -> Optional[pd.Series]:
        """获取特征重要性"""
        if hasattr(self.sklearn_model, 'feature_importances_'):
            return pd.Series(
                self.sklearn_model.feature_importances_,
                index=self._feature_names,
                name='importance'
            )
        elif hasattr(self.sklearn_model, 'coef_'):
            # 线性模型的系数
            coef = self.sklearn_model.coef_
            if coef.ndim > 1:
                coef = np.abs(coef).mean(axis=0)
            return pd.Series(
                np.abs(coef),
                index=self._feature_names,
                name='importance'
            )
        
        return None
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        
        if self.sklearn_model:
            # 更新sklearn模型参数
            self.sklearn_model.set_params(**hyperparams)


class XGBoostModelAdapter(IModel):
    """XGBoost模型适配器"""
    
    def __init__(self, xgb_model: Any = None, name: str = "XGBoostModel"):
        super().__init__(name, MODEL_TYPES.TABULAR)
        self.xgb_model = xgb_model
        
        if xgb_model:
            self.name = f"XGBoost{type(xgb_model).__name__}"
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'XGBoostModelAdapter':
        """训练模型"""
        if self.xgb_model is None:
            raise ValueError("XGBoost模型未设置")
        
        try:
            self._feature_names = list(X.columns)
            if y is not None:
                self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # XGBoost训练
            eval_set = kwargs.get('eval_set', [(X, y)] if y is not None else None)
            verbose = kwargs.get('verbose', False)
            
            self.xgb_model.fit(X, y, eval_set=eval_set, verbose=verbose)
            
            self.update_status(self.ModelStatus.TRAINED)
            return self
            
        except Exception as e:
            self.update_status(self.ModelStatus.UNTRAINED)
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测"""
        if not self.is_trained:
            raise RuntimeError("模型未训练")
        
        predictions = self.xgb_model.predict(X)
        return pd.DataFrame(predictions, index=X.index, columns=['prediction'])
    
    def get_feature_importance(self) -> Optional[pd.Series]:
        """获取特征重要性"""
        if hasattr(self.xgb_model, 'feature_importances_'):
            return pd.Series(
                self.xgb_model.feature_importances_,
                index=self._feature_names,
                name='importance'
            )
        return None
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        
        if self.xgb_model:
            # 更新XGBoost参数
            for key, value in hyperparams.items():
                if hasattr(self.xgb_model, key):
                    setattr(self.xgb_model, key, value)


class LightGBMModelAdapter(IModel):
    """LightGBM模型适配器"""
    
    def __init__(self, lgb_model: Any = None, name: str = "LightGBMModel"):
        super().__init__(name, MODEL_TYPES.TABULAR)
        self.lgb_model = lgb_model
        
        if lgb_model:
            self.name = f"LightGBM{type(lgb_model).__name__}"
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'LightGBMModelAdapter':
        """训练模型"""
        if self.lgb_model is None:
            raise ValueError("LightGBM模型未设置")
        
        try:
            self._feature_names = list(X.columns)
            if y is not None:
                self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # LightGBM训练
            eval_set = kwargs.get('eval_set', [(X, y)] if y is not None else None)
            verbose = kwargs.get('verbose', False)
            
            self.lgb_model.fit(X, y, eval_set=eval_set, verbose=verbose)
            
            self.update_status(self.ModelStatus.TRAINED)
            return self
            
        except Exception as e:
            self.update_status(self.ModelStatus.UNTRAINED)
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测"""
        if not self.is_trained:
            raise RuntimeError("模型未训练")
        
        predictions = self.lgb_model.predict(X)
        return pd.DataFrame(predictions, index=X.index, columns=['prediction'])
    
    def get_feature_importance(self) -> Optional[pd.Series]:
        """获取特征重要性"""
        if hasattr(self.lgb_model, 'feature_importances_'):
            return pd.Series(
                self.lgb_model.feature_importances_,
                index=self._feature_names,
                name='importance'
            )
        return None
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)


class PyTorchModelAdapter(IModel):
    """PyTorch模型适配器"""
    
    def __init__(self, torch_model: Any = None, name: str = "PyTorchModel"):
        super().__init__(name, MODEL_TYPES.DEEP_LEARNING)
        self.torch_model = torch_model
        self.device = 'cpu'  # 默认使用CPU
        
        if torch_model:
            self.name = f"PyTorch{type(torch_model).__name__}"
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'PyTorchModelAdapter':
        """训练模型"""
        if self.torch_model is None:
            raise ValueError("PyTorch模型未设置")
        
        # PyTorch训练需要更复杂的实现，这里提供基础框架
        try:
            import torch
            
            self._feature_names = list(X.columns)
            if y is not None:
                self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # 转换数据为张量
            X_tensor = torch.tensor(X.values, dtype=torch.float32).to(self.device)
            if y is not None:
                y_tensor = torch.tensor(y.values, dtype=torch.float32).to(self.device)
            
            # 这里需要实现具体的训练逻辑
            # 包括优化器、损失函数、训练循环等
            GLOG.INFO("PyTorch模型训练需要自定义实现")
            
            self.update_status(self.ModelStatus.TRAINED)
            return self
            
        except ImportError:
            raise AdapterError("PyTorch未安装")
        except Exception as e:
            self.update_status(self.ModelStatus.UNTRAINED)
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测"""
        if not self.is_trained:
            raise RuntimeError("模型未训练")
        
        try:
            import torch
            
            self.torch_model.eval()
            with torch.no_grad():
                X_tensor = torch.tensor(X.values, dtype=torch.float32).to(self.device)
                predictions = self.torch_model(X_tensor)
                
                # 转换回numpy和DataFrame
                pred_numpy = predictions.cpu().numpy()
                return pd.DataFrame(pred_numpy, index=X.index, columns=['prediction'])
                
        except ImportError:
            raise AdapterError("PyTorch未安装")
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        # PyTorch模型的超参数设置需要自定义实现


class TensorFlowModelAdapter(IModel):
    """TensorFlow模型适配器"""
    
    def __init__(self, tf_model: Any = None, name: str = "TensorFlowModel"):
        super().__init__(name, MODEL_TYPES.DEEP_LEARNING)
        self.tf_model = tf_model
        
        if tf_model:
            self.name = f"TensorFlow{type(tf_model).__name__}"
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'TensorFlowModelAdapter':
        """训练模型"""
        if self.tf_model is None:
            raise ValueError("TensorFlow模型未设置")
        
        try:
            import tensorflow as tf
            
            self._feature_names = list(X.columns)
            if y is not None:
                self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # TensorFlow/Keras训练
            epochs = kwargs.get('epochs', 100)
            batch_size = kwargs.get('batch_size', 32)
            validation_split = kwargs.get('validation_split', 0.2)
            
            history = self.tf_model.fit(
                X, y,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=validation_split,
                verbose=kwargs.get('verbose', 0)
            )
            
            # 保存训练历史
            if hasattr(history, 'history'):
                for epoch, metrics in enumerate(history.history.items()):
                    self.add_training_record(dict(metrics), epoch)
            
            self.update_status(self.ModelStatus.TRAINED)
            return self
            
        except ImportError:
            raise AdapterError("TensorFlow未安装")
        except Exception as e:
            self.update_status(self.ModelStatus.UNTRAINED)
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测"""
        if not self.is_trained:
            raise RuntimeError("模型未训练")
        
        try:
            predictions = self.tf_model.predict(X)
            
            if predictions.ndim == 1:
                return pd.DataFrame(predictions, index=X.index, columns=['prediction'])
            else:
                columns = [f'prediction_{i}' for i in range(predictions.shape[1])]
                return pd.DataFrame(predictions, index=X.index, columns=columns)
                
        except ImportError:
            raise AdapterError("TensorFlow未安装")
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        # TensorFlow模型的超参数设置需要重新编译模型


class GenericModelAdapter(IModel):
    """通用模型适配器"""
    
    def __init__(self, model: Any, name: str = "GenericModel"):
        super().__init__(name, MODEL_TYPES.UNKNOWN)
        self.wrapped_model = model
        
        if hasattr(model, '__class__'):
            self.name = f"Generic{model.__class__.__name__}"
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'GenericModelAdapter':
        """训练模型"""
        try:
            if hasattr(self.wrapped_model, 'fit'):
                if y is not None:
                    self.wrapped_model.fit(X, y, **kwargs)
                else:
                    self.wrapped_model.fit(X, **kwargs)
            else:
                raise NotImplementedError("模型没有fit方法")
            
            self._feature_names = list(X.columns)
            if y is not None:
                self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            self.update_status(self.ModelStatus.TRAINED)
            return self
            
        except Exception as e:
            self.update_status(self.ModelStatus.UNTRAINED)
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测"""
        if not hasattr(self.wrapped_model, 'predict'):
            raise NotImplementedError("模型没有predict方法")
        
        predictions = self.wrapped_model.predict(X, **kwargs)
        
        if isinstance(predictions, np.ndarray):
            if predictions.ndim == 1:
                return pd.DataFrame(predictions, index=X.index, columns=['prediction'])
            else:
                columns = [f'prediction_{i}' for i in range(predictions.shape[1])]
                return pd.DataFrame(predictions, index=X.index, columns=columns)
        
        return predictions
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        
        # 尝试设置属性
        for key, value in hyperparams.items():
            if hasattr(self.wrapped_model, key):
                setattr(self.wrapped_model, key, value)