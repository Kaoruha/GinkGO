"""
ML模块DI容器

管理机器学习模块的依赖注入，包括模型、策略、数据处理等组件的生命周期管理。
"""

from typing import Dict, Any, Optional, Type
from ginkgo.libs.containers.base_container import BaseContainer
from ginkgo.libs import GLOG


class MLContainer(BaseContainer):
    """
    ML模块依赖注入容器
    
    管理ML组件：
    - 模型（Models）：各种ML模型实现
    - 策略（Strategies）：ML策略实现
    - 数据处理（Data Processing）：特征工程、数据预处理
    - 训练器（Trainers）：模型训练管理
    - 评估器（Evaluators）：模型评估工具
    """
    
    module_name = "quant_ml"
    
    def __init__(self):
        super().__init__()
        self._logger = GLOG
    
    def configure(self) -> None:
        """配置ML模块的服务和依赖关系"""
        try:
            # 模型服务
            self._configure_models()
            
            # 策略服务
            self._configure_strategies()
            
            # 数据处理服务
            self._configure_data_processing()
            
            # 训练器服务
            self._configure_trainers()
            
            # 评估器服务
            self._configure_evaluators()
            
            # 工具服务
            self._configure_utilities()
            
            self._logger.DEBUG("ML模块DI容器配置完成")
            
        except Exception as e:
            self._logger.ERROR(f"ML模块DI容器配置失败: {e}")
            raise
    
    def _configure_models(self) -> None:
        """配置模型服务"""
        # 基础ML模型
        self.bind(
            "base_ml_model",
            self._get_base_ml_model_class,
            singleton=False
        )
        
        # Sklearn模型
        self.bind(
            "sklearn_model",
            self._get_sklearn_model_class,
            singleton=False
        )
        
        # XGBoost模型
        self.bind(
            "xgboost_model",
            self._get_xgboost_model_class,
            singleton=False
        )
        
        # LightGBM模型
        self.bind(
            "lightgbm_model",
            self._get_lightgbm_model_class,
            singleton=False
        )
        
        # PyTorch模型
        self.bind(
            "pytorch_model",
            self._get_pytorch_model_class,
            singleton=False
        )
        
        # TensorFlow模型
        self.bind(
            "tensorflow_model",
            self._get_tensorflow_model_class,
            singleton=False
        )
        
        # 时间序列模型
        self.bind(
            "timeseries_model",
            self._get_timeseries_model_class,
            singleton=False
        )
        
        # 集成模型
        self.bind(
            "ensemble_model",
            self._get_ensemble_model_class,
            dependencies=["base_ml_model"],
            singleton=False
        )
        
        # 模型注册表
        self.bind(
            "model_registry",
            self._get_model_registry_class,
            singleton=True
        )
    
    def _configure_strategies(self) -> None:
        """配置策略服务"""
        # 基础ML策略
        self.bind(
            "base_ml_strategy",
            self._get_base_ml_strategy_class,
            dependencies=["base_ml_model"],
            singleton=False
        )
        
        # 回归策略
        self.bind(
            "regression_strategy",
            self._get_regression_strategy_class,
            dependencies=["sklearn_model"],
            singleton=False
        )
        
        # 分类策略
        self.bind(
            "classification_strategy",
            self._get_classification_strategy_class,
            dependencies=["sklearn_model"],
            singleton=False
        )
        
        # 深度学习策略
        self.bind(
            "deep_learning_strategy",
            self._get_deep_learning_strategy_class,
            dependencies=["pytorch_model"],
            singleton=False
        )
        
        # 强化学习策略
        self.bind(
            "reinforcement_strategy",
            self._get_reinforcement_strategy_class,
            dependencies=["pytorch_model"],
            singleton=False
        )
        
        # 策略组合器
        self.bind(
            "strategy_ensemble",
            self._get_strategy_ensemble_class,
            dependencies=["base_ml_strategy"],
            singleton=False
        )
    
    def _configure_data_processing(self) -> None:
        """配置数据处理服务"""
        # 特征工程器
        self.bind(
            "feature_engineer",
            self._get_feature_engineer_class,
            singleton=True
        )
        
        # 数据预处理器
        self.bind(
            "data_preprocessor",
            self._get_data_preprocessor_class,
            singleton=True
        )
        
        # 数据标准化器
        self.bind(
            "data_normalizer",
            self._get_data_normalizer_class,
            singleton=True
        )
        
        # 特征选择器
        self.bind(
            "feature_selector",
            self._get_feature_selector_class,
            singleton=True
        )
        
        # 数据分割器
        self.bind(
            "data_splitter",
            self._get_data_splitter_class,
            singleton=True
        )
        
        # 数据增强器
        self.bind(
            "data_augmenter",
            self._get_data_augmenter_class,
            singleton=True
        )
    
    def _configure_trainers(self) -> None:
        """配置训练器服务"""
        # 基础训练器
        self.bind(
            "base_trainer",
            self._get_base_trainer_class,
            dependencies=["data_preprocessor"],
            singleton=False
        )
        
        # 批量训练器
        self.bind(
            "batch_trainer",
            self._get_batch_trainer_class,
            dependencies=["base_trainer"],
            singleton=False
        )
        
        # 在线训练器
        self.bind(
            "online_trainer",
            self._get_online_trainer_class,
            dependencies=["base_trainer"],
            singleton=False
        )
        
        # 分布式训练器
        self.bind(
            "distributed_trainer",
            self._get_distributed_trainer_class,
            dependencies=["base_trainer"],
            singleton=False
        )
        
        # 超参数优化器
        self.bind(
            "hyperparameter_optimizer",
            self._get_hyperparameter_optimizer_class,
            dependencies=["base_trainer"],
            singleton=True
        )
        
        # 训练管理器
        self.bind(
            "training_manager",
            self._get_training_manager_class,
            dependencies=["base_trainer", "hyperparameter_optimizer"],
            singleton=True
        )
    
    def _configure_evaluators(self) -> None:
        """配置评估器服务"""
        # 模型评估器
        self.bind(
            "model_evaluator",
            self._get_model_evaluator_class,
            singleton=True
        )
        
        # 交叉验证器
        self.bind(
            "cross_validator",
            self._get_cross_validator_class,
            dependencies=["model_evaluator"],
            singleton=True
        )
        
        # 回测评估器
        self.bind(
            "backtest_evaluator",
            self._get_backtest_evaluator_class,
            dependencies=["model_evaluator"],
            singleton=True
        )
        
        # 风险评估器
        self.bind(
            "risk_evaluator",
            self._get_risk_evaluator_class,
            singleton=True
        )
        
        # 性能分析器
        self.bind(
            "performance_analyzer",
            self._get_performance_analyzer_class,
            dependencies=["model_evaluator"],
            singleton=True
        )
    
    def _configure_utilities(self) -> None:
        """配置工具服务"""
        # 模型序列化器
        self.bind(
            "model_serializer",
            self._get_model_serializer_class,
            singleton=True
        )
        
        # 实验跟踪器
        self.bind(
            "experiment_tracker",
            self._get_experiment_tracker_class,
            singleton=True
        )
        
        # 模型监控器
        self.bind(
            "model_monitor",
            self._get_model_monitor_class,
            singleton=True
        )
        
        # GPU管理器
        self.bind(
            "gpu_manager",
            self._get_gpu_manager_class,
            singleton=True
        )
        
        # 资源管理器
        self.bind(
            "resource_manager",
            self._get_resource_manager_class,
            dependencies=["gpu_manager"],
            singleton=True
        )
    
    # 模型类获取方法
    def _get_base_ml_model_class(self) -> Type:
        """获取基础ML模型类"""
        from ginkgo.quant_ml.models.base_model import BaseMLModel
        return BaseMLModel
    
    def _get_sklearn_model_class(self) -> Type:
        """获取Sklearn模型类"""
        from ginkgo.quant_ml.models.sklearn_model import SklearnModel
        return SklearnModel
    
    def _get_xgboost_model_class(self) -> Type:
        """获取XGBoost模型类"""
        from ginkgo.quant_ml.models.xgboost_model import XGBoostModel
        return XGBoostModel
    
    def _get_lightgbm_model_class(self) -> Type:
        """获取LightGBM模型类"""
        from ginkgo.quant_ml.models.lightgbm_model import LightGBMModel
        return LightGBMModel
    
    def _get_pytorch_model_class(self) -> Type:
        """获取PyTorch模型类"""
        from ginkgo.quant_ml.models.pytorch_model import PyTorchModel
        return PyTorchModel
    
    def _get_tensorflow_model_class(self) -> Type:
        """获取TensorFlow模型类"""
        from ginkgo.quant_ml.models.tensorflow_model import TensorFlowModel
        return TensorFlowModel
    
    def _get_timeseries_model_class(self) -> Type:
        """获取时间序列模型类"""
        from ginkgo.quant_ml.models.timeseries_model import TimeSeriesModel
        return TimeSeriesModel
    
    def _get_ensemble_model_class(self) -> Type:
        """获取集成模型类"""
        from ginkgo.quant_ml.models.ensemble_model import EnsembleModel
        return EnsembleModel
    
    def _get_model_registry_class(self) -> Type:
        """获取模型注册表类"""
        from ginkgo.quant_ml.utils.model_registry import ModelRegistry
        return ModelRegistry
    
    # 策略类获取方法
    def _get_base_ml_strategy_class(self) -> Type:
        """获取基础ML策略类"""
        from ginkgo.quant_ml.strategies.base_ml_strategy import BaseMLStrategy
        return BaseMLStrategy
    
    def _get_regression_strategy_class(self) -> Type:
        """获取回归策略类"""
        from ginkgo.quant_ml.strategies.regression_strategy import RegressionStrategy
        return RegressionStrategy
    
    def _get_classification_strategy_class(self) -> Type:
        """获取分类策略类"""
        from ginkgo.quant_ml.strategies.classification_strategy import ClassificationStrategy
        return ClassificationStrategy
    
    def _get_deep_learning_strategy_class(self) -> Type:
        """获取深度学习策略类"""
        from ginkgo.quant_ml.strategies.deep_learning_strategy import DeepLearningStrategy
        return DeepLearningStrategy
    
    def _get_reinforcement_strategy_class(self) -> Type:
        """获取强化学习策略类"""
        from ginkgo.quant_ml.strategies.reinforcement_strategy import ReinforcementStrategy
        return ReinforcementStrategy
    
    def _get_strategy_ensemble_class(self) -> Type:
        """获取策略组合器类"""
        from ginkgo.quant_ml.strategies.strategy_ensemble import StrategyEnsemble
        return StrategyEnsemble
    
    # 数据处理类获取方法
    def _get_feature_engineer_class(self) -> Type:
        """获取特征工程器类"""
        from ginkgo.quant_ml.data.feature_engineer import FeatureEngineer
        return FeatureEngineer
    
    def _get_data_preprocessor_class(self) -> Type:
        """获取数据预处理器类"""
        from ginkgo.quant_ml.data.data_preprocessor import DataPreprocessor
        return DataPreprocessor
    
    def _get_data_normalizer_class(self) -> Type:
        """获取数据标准化器类"""
        from ginkgo.quant_ml.data.data_normalizer import DataNormalizer
        return DataNormalizer
    
    def _get_feature_selector_class(self) -> Type:
        """获取特征选择器类"""
        from ginkgo.quant_ml.data.feature_selector import FeatureSelector
        return FeatureSelector
    
    def _get_data_splitter_class(self) -> Type:
        """获取数据分割器类"""
        from ginkgo.quant_ml.data.data_splitter import DataSplitter
        return DataSplitter
    
    def _get_data_augmenter_class(self) -> Type:
        """获取数据增强器类"""
        from ginkgo.quant_ml.data.data_augmenter import DataAugmenter
        return DataAugmenter
    
    # 训练器类获取方法
    def _get_base_trainer_class(self) -> Type:
        """获取基础训练器类"""
        from ginkgo.quant_ml.training.base_trainer import BaseTrainer
        return BaseTrainer
    
    def _get_batch_trainer_class(self) -> Type:
        """获取批量训练器类"""
        from ginkgo.quant_ml.training.batch_trainer import BatchTrainer
        return BatchTrainer
    
    def _get_online_trainer_class(self) -> Type:
        """获取在线训练器类"""
        from ginkgo.quant_ml.training.online_trainer import OnlineTrainer
        return OnlineTrainer
    
    def _get_distributed_trainer_class(self) -> Type:
        """获取分布式训练器类"""
        from ginkgo.quant_ml.training.distributed_trainer import DistributedTrainer
        return DistributedTrainer
    
    def _get_hyperparameter_optimizer_class(self) -> Type:
        """获取超参数优化器类"""
        from ginkgo.quant_ml.training.hyperparameter_optimizer import HyperparameterOptimizer
        return HyperparameterOptimizer
    
    def _get_training_manager_class(self) -> Type:
        """获取训练管理器类"""
        from ginkgo.quant_ml.training.training_manager import TrainingManager
        return TrainingManager
    
    # 评估器类获取方法
    def _get_model_evaluator_class(self) -> Type:
        """获取模型评估器类"""
        from ginkgo.quant_ml.evaluation.model_evaluator import ModelEvaluator
        return ModelEvaluator
    
    def _get_cross_validator_class(self) -> Type:
        """获取交叉验证器类"""
        from ginkgo.quant_ml.evaluation.cross_validator import CrossValidator
        return CrossValidator
    
    def _get_backtest_evaluator_class(self) -> Type:
        """获取回测评估器类"""
        from ginkgo.quant_ml.evaluation.backtest_evaluator import BacktestEvaluator
        return BacktestEvaluator
    
    def _get_risk_evaluator_class(self) -> Type:
        """获取风险评估器类"""
        from ginkgo.quant_ml.evaluation.risk_evaluator import RiskEvaluator
        return RiskEvaluator
    
    def _get_performance_analyzer_class(self) -> Type:
        """获取性能分析器类"""
        from ginkgo.quant_ml.evaluation.performance_analyzer import PerformanceAnalyzer
        return PerformanceAnalyzer
    
    # 工具类获取方法
    def _get_model_serializer_class(self) -> Type:
        """获取模型序列化器类"""
        from ginkgo.quant_ml.utils.model_serializer import ModelSerializer
        return ModelSerializer
    
    def _get_experiment_tracker_class(self) -> Type:
        """获取实验跟踪器类"""
        from ginkgo.quant_ml.utils.experiment_tracker import ExperimentTracker
        return ExperimentTracker
    
    def _get_model_monitor_class(self) -> Type:
        """获取模型监控器类"""
        from ginkgo.quant_ml.utils.model_monitor import ModelMonitor
        return ModelMonitor
    
    def _get_gpu_manager_class(self) -> Type:
        """获取GPU管理器类"""
        from ginkgo.quant_ml.utils.gpu_manager import GPUManager
        return GPUManager
    
    def _get_resource_manager_class(self) -> Type:
        """获取资源管理器类"""
        from ginkgo.quant_ml.utils.resource_manager import ResourceManager
        return ResourceManager
    
    def get_model(self, model_type: str) -> Any:
        """
        获取指定类型的模型
        
        Args:
            model_type: 模型类型
            
        Returns:
            模型实例
        """
        model_mapping = {
            'base': 'base_ml_model',
            'sklearn': 'sklearn_model',
            'xgboost': 'xgboost_model', 
            'lightgbm': 'lightgbm_model',
            'pytorch': 'pytorch_model',
            'tensorflow': 'tensorflow_model',
            'timeseries': 'timeseries_model',
            'ensemble': 'ensemble_model'
        }
        
        service_name = model_mapping.get(model_type)
        if not service_name:
            raise ValueError(f"未知的模型类型: {model_type}")
            
        return self.get(service_name)
    
    def get_strategy(self, strategy_type: str) -> Any:
        """
        获取指定类型的策略
        
        Args:
            strategy_type: 策略类型
            
        Returns:
            策略实例
        """
        strategy_mapping = {
            'base': 'base_ml_strategy',
            'regression': 'regression_strategy',
            'classification': 'classification_strategy',
            'deep_learning': 'deep_learning_strategy',
            'reinforcement': 'reinforcement_strategy',
            'ensemble': 'strategy_ensemble'
        }
        
        service_name = strategy_mapping.get(strategy_type)
        if not service_name:
            raise ValueError(f"未知的策略类型: {strategy_type}")
            
        return self.get(service_name)
    
    def get_data_processor(self, processor_type: str) -> Any:
        """
        获取指定类型的数据处理器
        
        Args:
            processor_type: 处理器类型
            
        Returns:
            处理器实例
        """
        processor_mapping = {
            'feature_engineer': 'feature_engineer',
            'preprocessor': 'data_preprocessor',
            'normalizer': 'data_normalizer',
            'selector': 'feature_selector',
            'splitter': 'data_splitter',
            'augmenter': 'data_augmenter'
        }
        
        service_name = processor_mapping.get(processor_type)
        if not service_name:
            raise ValueError(f"未知的数据处理器类型: {processor_type}")
            
        return self.get(service_name)
    
    def get_trainer(self, trainer_type: str) -> Any:
        """
        获取指定类型的训练器
        
        Args:
            trainer_type: 训练器类型
            
        Returns:
            训练器实例
        """
        trainer_mapping = {
            'base': 'base_trainer',
            'batch': 'batch_trainer',
            'online': 'online_trainer',
            'distributed': 'distributed_trainer',
            'manager': 'training_manager'
        }
        
        service_name = trainer_mapping.get(trainer_type)
        if not service_name:
            raise ValueError(f"未知的训练器类型: {trainer_type}")
            
        return self.get(service_name)
    
    def get_evaluator(self, evaluator_type: str) -> Any:
        """
        获取指定类型的评估器
        
        Args:
            evaluator_type: 评估器类型
            
        Returns:
            评估器实例
        """
        evaluator_mapping = {
            'model': 'model_evaluator',
            'cross_validator': 'cross_validator',
            'backtest': 'backtest_evaluator',
            'risk': 'risk_evaluator',
            'performance': 'performance_analyzer'
        }
        
        service_name = evaluator_mapping.get(evaluator_type)
        if not service_name:
            raise ValueError(f"未知的评估器类型: {evaluator_type}")
            
        return self.get(service_name)
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "module": self.module_name,
            "state": self.state.value,
            "services": {
                "models": [
                    "base_ml_model", "sklearn_model", "xgboost_model", "lightgbm_model",
                    "pytorch_model", "tensorflow_model", "timeseries_model", "ensemble_model"
                ],
                "strategies": [
                    "base_ml_strategy", "regression_strategy", "classification_strategy",
                    "deep_learning_strategy", "reinforcement_strategy", "strategy_ensemble"
                ],
                "data_processing": [
                    "feature_engineer", "data_preprocessor", "data_normalizer",
                    "feature_selector", "data_splitter", "data_augmenter"
                ],
                "trainers": [
                    "base_trainer", "batch_trainer", "online_trainer",
                    "distributed_trainer", "hyperparameter_optimizer", "training_manager"
                ],
                "evaluators": [
                    "model_evaluator", "cross_validator", "backtest_evaluator",
                    "risk_evaluator", "performance_analyzer"
                ],
                "utilities": [
                    "model_serializer", "experiment_tracker", "model_monitor",
                    "gpu_manager", "resource_manager"
                ]
            },
            "total_services": len(self.list_services())
        }


# 创建全局ML容器实例
ml_container = MLContainer()

# 自动注册到全局容器注册表
try:
    from ginkgo.libs.containers.container_registry import registry
    registry.register(ml_container)
    GLOG.DEBUG("ML容器已注册到全局注册表")
except ImportError as e:
    GLOG.WARNING(f"ML容器注册失败: {e}")