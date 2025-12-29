# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: SklearnModel Sklearn模型封装Sklearn算法接口支持Scikit-learn集成






"""
Sklearn模型实现

基于scikit-learn的机器学习模型，包括随机森林、线性模型等。
所有模型都适配ginkgo的IModel接口。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge, Lasso
    from sklearn.svm import SVR, SVC
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import r2_score, accuracy_score, roc_auc_score
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ginkgo.core.interfaces.model_interface import IModel, ModelStatus
from ginkgo.enums import MODEL_TYPES
from ginkgo.libs import GLOG


class SklearnModelBase(IModel):
    """Sklearn模型基类"""
    
    def __init__(self, name: str, sklearn_model, task: str = "regression", **kwargs):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn未安装，请运行: pip install scikit-learn")
        
        super().__init__(name, MODEL_TYPES.TABULAR)
        
        self.task = task
        self.sklearn_model = sklearn_model
        
        # 设置模型参数
        if hasattr(sklearn_model, 'get_params'):
            self._hyperparameters = sklearn_model.get_params()
        self._hyperparameters.update(kwargs)
        
        if hasattr(sklearn_model, 'set_params'):
            sklearn_model.set_params(**kwargs)
        
        GLOG.INFO(f"初始化{name}模型，任务类型: {task}")
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'SklearnModelBase':
        """训练模型"""
        if y is None:
            raise ValueError("监督学习需要目标变量y")
        
        try:
            self.update_status(ModelStatus.TRAINING)
            
            # 记录特征和目标信息
            self._feature_names = list(X.columns)
            self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # 准备目标变量
            y_array = self._prepare_target(y)
            
            # 训练参数
            sample_weight = kwargs.get('sample_weight', None)
            
            GLOG.INFO(f"开始训练{self.name}模型，特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
            
            # 训练模型
            if sample_weight is not None:
                self.sklearn_model.fit(X, y_array, sample_weight=sample_weight)
            else:
                self.sklearn_model.fit(X, y_array)
            
            # 更新状态
            self.update_status(ModelStatus.TRAINED)
            
            # 记录训练指标
            if hasattr(self.sklearn_model, 'score'):
                train_score = self.sklearn_model.score(X, y_array)
                self.add_training_record({"train_score": train_score})
                GLOG.INFO(f"{self.name}训练完成，训练分数: {train_score:.4f}")
            
            return self
            
        except Exception as e:
            self.update_status(ModelStatus.UNTRAINED)
            GLOG.ERROR(f"{self.name}训练失败: {e}")
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测"""
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用fit方法")
        
        try:
            predictions = self.sklearn_model.predict(X)
            
            # 转换为DataFrame
            if predictions.ndim == 1:
                return pd.DataFrame(predictions, index=X.index, columns=['prediction'])
            else:
                columns = [f'prediction_{i}' for i in range(predictions.shape[1])]
                return pd.DataFrame(predictions, index=X.index, columns=columns)
                
        except Exception as e:
            GLOG.ERROR(f"{self.name}预测失败: {e}")
            raise e
    
    def predict_proba(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测概率"""
        if not hasattr(self.sklearn_model, 'predict_proba'):
            raise NotImplementedError(f"{self.name}不支持概率预测")
        
        probabilities = self.sklearn_model.predict_proba(X)
        
        # 获取类别标签
        if hasattr(self.sklearn_model, 'classes_'):
            columns = [f'prob_class_{cls}' for cls in self.sklearn_model.classes_]
        else:
            columns = [f'prob_class_{i}' for i in range(probabilities.shape[1])]
        
        return pd.DataFrame(probabilities, index=X.index, columns=columns)
    
    def score(self, X: pd.DataFrame, y: pd.DataFrame, **kwargs) -> float:
        """评分"""
        y_array = self._prepare_target(y)
        return self.sklearn_model.score(X, y_array)
    
    def get_feature_importance(self) -> Optional[pd.Series]:
        """获取特征重要性"""
        if hasattr(self.sklearn_model, 'feature_importances_'):
            return pd.Series(
                self.sklearn_model.feature_importances_,
                index=self._feature_names,
                name='importance'
            ).sort_values(ascending=False)
        elif hasattr(self.sklearn_model, 'coef_'):
            # 线性模型的系数
            coef = self.sklearn_model.coef_
            if coef.ndim > 1:
                coef = np.abs(coef).mean(axis=0)
            return pd.Series(
                np.abs(coef),
                index=self._feature_names,
                name='importance'
            ).sort_values(ascending=False)
        
        return None
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        
        if hasattr(self.sklearn_model, 'set_params'):
            self.sklearn_model.set_params(**hyperparams)
        
        GLOG.INFO(f"更新{self.name}超参数: {hyperparams}")
    
    def cross_validate(self, X: pd.DataFrame, y: pd.DataFrame = None, cv: int = 5, **kwargs) -> Dict[str, float]:
        """交叉验证"""
        y_array = self._prepare_target(y)
        
        # 选择评分指标
        scoring = kwargs.get('scoring', None)
        if scoring is None:
            scoring = 'r2' if self.task == 'regression' else 'accuracy'
        
        scores = cross_val_score(self.sklearn_model, X, y_array, cv=cv, scoring=scoring)
        
        return {
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'scores': scores.tolist()
        }
    
    def save(self, filepath: str, **kwargs) -> None:
        """保存模型"""
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，无法保存")
        
        # 保存sklearn模型
        model_path = filepath.replace('.pkl', '.joblib')
        joblib.dump(self.sklearn_model, model_path)
        
        # 保存元数据
        super().save(filepath, **kwargs)
        
        GLOG.INFO(f"{self.name}模型已保存: {filepath}")
    
    @classmethod
    def load(cls, filepath: str, **kwargs) -> 'SklearnModelBase':
        """加载模型"""
        # 先加载元数据
        base_model = super().load(filepath, **kwargs)
        
        # 加载sklearn模型
        model_path = filepath.replace('.pkl', '.joblib')
        if model_path != filepath:
            base_model.sklearn_model = joblib.load(model_path)
        
        GLOG.INFO(f"模型已加载: {filepath}")
        return base_model
    
    def _prepare_target(self, y: Union[pd.DataFrame, pd.Series, np.ndarray]) -> np.ndarray:
        """准备目标变量格式"""
        if isinstance(y, pd.DataFrame):
            if y.shape[1] == 1:
                return y.values.ravel()
            else:
                return y.values
        elif isinstance(y, pd.Series):
            return y.values
        elif isinstance(y, np.ndarray):
            return y
        else:
            return np.array(y)


class RandomForestModel(SklearnModelBase):
    """随机森林模型"""
    
    DEFAULT_PARAMS = {
        "n_estimators": 100,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
        "bootstrap": True,
        "random_state": 42,
        "n_jobs": -1
    }
    
    def __init__(self, 
                 name: str = "RandomForest",
                 task: str = "regression",
                 **kwargs):
        """
        初始化随机森林模型
        
        Args:
            name: 模型名称
            task: 任务类型 ("regression" 或 "classification")
            **kwargs: RandomForest参数
        """
        # 合并默认参数
        params = self.DEFAULT_PARAMS.copy()
        params.update(kwargs)
        
        # 根据任务选择模型类型
        if task == "regression":
            sklearn_model = RandomForestRegressor(**params)
        elif task == "classification":
            sklearn_model = RandomForestClassifier(**params)
        else:
            raise ValueError(f"不支持的任务类型: {task}")
        
        super().__init__(name, sklearn_model, task, **kwargs)


class LinearModel(SklearnModelBase):
    """线性模型"""
    
    def __init__(self, 
                 name: str = "Linear",
                 task: str = "regression",
                 model_type: str = "linear",
                 **kwargs):
        """
        初始化线性模型
        
        Args:
            name: 模型名称
            task: 任务类型 ("regression" 或 "classification")
            model_type: 线性模型类型 ("linear", "ridge", "lasso")
            **kwargs: 模型参数
        """
        # 根据任务和模型类型选择sklearn模型
        if task == "regression":
            if model_type == "linear":
                sklearn_model = LinearRegression(**kwargs)
            elif model_type == "ridge":
                sklearn_model = Ridge(**kwargs)
            elif model_type == "lasso":
                sklearn_model = Lasso(**kwargs)
            else:
                raise ValueError(f"不支持的回归模型类型: {model_type}")
        elif task == "classification":
            sklearn_model = LogisticRegression(**kwargs)
        else:
            raise ValueError(f"不支持的任务类型: {task}")
        
        super().__init__(name, sklearn_model, task, **kwargs)


class SVMModel(SklearnModelBase):
    """支持向量机模型"""
    
    def __init__(self, 
                 name: str = "SVM",
                 task: str = "regression",
                 **kwargs):
        """
        初始化SVM模型
        
        Args:
            name: 模型名称
            task: 任务类型 ("regression" 或 "classification")
            **kwargs: SVM参数
        """
        # 设置默认参数
        default_params = {"kernel": "rbf", "C": 1.0, "gamma": "scale"}
        default_params.update(kwargs)
        
        # 根据任务选择模型类型
        if task == "regression":
            sklearn_model = SVR(**default_params)
        elif task == "classification":
            sklearn_model = SVC(**default_params)
        else:
            raise ValueError(f"不支持的任务类型: {task}")
        
        super().__init__(name, sklearn_model, task, **kwargs)