"""
ML服务容器

提供机器学习相关服务的依赖注入容器，集成模型工厂、特征工程、超参数管理等服务。
"""

from typing import Dict, Any, Type

from ginkgo.core.interfaces.model_interface import IModel
from ginkgo.quant_ml.models.lightgbm import LightGBMModel
from ginkgo.quant_ml.models.xgboost import XGBoostModel
from ginkgo.quant_ml.models.sklearn import RandomForestModel, LinearModel, SVMModel
from ginkgo.quant_ml.features.feature_processor import FeatureProcessor
from ginkgo.quant_ml.features.alpha_factors import AlphaFactors


# 简化的模型类型映射
MODEL_TYPE_MAPPING = {
    "lightgbm": LightGBMModel,
    "xgboost": XGBoostModel,
    "random_forest": RandomForestModel,
    "linear": LinearModel,
    "svm": SVMModel,
}


def create_model(model_type: str, **kwargs) -> IModel:
    """
    模型工厂方法
    
    Args:
        model_type: 模型类型 ("lightgbm", "xgboost", "random_forest", "linear", "svm")
        **kwargs: 模型初始化参数
        
    Returns:
        IModel: 模型实例
    """
    if model_type not in MODEL_TYPE_MAPPING:
        raise ValueError(f"不支持的模型类型: {model_type}")
    
    model_class = MODEL_TYPE_MAPPING[model_type]
    return model_class(**kwargs)


def get_available_models() -> Dict[str, Type[IModel]]:
    """获取所有可用的模型类型"""
    return MODEL_TYPE_MAPPING.copy()


def create_feature_processor(**kwargs) -> FeatureProcessor:
    """创建特征处理器"""
    return FeatureProcessor(**kwargs)


def create_alpha_factors(**kwargs) -> AlphaFactors:
    """创建Alpha因子计算器"""
    return AlphaFactors(**kwargs)


# 简化的容器类
class SimpleMLContainer:
    """简化的ML容器，避免复杂的依赖注入"""
    
    def __init__(self):
        self._models = MODEL_TYPE_MAPPING
        self._feature_processor = None
        self._alpha_factors = None
    
    def get_model(self, model_type: str, **kwargs) -> IModel:
        """获取模型实例"""
        return create_model(model_type, **kwargs)
    
    def get_feature_processor(self, **kwargs) -> FeatureProcessor:
        """获取特征处理器"""
        if self._feature_processor is None:
            self._feature_processor = FeatureProcessor(**kwargs)
        return self._feature_processor
    
    def get_alpha_factors(self, **kwargs) -> AlphaFactors:
        """获取Alpha因子计算器"""
        if self._alpha_factors is None:
            self._alpha_factors = AlphaFactors(**kwargs)
        return self._alpha_factors
    
    def list_models(self) -> Dict[str, Type[IModel]]:
        """列出可用模型"""
        return self._models.copy()


# 创建全局容器实例
ml_container = SimpleMLContainer()