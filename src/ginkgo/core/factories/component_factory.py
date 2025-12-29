# Upstream: All Modules
# Downstream: Standard Library
# Role: ComponentFactory组件工厂提供动态创建和配置组件功能支持工厂模式支持交易系统功能支持相关功能






"""
组件工厂

统一的组件创建工厂，支持策略、模型、引擎等各类组件的创建。
"""

from typing import Dict, Any, Optional, Type
from ginkgo.core.factories.base_factory import BaseFactory


class ComponentFactory(BaseFactory):
    """统一组件工厂"""
    
    def __init__(self, container=None):
        super().__init__(container)
        
        # 子工厂注册表
        self._sub_factories: Dict[str, BaseFactory] = {}
        
        # 预定义组件类型映射
        self._component_type_mapping = {
            'strategy': 'strategy_factory',
            'ml_strategy': 'strategy_factory',
            'model': 'model_factory',
            'ml_model': 'model_factory',
            'engine': 'engine_factory',
            'backtest_engine': 'engine_factory',
            'analyzer': 'analyzer_factory',
            'portfolio': 'portfolio_factory',
            'risk_manager': 'risk_factory',
            'sizer': 'sizer_factory'
        }
    
    def register_sub_factory(self, factory_type: str, factory: BaseFactory) -> None:
        """
        注册子工厂
        
        Args:
            factory_type: 工厂类型
            factory: 工厂实例
        """
        self._sub_factories[factory_type] = factory
        factory.set_container(self._container)
        self._logger.DEBUG(f"已注册子工厂: {factory_type}")
    
    def unregister_sub_factory(self, factory_type: str) -> None:
        """注销子工厂"""
        if factory_type in self._sub_factories:
            del self._sub_factories[factory_type]
            self._logger.DEBUG(f"已注销子工厂: {factory_type}")
    
    def create(self, component_type: str, **kwargs) -> Any:
        """
        创建组件实例
        
        Args:
            component_type: 组件类型
            **kwargs: 创建参数
            
        Returns:
            组件实例
        """
        # 检查是否有直接注册的组件
        if self.has_component(component_type):
            component_class = self._component_registry[component_type]
            return self._create_with_di(component_class, kwargs)
        
        # 尝试使用子工厂创建
        factory_type = self._get_factory_type(component_type)
        if factory_type and factory_type in self._sub_factories:
            sub_factory = self._sub_factories[factory_type]
            return sub_factory.create(component_type, **kwargs)
        
        # 尝试从容器获取工厂
        if self._container:
            try:
                if factory_type and self._container.has(factory_type):
                    factory = self._container.get(factory_type)
                    return factory.create(component_type, **kwargs)
            except Exception as e:
                self._logger.DEBUG(f"从容器获取工厂失败: {e}")
        
        raise ValueError(f"无法创建组件: {component_type}")
    
    def _get_factory_type(self, component_type: str) -> Optional[str]:
        """
        根据组件类型确定工厂类型
        
        Args:
            component_type: 组件类型
            
        Returns:
            工厂类型
        """
        # 直接映射
        if component_type in self._component_type_mapping:
            return self._component_type_mapping[component_type]
        
        # 模糊匹配
        for pattern, factory_type in self._component_type_mapping.items():
            if pattern in component_type.lower():
                return factory_type
        
        return None
    
    def create_strategy(self, strategy_type: str, **kwargs) -> Any:
        """创建策略实例"""
        return self.create(f"strategy_{strategy_type}", **kwargs)
    
    def create_model(self, model_type: str, **kwargs) -> Any:
        """创建模型实例"""
        return self.create(f"model_{model_type}", **kwargs)
    
    def create_engine(self, engine_type: str, **kwargs) -> Any:
        """创建引擎实例"""
        return self.create(f"engine_{engine_type}", **kwargs)
    
    def create_analyzer(self, analyzer_type: str, **kwargs) -> Any:
        """创建分析器实例"""
        return self.create(f"analyzer_{analyzer_type}", **kwargs)
    
    def create_portfolio(self, portfolio_type: str, **kwargs) -> Any:
        """创建投资组合实例"""
        return self.create(f"portfolio_{portfolio_type}", **kwargs)
    
    def batch_create(self, component_specs: list) -> Dict[str, Any]:
        """
        批量创建组件
        
        Args:
            component_specs: 组件规格列表，每个元素包含 {'type': str, 'name': str, 'params': dict}
            
        Returns:
            创建的组件字典
        """
        components = {}
        
        for spec in component_specs:
            try:
                component_type = spec['type']
                component_name = spec.get('name', component_type)
                params = spec.get('params', {})
                
                component = self.create(component_type, **params)
                components[component_name] = component
                
                self._logger.DEBUG(f"批量创建组件成功: {component_name}")
                
            except Exception as e:
                self._logger.ERROR(f"批量创建组件失败 {spec}: {e}")
                # 继续创建其他组件而不中断
        
        return components
    
    def create_from_config(self, config: Dict[str, Any]) -> Any:
        """
        根据配置创建组件
        
        Args:
            config: 组件配置
            
        Returns:
            组件实例
        """
        component_type = config.get('type')
        if not component_type:
            raise ValueError("配置中缺少组件类型")
        
        # 提取创建参数
        params = config.get('params', {})
        
        # 处理嵌套组件创建
        if 'dependencies' in config:
            for dep_name, dep_config in config['dependencies'].items():
                if isinstance(dep_config, dict) and 'type' in dep_config:
                    # 递归创建依赖组件
                    dep_component = self.create_from_config(dep_config)
                    params[dep_name] = dep_component
        
        return self.create(component_type, **params)
    
    def list_all_components(self) -> Dict[str, list]:
        """列出所有可创建的组件"""
        all_components = {
            'direct': self.list_components(),
            'sub_factories': {}
        }
        
        for factory_type, factory in self._sub_factories.items():
            all_components['sub_factories'][factory_type] = factory.list_components()
        
        return all_components
    
    def get_component_factory(self, component_type: str) -> Optional[BaseFactory]:
        """
        获取负责创建指定组件的工厂
        
        Args:
            component_type: 组件类型
            
        Returns:
            工厂实例
        """
        if self.has_component(component_type):
            return self
        
        factory_type = self._get_factory_type(component_type)
        if factory_type and factory_type in self._sub_factories:
            return self._sub_factories[factory_type]
        
        return None
    
    def set_container(self, container) -> None:
        """设置DI容器并传播到子工厂"""
        super().set_container(container)
        
        # 传播到所有子工厂
        for factory in self._sub_factories.values():
            factory.set_container(container)
    
    def get_factory_info(self) -> Dict[str, Any]:
        """获取工厂信息"""
        base_info = super().get_factory_info()
        
        sub_factory_info = {}
        for factory_type, factory in self._sub_factories.items():
            sub_factory_info[factory_type] = factory.get_factory_info()
        
        base_info.update({
            'sub_factories': sub_factory_info,
            'component_type_mappings': self._component_type_mapping
        })
        
        return base_info