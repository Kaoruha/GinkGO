# Upstream: 模型适配器(sklearn/xgboost/lightgbm 继承BaseModel)、ML策略模块
# Downstream: MODEL_TYPES(枚举), pandas, numpy, datetime, sklearn.metrics
# Role: ML模型统一接口，定义BaseModel协议含fit/predict/save/load等完整生命周期
# Origin: 自 core/interfaces/model_interface.py 迁入（ADR-022 原则6 · core/interfaces 整层下架）；
#         死子类 BaseTimeSeriesModel/BaseEnsembleModel（0 继承者）未随迁，就地删除。

"""
ML模型统一接口定义

定义所有ML模型必须实现的统一接口，
支持不同类型的机器学习模型（监督学习、强化学习、深度学习等）。

历史：自 core/interfaces 整层下架时迁入 quant_ml 域（ADR-022 原则6 · 命名空间唯一性）。
5 处生产 import 全在 quant_ml 域（lightgbm/sklearn/xgboost + trading 与 quant_ml 的 ML 策略基类），
迁移路径扁平无循环。死子类 BaseTimeSeriesModel/BaseEnsembleModel（0 继承者）未随迁。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum

from ginkgo.enums import MODEL_TYPES


class ModelStatus(Enum):
    """模型状态枚举"""
    UNTRAINED = "untrained"
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"


class BaseModel(ABC):
    """ML模型统一接口"""

    def __init__(self, name: str = "UnknownModel", model_type: MODEL_TYPES = MODEL_TYPES.UNKNOWN):
        self.name = name
        self.model_type = model_type
        self.status = ModelStatus.UNTRAINED
        self.version = "1.0.0"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 模型配置
        self._config = {}
        self._hyperparameters = {}

        # 训练相关
        self._training_history = []
        self._validation_metrics = {}

        # 特征相关
        self._feature_names = []
        self._target_names = []

    @property
    def config(self) -> Dict[str, Any]:
        """模型配置"""
        return self._config

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        """超参数"""
        return self._hyperparameters

    @property
    def training_history(self) -> List[Dict[str, Any]]:
        """训练历史"""
        return self._training_history

    @property
    def validation_metrics(self) -> Dict[str, float]:
        """验证指标"""
        return self._validation_metrics

    @property
    def feature_names(self) -> List[str]:
        """特征名称"""
        return self._feature_names

    @property
    def target_names(self) -> List[str]:
        """目标变量名称"""
        return self._target_names

    @property
    def is_trained(self) -> bool:
        """是否已训练"""
        return self.status in [ModelStatus.TRAINED, ModelStatus.DEPLOYED]

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'BaseModel':
        """
        训练模型

        Args:
            X: 特征数据
            y: 目标变量（可选，用于监督学习）
            **kwargs: 训练参数

        Returns:
            BaseModel: 训练后的模型实例
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame, **kwargs) -> Union[pd.DataFrame, np.ndarray]:
        """
        模型预测

        Args:
            X: 特征数据
            **kwargs: 预测参数

        Returns:
            预测结果
        """
        pass

    def predict_proba(self, X: pd.DataFrame, **kwargs) -> Union[pd.DataFrame, np.ndarray]:
        """
        预测概率（用于分类模型）

        Args:
            X: 特征数据
            **kwargs: 预测参数

        Returns:
            预测概率
        """
        raise NotImplementedError(f"模型 {self.name} 不支持概率预测")

    def score(self, X: pd.DataFrame, y: pd.DataFrame, **kwargs) -> float:
        """
        模型评分

        Args:
            X: 特征数据
            y: 真实标签
            **kwargs: 评分参数

        Returns:
            float: 评分结果
        """
        predictions = self.predict(X, **kwargs)
        return self._calculate_default_score(y, predictions)

    def _calculate_default_score(self, y_true: pd.DataFrame, y_pred: Union[pd.DataFrame, np.ndarray]) -> float:
        """计算默认评分（子类可重写）"""
        from sklearn.metrics import r2_score
        return r2_score(y_true, y_pred)

    @abstractmethod
    def set_hyperparameters(self, **hyperparams) -> None:
        """
        设置超参数

        Args:
            **hyperparams: 超参数字典
        """
        pass

    def get_hyperparameter(self, key: str, default: Any = None) -> Any:
        """获取单个超参数"""
        return self._hyperparameters.get(key, default)

    def validate_hyperparameters(self) -> bool:
        """验证超参数有效性"""
        return True

    def get_feature_importance(self) -> Optional[pd.Series]:
        """
        获取特征重要性（如果模型支持）

        Returns:
            pd.Series: 特征重要性，index为特征名，values为重要性分数
        """
        return None

    def cross_validate(self, X: pd.DataFrame, y: pd.DataFrame = None, cv: int = 5, **kwargs) -> Dict[str, float]:
        """
        交叉验证

        Args:
            X: 特征数据
            y: 目标变量
            cv: 折数
            **kwargs: 验证参数

        Returns:
            Dict[str, float]: 验证指标
        """
        from sklearn.model_selection import cross_val_score

        if not self.is_trained:
            # 临时训练用于交叉验证
            temp_model = self.__class__(name=f"temp_{self.name}")
            temp_model.set_hyperparameters(**self.hyperparameters)
            scores = cross_val_score(temp_model, X, y, cv=cv, **kwargs)
        else:
            scores = cross_val_score(self, X, y, cv=cv, **kwargs)

        return {
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'scores': scores.tolist()
        }

    def save(self, filepath: str, **kwargs) -> None:
        """
        保存模型

        Args:
            filepath: 保存路径
            **kwargs: 保存参数
        """
        import pickle

        model_data = {
            'name': self.name,
            'model_type': self.model_type,
            'status': self.status,
            'version': self.version,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'config': self._config,
            'hyperparameters': self._hyperparameters,
            'training_history': self._training_history,
            'validation_metrics': self._validation_metrics,
            'feature_names': self._feature_names,
            'target_names': self._target_names,
            'model_object': self  # 实际模型对象
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

    @classmethod
    def load(cls, filepath: str, **kwargs) -> 'BaseModel':
        """
        加载模型

        Args:
            filepath: 模型文件路径
            **kwargs: 加载参数

        Returns:
            BaseModel: 加载的模型实例
        """
        import pickle

        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        model = model_data['model_object']
        return model

    def clone(self) -> 'BaseModel':
        """克隆模型（保持相同配置但未训练状态）"""
        cloned = self.__class__(name=f"{self.name}_clone", model_type=self.model_type)
        cloned._config = self._config.copy()
        cloned._hyperparameters = self._hyperparameters.copy()
        cloned._feature_names = self._feature_names.copy()
        cloned._target_names = self._target_names.copy()
        return cloned

    def get_metadata(self) -> Dict[str, Any]:
        """获取模型元数据"""
        return {
            'name': self.name,
            'model_type': self.model_type.value if hasattr(self.model_type, 'value') else str(self.model_type),
            'status': self.status.value,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_trained': self.is_trained,
            'feature_count': len(self._feature_names),
            'target_count': len(self._target_names),
            'hyperparameters': self._hyperparameters,
            'validation_metrics': self._validation_metrics
        }

    def update_status(self, new_status: ModelStatus) -> None:
        """更新模型状态"""
        self.status = new_status
        self.updated_at = datetime.now()

    def add_training_record(self, metrics: Dict[str, float], epoch: int = None) -> None:
        """添加训练记录"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics.copy()
        }
        if epoch is not None:
            record['epoch'] = epoch

        self._training_history.append(record)
        self.updated_at = datetime.now()

    def set_validation_metrics(self, metrics: Dict[str, float]) -> None:
        """设置验证指标"""
        self._validation_metrics = metrics.copy()
        self.updated_at = datetime.now()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, type={self.model_type}, status={self.status.value})"

    def __repr__(self) -> str:
        return self.__str__()
