"""
ML Module Container

Provides unified access to ML services using dependency-injector,
following the same pattern as data and backtest modules.

Usage Examples:

    from ginkgo.quant_ml.containers import container
    
    # Access models (similar to data.cruds.bar())
    lightgbm_model = container.models.lightgbm()
    xgboost_model = container.models.xgboost()
    
    # Access services
    feature_processor = container.services.feature_processor()
    alpha_factors = container.services.alpha_factors()
    
    # For dependency injection:
    from dependency_injector.wiring import inject, Provide
    
    @inject
    def your_function(model = Provide[Container.models.lightgbm]):
        # Use model here
        pass
"""

from dependency_injector import containers, providers
from typing import Dict, Any, Type


# ============= LAZY IMPORT FUNCTIONS =============
def _get_lightgbm_model_class():
    """Lazy import for LightGBM model class."""
    from ginkgo.quant_ml.models.lightgbm import LightGBMModel
    return LightGBMModel

def _get_xgboost_model_class():
    """Lazy import for XGBoost model class."""
    from ginkgo.quant_ml.models.xgboost import XGBoostModel
    return XGBoostModel

def _get_random_forest_model_class():
    """Lazy import for RandomForest model class."""
    from ginkgo.quant_ml.models.sklearn import RandomForestModel
    return RandomForestModel

def _get_linear_model_class():
    """Lazy import for Linear model class."""
    from ginkgo.quant_ml.models.sklearn import LinearModel
    return LinearModel

def _get_svm_model_class():
    """Lazy import for SVM model class."""
    from ginkgo.quant_ml.models.sklearn import SVMModel
    return SVMModel

def _get_feature_processor_class():
    """Lazy import for FeatureProcessor class."""
    from ginkgo.quant_ml.features.feature_processor import FeatureProcessor
    return FeatureProcessor

def _get_alpha_factors_class():
    """Lazy import for AlphaFactors class."""
    from ginkgo.quant_ml.features.alpha_factors import AlphaFactors
    return AlphaFactors

def _get_ml_strategy_base_class():
    """Lazy import for MLStrategyBase class."""
    from ginkgo.quant_ml.strategies.ml_strategy_base import MLStrategyBase
    return MLStrategyBase

def _get_prediction_strategy_class():
    """Lazy import for PredictionStrategy class."""
    from ginkgo.quant_ml.strategies.prediction_strategy import PredictionStrategy
    return PredictionStrategy


class Container(containers.DeclarativeContainer):
    """
    ML module dependency injection container.
    
    Provides unified access to ML components using FactoryAggregate,
    following the data module's successful pattern.
    """
    
    # ============= MODELS =============
    # Model factories - using Factory for per-use instances
    lightgbm_model = providers.Factory(_get_lightgbm_model_class)
    xgboost_model = providers.Factory(_get_xgboost_model_class)
    random_forest_model = providers.Factory(_get_random_forest_model_class)
    linear_model = providers.Factory(_get_linear_model_class)
    svm_model = providers.Factory(_get_svm_model_class)
    
    # Models aggregate - similar to data module's cruds
    models = providers.FactoryAggregate(
        lightgbm=lightgbm_model,
        xgboost=xgboost_model,
        random_forest=random_forest_model,
        linear=linear_model,
        svm=svm_model
    )
    
    # ============= SERVICES =============
    # Service factories - using Singleton for shared services
    feature_processor_service = providers.Singleton(_get_feature_processor_class)
    alpha_factors_service = providers.Singleton(_get_alpha_factors_class)
    
    # Services aggregate
    services = providers.FactoryAggregate(
        feature_processor=feature_processor_service,
        alpha_factors=alpha_factors_service
    )
    
    # ============= STRATEGIES =============
    # Strategy factories
    ml_strategy_base = providers.Factory(_get_ml_strategy_base_class)
    prediction_strategy = providers.Factory(_get_prediction_strategy_class)
    
    # Strategies aggregate
    strategies = providers.FactoryAggregate(
        base=ml_strategy_base,
        prediction=prediction_strategy
    )


# Create a singleton instance of the container, accessible throughout the application
container = Container()

# Backward compatibility - provide old access methods
def create_model(model_type: str, **kwargs):
    """Create model by type (backward compatibility)"""
    model_mapping = {
        'lightgbm': container.models.lightgbm,
        'xgboost': container.models.xgboost,
        'random_forest': container.models.random_forest,
        'linear': container.models.linear,
        'svm': container.models.svm
    }
    
    if model_type in model_mapping:
        return model_mapping[model_type](**kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

def get_available_models() -> Dict[str, str]:
    """Get available model types (backward compatibility)"""
    return {
        "lightgbm": "LightGBM Gradient Boosting",
        "xgboost": "XGBoost Gradient Boosting", 
        "random_forest": "Random Forest",
        "linear": "Linear Model",
        "svm": "Support Vector Machine"
    }

def create_feature_processor(**kwargs):
    """Create feature processor (backward compatibility)"""
    return container.services.feature_processor()(**kwargs)

def create_alpha_factors(**kwargs):
    """Create alpha factors (backward compatibility)"""
    return container.services.alpha_factors()(**kwargs)

def get_service_info():
    """Get service information (backward compatibility)"""
    return {
        "models": ["lightgbm", "xgboost", "random_forest", "linear", "svm"],
        "services": ["feature_processor", "alpha_factors"],
        "strategies": ["base", "prediction"]
    }

# Bind backward compatibility methods to container
container.create_model = create_model
container.get_available_models = get_available_models
container.create_feature_processor = create_feature_processor
container.create_alpha_factors = create_alpha_factors
container.get_service_info = get_service_info

# Create alias for backward compatibility
ml_container = container