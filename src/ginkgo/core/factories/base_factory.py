# Upstream: All Modules
# Downstream: Standard Library
# Role: BaseFactory基础工厂定义组件创建的抽象基类和接口支持依赖注入管理支持交易系统功能支持交易系统功能和组件集成提供完整业务支持






"""
基础工厂类

提供统一的工厂接口，支持依赖注入的组件创建。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional, List
from ginkgo.libs import GLOG


class BaseFactory(ABC):
    """基础工厂抽象类"""
    
    def __init__(self, container=None):
        """
        初始化工厂
        
        Args:
            container: DI容器实例
        """
        self._container = container
        self._component_registry: Dict[str, Type] = {}
        self._logger = GLOG
    
    def set_container(self, container) -> None:
        """设置DI容器"""
        self._container = container
    
    def register_component(self, name: str, component_class: Type) -> None:
        """
        注册组件类
        
        Args:
            name: 组件名称
            component_class: 组件类
        """
        self._component_registry[name] = component_class
        self._logger.DEBUG(f"已注册组件: {name} -> {component_class.__name__}")
    
    def unregister_component(self, name: str) -> None:
        """注销组件"""
        if name in self._component_registry:
            del self._component_registry[name]
            self._logger.DEBUG(f"已注销组件: {name}")
    
    def list_components(self) -> List[str]:
        """列出所有已注册的组件"""
        return list(self._component_registry.keys())
    
    def has_component(self, name: str) -> bool:
        """检查组件是否已注册"""
        return name in self._component_registry
    
    @abstractmethod
    def create(self, component_type: str, **kwargs) -> Any:
        """
        创建组件实例
        
        Args:
            component_type: 组件类型
            **kwargs: 创建参数
            
        Returns:
            组件实例
        """
        pass
    
    def _resolve_dependencies(self, component_class: Type) -> Dict[str, Any]:
        """
        解析组件依赖
        
        Args:
            component_class: 组件类
            
        Returns:
            依赖字典
        """
        dependencies = {}
        
        if not self._container:
            return dependencies
        
        # 检查组件类的依赖标注
        if hasattr(component_class, '__annotations__'):
            for param_name, param_type in component_class.__annotations__.items():
                if param_name == 'return':
                    continue
                
                try:
                    # 尝试从容器解析依赖
                    if self._container.has(param_name):
                        dependencies[param_name] = self._container.get(param_name)
                    elif hasattr(param_type, '__name__'):
                        # 尝试根据类型名称解析
                        type_name = param_type.__name__.lower()
                        if self._container.has(type_name):
                            dependencies[param_name] = self._container.get(type_name)
                except Exception as e:
                    self._logger.DEBUG(f"无法解析依赖 {param_name}: {e}")
        
        return dependencies
    
    def _create_with_di(self, component_class: Type, explicit_params: Dict[str, Any]) -> Any:
        """
        使用依赖注入创建组件实例
        
        Args:
            component_class: 组件类
            explicit_params: 显式参数
            
        Returns:
            组件实例
        """
        try:
            # 解析依赖
            dependencies = self._resolve_dependencies(component_class)
            
            # 合并显式参数（优先级更高）
            final_params = {**dependencies, **explicit_params}
            
            # 创建实例
            instance = component_class(**final_params)
            
            self._logger.DEBUG(f"成功创建组件实例: {component_class.__name__}")
            return instance
            
        except Exception as e:
            self._logger.ERROR(f"创建组件实例失败 {component_class.__name__}: {e}")
            raise
    
    def get_component_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取组件信息
        
        Args:
            name: 组件名称
            
        Returns:
            组件信息字典
        """
        if name not in self._component_registry:
            return None
        
        component_class = self._component_registry[name]
        
        return {
            'name': name,
            'class_name': component_class.__name__,
            'module': component_class.__module__,
            'doc': component_class.__doc__,
            'dependencies': list(getattr(component_class, '__annotations__', {}).keys())
        }
    
    def get_factory_info(self) -> Dict[str, Any]:
        """获取工厂信息"""
        return {
            'factory_class': self.__class__.__name__,
            'registered_components': len(self._component_registry),
            'has_container': self._container is not None,
            'components': list(self._component_registry.keys())
        }