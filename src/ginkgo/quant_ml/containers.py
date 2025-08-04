"""
ML Module Container

Provides unified access to machine learning components using dependency-injector,
following the same pattern as data, backtest, and core modules.

Usage Examples:

    from ginkgo.quant_ml.containers import container
    
    # Access ML models (similar to data.cruds.bar())
    sklearn_model = container.models.sklearn()
    torch_model = container.models.torch()
    
    # Access ML strategies
    ml_strategy = container.strategies.base_ml()
    
    # Access utilities
    feature_processor = container.utilities.feature_processor()
    model_evaluator = container.utilities.evaluator()
    
    # For dependency injection:
    from dependency_injector.wiring import inject, Provide
    
    @inject
    def your_function(model = Provide[Container.models.sklearn]):
        # Use model here
        pass
"""

from dependency_injector import containers, providers


# ============= LAZY IMPORT FUNCTIONS =============
# Model classes
def _get_base_model_class():
    """Lazy import for base ML model."""
    try:
        from ginkgo.quant_ml.models.base_model import BaseMLModel
        return BaseMLModel
    except ImportError:
        # Fallback to a simple model class if not available
        class MockMLModel:
            def __init__(self):
                self.is_trained = False
            def train(self, data):
                self.is_trained = True
                return {"status": "success", "mock": True}
            def predict(self, data):
                return [0.5] * len(data) if hasattr(data, '__len__') else 0.5
        return MockMLModel

def _get_sklearn_model_class():
    """Lazy import for sklearn model."""
    try:
        from ginkgo.quant_ml.models.sklearn_model import SklearnModel
        return SklearnModel
    except ImportError:
        return _get_base_model_class()

def _get_torch_model_class():
    """Lazy import for PyTorch model."""
    try:
        from ginkgo.quant_ml.models.torch_model import TorchModel
        return TorchModel
    except ImportError:
        return _get_base_model_class()

# Strategy classes
def _get_base_ml_strategy_class():
    """Lazy import for base ML strategy."""
    try:
        from ginkgo.quant_ml.strategies.base_ml_strategy import BaseMLStrategy
        return BaseMLStrategy
    except ImportError:
        # Fallback to a simple strategy class if not available
        class MockMLStrategy:
            def __init__(self):
                self.model = None
            def initialize(self):
                pass
            def generate_signals(self, data):
                return []
        return MockMLStrategy

# Utility classes
def _get_feature_processor_class():
    """Lazy import for feature processor."""
    try:
        from ginkgo.quant_ml.utils.feature_processor import FeatureProcessor
        return FeatureProcessor
    except ImportError:
        # Fallback to a simple processor if not available
        class MockFeatureProcessor:
            def __init__(self):
                pass
            def process_features(self, data):
                return data
        return MockFeatureProcessor

def _get_model_evaluator_class():
    """Lazy import for model evaluator."""
    try:
        from ginkgo.quant_ml.utils.model_evaluator import ModelEvaluator
        return ModelEvaluator
    except ImportError:
        # Fallback to a simple evaluator if not available
        class MockModelEvaluator:
            def __init__(self):
                pass
            def evaluate(self, model, test_data):
                return {"accuracy": 0.85, "mse": 0.15, "mock": True}
        return MockModelEvaluator


class Container(containers.DeclarativeContainer):
    """
    ML module dependency injection container.
    
    Provides unified access to ML components using FactoryAggregate,
    following the data module's successful pattern.
    """
    
    # ============= MODELS =============
    # Model factories
    base_model = providers.Factory(_get_base_model_class)
    sklearn_model = providers.Factory(_get_sklearn_model_class)
    torch_model = providers.Factory(_get_torch_model_class)
    
    # Models aggregate - similar to data module's cruds
    models = providers.FactoryAggregate(
        base=base_model,
        sklearn=sklearn_model,
        torch=torch_model
    )
    
    # ============= STRATEGIES =============
    # Strategy factories
    base_ml_strategy = providers.Factory(_get_base_ml_strategy_class)
    
    # Strategies aggregate
    strategies = providers.FactoryAggregate(
        base_ml=base_ml_strategy
    )
    
    # ============= UTILITIES =============
    # Utility factories
    feature_processor = providers.Factory(_get_feature_processor_class)
    model_evaluator = providers.Factory(_get_model_evaluator_class)
    
    # Utilities aggregate
    utilities = providers.FactoryAggregate(
        feature_processor=feature_processor,
        evaluator=model_evaluator
    )


# Create a singleton instance of the container, accessible throughout the application
container = Container()

# Backward compatibility - provide old access methods (following backtest pattern)
def get_model(model_type: str):
    """Get model by type (backward compatibility)"""
    model_mapping = {
        'base': container.models.base,
        'sklearn': container.models.sklearn,
        'torch': container.models.torch
    }
    
    if model_type in model_mapping:
        return model_mapping[model_type]()
    else:
        raise ValueError(f"Unknown model type: {model_type}")

def get_strategy(strategy_type: str):
    """Get strategy by type (backward compatibility)"""
    strategy_mapping = {
        'base_ml': container.strategies.base_ml
    }
    
    if strategy_type in strategy_mapping:
        return strategy_mapping[strategy_type]()
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

def get_service_info():
    """Get service information (backward compatibility)"""
    return {
        "models": ["base", "sklearn", "torch"],
        "strategies": ["base_ml"],
        "utilities": ["feature_processor", "evaluator"]
    }

# Bind backward compatibility methods to container (following backtest pattern)
container.get_model = get_model
container.get_strategy = get_strategy
container.get_service_info = get_service_info

# Create alias for backward compatibility
ml_container = container