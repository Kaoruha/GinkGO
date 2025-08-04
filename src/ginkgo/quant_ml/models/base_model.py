"""
ML模型基类

实现IModel接口，为所有ML模型提供统一的基础功能。
"""

from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime

from ginkgo.core.interfaces.model_interface import IModel, ModelStatus
from ginkgo.enums import MODEL_TYPES
from ginkgo.libs import GLOG


class BaseMLModel(IModel):
    """ML模型基类"""
    
    def __init__(self, name: str = "BaseMLModel", model_type: MODEL_TYPES = MODEL_TYPES.UNKNOWN):
        super().__init__(name, model_type)
        
        # 数据相关
        self._train_data = None
        self._validation_data = None
        self._test_data = None
        
        # 特征相关
        self._feature_importance = None
        self._feature_statistics = {}
        
        # 模型相关
        self._model_params = {}
        self._training_config = {}
        
    @property
    def train_data(self) -> Optional[pd.DataFrame]:
        """训练数据"""
        return self._train_data
    
    @property
    def validation_data(self) -> Optional[pd.DataFrame]:
        """验证数据"""
        return self._validation_data
    
    @property
    def test_data(self) -> Optional[pd.DataFrame]:
        """测试数据"""
        return self._test_data
    
    @property
    def model_params(self) -> Dict[str, Any]:
        """模型参数"""
        return self._model_params
    
    def set_training_data(self, train_data: pd.DataFrame, validation_data: pd.DataFrame = None, test_data: pd.DataFrame = None) -> None:
        """
        设置训练数据
        
        Args:
            train_data: 训练数据
            validation_data: 验证数据
            test_data: 测试数据
        """
        self._train_data = train_data
        self._validation_data = validation_data
        self._test_data = test_data
        
        # 记录特征信息
        if train_data is not None:
            self._feature_names = list(train_data.columns)
            self._calculate_feature_statistics(train_data)
    
    def _calculate_feature_statistics(self, data: pd.DataFrame) -> None:
        """计算特征统计信息"""
        self._feature_statistics = {
            'mean': data.mean().to_dict(),
            'std': data.std().to_dict(),
            'min': data.min().to_dict(),
            'max': data.max().to_dict(),
            'missing_ratio': (data.isnull().sum() / len(data)).to_dict(),
            'data_shape': data.shape,
            'dtypes': data.dtypes.astype(str).to_dict()
        }
    
    def get_feature_statistics(self) -> Dict[str, Any]:
        """获取特征统计信息"""
        return self._feature_statistics
    
    def preprocess_data(self, data: pd.DataFrame, fit_scaler: bool = True) -> pd.DataFrame:
        """
        数据预处理
        
        Args:
            data: 原始数据
            fit_scaler: 是否拟合标准化器
            
        Returns:
            pd.DataFrame: 预处理后的数据
        """
        processed_data = data.copy()
        
        # 处理缺失值
        processed_data = self._handle_missing_values(processed_data)
        
        # 特征标准化
        if fit_scaler:
            processed_data = self._scale_features(processed_data, fit=True)
        else:
            processed_data = self._scale_features(processed_data, fit=False)
        
        # 特征工程
        processed_data = self._feature_engineering(processed_data)
        
        return processed_data
    
    def _handle_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 默认前向填充
        return data.fillna(method='ffill').fillna(0)
    
    def _scale_features(self, data: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """特征标准化"""
        # 简单的Z-score标准化，子类可以重写
        if not hasattr(self, '_scaler_params'):
            self._scaler_params = {}
        
        scaled_data = data.copy()
        
        for column in data.select_dtypes(include=[np.number]).columns:
            if fit:
                mean = data[column].mean()
                std = data[column].std()
                self._scaler_params[column] = {'mean': mean, 'std': std}
            else:
                if column in self._scaler_params:
                    mean = self._scaler_params[column]['mean']
                    std = self._scaler_params[column]['std']
                else:
                    continue
            
            if std > 0:
                scaled_data[column] = (data[column] - mean) / std
        
        return scaled_data
    
    def _feature_engineering(self, data: pd.DataFrame) -> pd.DataFrame:
        """特征工程 - 子类可重写"""
        return data
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'BaseMLModel':
        """
        训练模型 - 抽象方法，子类必须实现
        
        Args:
            X: 特征数据
            y: 目标变量
            **kwargs: 训练参数
            
        Returns:
            BaseMLModel: 训练后的模型
        """
        self.update_status(ModelStatus.TRAINING)
        
        try:
            # 数据预处理
            X_processed = self.preprocess_data(X, fit_scaler=True)
            
            # 记录训练数据信息
            self.set_training_data(X_processed, y)
            
            # 子类实现具体训练逻辑
            self._fit_implementation(X_processed, y, **kwargs)
            
            # 更新状态
            self.update_status(ModelStatus.TRAINED)
            GLOG.INFO(f"模型 {self.name} 训练完成")
            
            return self
            
        except Exception as e:
            self.update_status(ModelStatus.UNTRAINED)
            GLOG.ERROR(f"模型 {self.name} 训练失败: {e}")
            raise
    
    def _fit_implementation(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> None:
        """具体训练实现 - 子类重写"""
        raise NotImplementedError("子类必须实现_fit_implementation方法")
    
    def predict(self, X: pd.DataFrame, **kwargs) -> Union[pd.DataFrame, np.ndarray]:
        """
        预测
        
        Args:
            X: 特征数据
            **kwargs: 预测参数
            
        Returns:
            预测结果
        """
        if not self.is_trained:
            raise RuntimeError(f"模型 {self.name} 未训练")
        
        try:
            # 数据预处理
            X_processed = self.preprocess_data(X, fit_scaler=False)
            
            # 子类实现具体预测逻辑
            predictions = self._predict_implementation(X_processed, **kwargs)
            
            return predictions
            
        except Exception as e:
            GLOG.ERROR(f"模型 {self.name} 预测失败: {e}")
            raise
    
    def _predict_implementation(self, X: pd.DataFrame, **kwargs) -> Union[pd.DataFrame, np.ndarray]:
        """具体预测实现 - 子类重写"""
        raise NotImplementedError("子类必须实现_predict_implementation方法")
    
    def evaluate(self, X: pd.DataFrame, y: pd.DataFrame, metrics: List[str] = None) -> Dict[str, float]:
        """
        模型评估
        
        Args:
            X: 特征数据
            y: 真实标签
            metrics: 评估指标列表
            
        Returns:
            Dict[str, float]: 评估结果
        """
        if not self.is_trained:
            raise RuntimeError("模型未训练")
        
        predictions = self.predict(X)
        
        # 默认评估指标
        if metrics is None:
            metrics = self._get_default_metrics()
        
        results = {}
        for metric in metrics:
            try:
                score = self._calculate_metric(y, predictions, metric)
                results[metric] = score
            except Exception as e:
                GLOG.WARNING(f"计算指标 {metric} 失败: {e}")
                results[metric] = None
        
        # 更新验证指标
        self.set_validation_metrics(results)
        
        return results
    
    def _get_default_metrics(self) -> List[str]:
        """获取默认评估指标"""
        return ['mse', 'mae', 'r2']
    
    def _calculate_metric(self, y_true: pd.DataFrame, y_pred: Union[pd.DataFrame, np.ndarray], metric: str) -> float:
        """计算单个指标"""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score
        
        # 转换为numpy数组
        if isinstance(y_true, pd.DataFrame):
            y_true = y_true.values
        if isinstance(y_pred, pd.DataFrame):
            y_pred = y_pred.values
        
        # 展平多维数组
        if y_true.ndim > 1:
            y_true = y_true.ravel()
        if y_pred.ndim > 1:
            y_pred = y_pred.ravel()
        
        if metric == 'mse':
            return mean_squared_error(y_true, y_pred)
        elif metric == 'mae':
            return mean_absolute_error(y_true, y_pred)
        elif metric == 'r2':
            return r2_score(y_true, y_pred)
        elif metric == 'accuracy':
            return accuracy_score(y_true, y_pred.round())
        else:
            raise ValueError(f"不支持的指标: {metric}")
    
    def get_feature_importance(self) -> Optional[pd.Series]:
        """获取特征重要性"""
        return self._feature_importance
    
    def set_feature_importance(self, importance: Union[np.ndarray, List[float], pd.Series]) -> None:
        """设置特征重要性"""
        if isinstance(importance, (np.ndarray, list)):
            self._feature_importance = pd.Series(importance, index=self._feature_names, name='importance')
        elif isinstance(importance, pd.Series):
            self._feature_importance = importance
        else:
            raise ValueError("特征重要性必须是numpy数组、列表或pandas Series")
    
    def plot_feature_importance(self, top_n: int = 20, save_path: str = None) -> None:
        """绘制特征重要性图"""
        if self._feature_importance is None:
            GLOG.WARNING("没有特征重要性数据")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            # 获取top特征
            top_features = self._feature_importance.nlargest(top_n)
            
            plt.figure(figsize=(10, 6))
            top_features.plot(kind='barh')
            plt.title(f'Top {top_n} Feature Importance - {self.name}')
            plt.xlabel('Importance')
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
                GLOG.INFO(f"特征重要性图已保存到: {save_path}")
            
            plt.show()
            
        except ImportError:
            GLOG.WARNING("matplotlib未安装，无法绘制图表")
    
    def save_model(self, filepath: str, **kwargs) -> None:
        """保存模型"""
        try:
            model_data = {
                'metadata': self.get_metadata(),
                'feature_statistics': self._feature_statistics,
                'scaler_params': getattr(self, '_scaler_params', {}),
                'model_params': self._model_params,
                'training_config': self._training_config,
                'feature_importance': self._feature_importance.to_dict() if self._feature_importance is not None else None,
                'model_object': self._get_model_state(),
            }
            
            import pickle
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            GLOG.INFO(f"模型已保存到: {filepath}")
            
        except Exception as e:
            GLOG.ERROR(f"保存模型失败: {e}")
            raise
    
    def _get_model_state(self) -> Any:
        """获取模型状态 - 子类重写"""
        return None
    
    @classmethod
    def load_model(cls, filepath: str, **kwargs) -> 'BaseMLModel':
        """加载模型"""
        try:
            import pickle
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            # 创建模型实例
            metadata = model_data['metadata']
            model = cls(name=metadata['name'])
            
            # 恢复模型状态
            model._feature_statistics = model_data.get('feature_statistics', {})
            model._scaler_params = model_data.get('scaler_params', {})
            model._model_params = model_data.get('model_params', {})
            model._training_config = model_data.get('training_config', {})
            
            # 恢复特征重要性
            if model_data.get('feature_importance'):
                importance_dict = model_data['feature_importance']
                model._feature_importance = pd.Series(importance_dict)
            
            # 恢复模型对象
            model._restore_model_state(model_data.get('model_object'))
            
            # 更新状态
            model.update_status(ModelStatus.TRAINED)
            
            GLOG.INFO(f"模型已从 {filepath} 加载")
            return model
            
        except Exception as e:
            GLOG.ERROR(f"加载模型失败: {e}")
            raise
    
    def _restore_model_state(self, model_state: Any) -> None:
        """恢复模型状态 - 子类重写"""
        pass
    
    def get_training_summary(self) -> Dict[str, Any]:
        """获取训练摘要"""
        summary = {
            'model_name': self.name,
            'model_type': self.model_type.value if hasattr(self.model_type, 'value') else str(self.model_type),
            'status': self.status.value,
            'is_trained': self.is_trained,
            'feature_count': len(self._feature_names),
            'training_data_shape': self._feature_statistics.get('data_shape', None),
            'hyperparameters': self._hyperparameters,
            'validation_metrics': self._validation_metrics,
            'training_history_count': len(self._training_history),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        
        # 添加特征重要性摘要
        if self._feature_importance is not None:
            summary['top_features'] = self._feature_importance.nlargest(5).to_dict()
        
        return summary
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        self._model_params.update(hyperparams)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, type={self.model_type}, status={self.status.value})"
    
    def __repr__(self) -> str:
        return self.__str__()