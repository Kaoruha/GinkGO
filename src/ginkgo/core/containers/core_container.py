"""
Core模块DI容器

管理核心模块的依赖注入，包括适配器、工厂、工具等组件的生命周期管理。
"""

from typing import Dict, Any, Optional, Type
from ginkgo.libs.containers.base_container import BaseContainer
from ginkgo.libs import GLOG


class CoreContainer(BaseContainer):
    """
    Core模块依赖注入容器
    
    管理核心组件：
    - 适配器（Adapters）：模式转换、策略适配、模型适配
    - 工厂（Factories）：组件创建工厂
    - 工具（Utilities）：核心工具类
    - 接口（Interfaces）：统一接口定义
    """
    
    module_name = "core"
    
    def __init__(self):
        super().__init__()
        self._logger = GLOG
    
    def configure(self) -> None:
        """配置Core模块的服务和依赖关系"""
        try:
            # 适配器服务
            self._configure_adapters()
            
            # 工厂服务
            self._configure_factories()
            
            # 工具服务
            self._configure_utilities()
            
            # 验证器服务
            self._configure_validators()
            
            self._logger.DEBUG("Core模块DI容器配置完成")
            
        except Exception as e:
            self._logger.ERROR(f"Core模块DI容器配置失败: {e}")
            raise
    
    def _configure_adapters(self) -> None:
        """配置适配器服务"""
        # 基础适配器
        self.bind(
            "base_adapter",
            self._get_base_adapter_class,
            singleton=False
        )
        
        # 模式适配器
        self.bind(
            "mode_adapter", 
            self._get_mode_adapter_class,
            singleton=True
        )
        
        # 策略适配器
        self.bind(
            "strategy_adapter",
            self._get_strategy_adapter_class,
            dependencies=["mode_adapter"],
            singleton=True
        )
        
        # 模型适配器
        self.bind(
            "model_adapter",
            self._get_model_adapter_class,
            singleton=True
        )
        
        # 复合适配器
        self.bind(
            "composite_adapter",
            self._get_composite_adapter_class,
            dependencies=["strategy_adapter", "model_adapter"],
            singleton=True
        )
        
        # 链式适配器
        self.bind(
            "chainable_adapter",
            self._get_chainable_adapter_class,
            singleton=False
        )
        
        # 条件适配器
        self.bind(
            "conditional_adapter",
            self._get_conditional_adapter_class,
            singleton=False
        )
    
    def _configure_factories(self) -> None:
        """配置工厂服务"""
        # 策略工厂
        self.bind(
            "strategy_factory",
            self._get_strategy_factory_class,
            dependencies=["strategy_adapter"],
            singleton=True
        )
        
        # 模型工厂
        self.bind(
            "model_factory", 
            self._get_model_factory_class,
            dependencies=["model_adapter"],
            singleton=True
        )
        
        # 引擎工厂
        self.bind(
            "engine_factory",
            self._get_engine_factory_class,
            dependencies=["strategy_factory"],
            singleton=True
        )
        
        # 组合工厂
        self.bind(
            "component_factory",
            self._get_component_factory_class,
            dependencies=["strategy_factory", "model_factory", "engine_factory"],
            singleton=True
        )
    
    def _configure_utilities(self) -> None:
        """配置工具服务"""
        # 性能监控器
        self.bind(
            "performance_monitor",
            self._get_performance_monitor_class,
            singleton=True
        )
        
        # 配置管理器
        self.bind(
            "config_manager",
            self._get_config_manager_class,
            singleton=True
        )
        
        # 缓存管理器
        self.bind(
            "cache_manager",
            self._get_cache_manager_class,
            singleton=True
        )
        
        # 错误处理器
        self.bind(
            "error_handler",
            self._get_error_handler_class,
            singleton=True
        )
        
        # 日志管理器
        self.bind(
            "logger_manager",
            self._get_logger_manager_class,
            singleton=True
        )
    
    def _configure_validators(self) -> None:
        """配置验证器服务"""
        # 策略验证器
        self.bind(
            "strategy_validator",
            self._get_strategy_validator_class,
            singleton=True
        )
        
        # 模型验证器  
        self.bind(
            "model_validator",
            self._get_model_validator_class,
            singleton=True
        )
        
        # 数据验证器
        self.bind(
            "data_validator",
            self._get_data_validator_class,
            singleton=True
        )
        
        # 配置验证器
        self.bind(
            "config_validator",
            self._get_config_validator_class,
            singleton=True
        )
    
    # 适配器类获取方法
    def _get_base_adapter_class(self) -> Type:
        """获取基础适配器类"""
        from ginkgo.core.adapters.base_adapter import BaseAdapter
        return BaseAdapter
    
    def _get_mode_adapter_class(self) -> Type:
        """获取模式适配器类"""
        from ginkgo.core.adapters.mode_adapter import ModeAdapter
        return ModeAdapter
    
    def _get_strategy_adapter_class(self) -> Type:
        """获取策略适配器类"""
        from ginkgo.core.adapters.strategy_adapter import StrategyAdapter
        return StrategyAdapter
    
    def _get_model_adapter_class(self) -> Type:
        """获取模型适配器类"""
        from ginkgo.core.adapters.model_adapter import ModelAdapter
        return ModelAdapter
    
    def _get_composite_adapter_class(self) -> Type:
        """获取复合适配器类"""
        from ginkgo.core.adapters.base_adapter import CompositeAdapter
        return CompositeAdapter
    
    def _get_chainable_adapter_class(self) -> Type:
        """获取链式适配器类"""
        from ginkgo.core.adapters.base_adapter import ChainableAdapter
        return ChainableAdapter
    
    def _get_conditional_adapter_class(self) -> Type:
        """获取条件适配器类"""
        from ginkgo.core.adapters.base_adapter import ConditionalAdapter
        return ConditionalAdapter
    
    # 工厂类获取方法
    def _get_strategy_factory_class(self) -> Type:
        """获取策略工厂类"""
        from ginkgo.core.factories.strategy_factory import StrategyFactory
        return StrategyFactory
    
    def _get_model_factory_class(self) -> Type:
        """获取模型工厂类"""
        from ginkgo.core.factories.model_factory import ModelFactory
        return ModelFactory
    
    def _get_engine_factory_class(self) -> Type:
        """获取引擎工厂类"""  
        from ginkgo.core.factories.engine_factory import EngineFactory
        return EngineFactory
    
    def _get_component_factory_class(self) -> Type:
        """获取组件工厂类"""
        from ginkgo.core.factories.component_factory import ComponentFactory
        return ComponentFactory
    
    # 工具类获取方法
    def _get_performance_monitor_class(self) -> Type:
        """获取性能监控器类"""
        from ginkgo.core.utils.performance_monitor import PerformanceMonitor
        return PerformanceMonitor
    
    def _get_config_manager_class(self) -> Type:
        """获取配置管理器类"""
        from ginkgo.core.utils.config_manager import ConfigManager
        return ConfigManager
    
    def _get_cache_manager_class(self) -> Type:
        """获取缓存管理器类"""
        from ginkgo.core.utils.cache_manager import CacheManager
        return CacheManager
    
    def _get_error_handler_class(self) -> Type:
        """获取错误处理器类"""
        from ginkgo.core.utils.error_handler import ErrorHandler
        return ErrorHandler
    
    def _get_logger_manager_class(self) -> Type:
        """获取日志管理器类"""
        from ginkgo.core.utils.logger_manager import LoggerManager
        return LoggerManager
    
    # 验证器类获取方法
    def _get_strategy_validator_class(self) -> Type:
        """获取策略验证器类"""
        from ginkgo.core.validators.strategy_validator import StrategyValidator
        return StrategyValidator
    
    def _get_model_validator_class(self) -> Type:
        """获取模型验证器类"""
        from ginkgo.core.validators.model_validator import ModelValidator
        return ModelValidator
    
    def _get_data_validator_class(self) -> Type:
        """获取数据验证器类"""
        from ginkgo.core.validators.data_validator import DataValidator
        return DataValidator
    
    def _get_config_validator_class(self) -> Type:
        """获取配置验证器类"""
        from ginkgo.core.validators.config_validator import ConfigValidator
        return ConfigValidator
    
    def get_adapter(self, adapter_type: str) -> Any:
        """
        获取指定类型的适配器
        
        Args:
            adapter_type: 适配器类型
            
        Returns:
            适配器实例
        """
        adapter_mapping = {
            'mode': 'mode_adapter',
            'strategy': 'strategy_adapter', 
            'model': 'model_adapter',
            'composite': 'composite_adapter',
            'chainable': 'chainable_adapter',
            'conditional': 'conditional_adapter'
        }
        
        service_name = adapter_mapping.get(adapter_type)
        if not service_name:
            raise ValueError(f"未知的适配器类型: {adapter_type}")
            
        return self.get(service_name)
    
    def get_factory(self, factory_type: str) -> Any:
        """
        获取指定类型的工厂
        
        Args:
            factory_type: 工厂类型
            
        Returns:
            工厂实例
        """
        factory_mapping = {
            'strategy': 'strategy_factory',
            'model': 'model_factory',
            'engine': 'engine_factory',
            'component': 'component_factory'
        }
        
        service_name = factory_mapping.get(factory_type)
        if not service_name:
            raise ValueError(f"未知的工厂类型: {factory_type}")
            
        return self.get(service_name)
    
    def get_utility(self, utility_type: str) -> Any:
        """
        获取指定类型的工具
        
        Args:
            utility_type: 工具类型
            
        Returns:
            工具实例
        """
        utility_mapping = {
            'performance': 'performance_monitor',
            'config': 'config_manager',
            'cache': 'cache_manager',
            'error': 'error_handler',
            'logger': 'logger_manager'
        }
        
        service_name = utility_mapping.get(utility_type)
        if not service_name:
            raise ValueError(f"未知的工具类型: {utility_type}")
            
        return self.get(service_name)
    
    def get_validator(self, validator_type: str) -> Any:
        """
        获取指定类型的验证器
        
        Args:
            validator_type: 验证器类型
            
        Returns:
            验证器实例
        """
        validator_mapping = {
            'strategy': 'strategy_validator',
            'model': 'model_validator',
            'data': 'data_validator',
            'config': 'config_validator'
        }
        
        service_name = validator_mapping.get(validator_type)
        if not service_name:
            raise ValueError(f"未知的验证器类型: {validator_type}")
            
        return self.get(service_name)
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "module": self.module_name,
            "state": self.state.value,
            "services": {
                "adapters": [
                    "mode_adapter", "strategy_adapter", "model_adapter",
                    "composite_adapter", "chainable_adapter", "conditional_adapter"
                ],
                "factories": [
                    "strategy_factory", "model_factory", "engine_factory", "component_factory"
                ],
                "utilities": [
                    "performance_monitor", "config_manager", "cache_manager",
                    "error_handler", "logger_manager"
                ],
                "validators": [
                    "strategy_validator", "model_validator", "data_validator", "config_validator"
                ]
            },
            "total_services": len(self.list_services())
        }


# 创建全局Core容器实例
core_container = CoreContainer()

# 禁用自动注册以避免与新容器冲突
# TODO: 在完成迁移到新容器后移除此旧容器
# try:
#     from ginkgo.libs.containers.container_registry import registry
#     registry.register(core_container)
#     GLOG.DEBUG("Core容器已注册到全局注册表")
# except ImportError as e:
#     GLOG.WARN(f"Core容器注册失败: {e}")