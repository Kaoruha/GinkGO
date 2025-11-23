"""
基础适配器类

提供适配器模式的基础实现，定义所有适配器的通用接口和行为。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from datetime import datetime

from ginkgo.libs import GLOG

T = TypeVar('T')


class AdapterError(Exception):
    """适配器异常"""
    pass


class BaseAdapter(ABC):
    """基础适配器抽象类"""
    
    def __init__(self, name: str = "BaseAdapter"):
        self.name = name
        self.created_at = datetime.now()
        self.adapted_count = 0
        self._error_count = 0
        self._error_log = []
        
    @property
    def error_count(self) -> int:
        """错误计数"""
        return self._error_count
    
    @property
    def error_log(self) -> List[Dict[str, Any]]:
        """错误日志"""
        return self._error_log
    
    @abstractmethod
    def adapt(self, source: Any, target_type: Type[T] = None, **kwargs) -> T:
        """
        适配方法 - 将源对象适配为目标类型
        
        Args:
            source: 源对象
            target_type: 目标类型
            **kwargs: 适配参数
            
        Returns:
            T: 适配后的对象
            
        Raises:
            AdapterError: 适配失败时抛出
        """
        pass
    
    @abstractmethod
    def can_adapt(self, source: Any, target_type: Type = None) -> bool:
        """
        检查是否可以适配
        
        Args:
            source: 源对象
            target_type: 目标类型
            
        Returns:
            bool: 是否可以适配
        """
        pass
    
    def validate_source(self, source: Any) -> bool:
        """
        验证源对象有效性
        
        Args:
            source: 源对象
            
        Returns:
            bool: 是否有效
        """
        return source is not None
    
    def validate_target_type(self, target_type: Type) -> bool:
        """
        验证目标类型有效性
        
        Args:
            target_type: 目标类型
            
        Returns:
            bool: 是否有效
        """
        return target_type is not None
    
    def log_adaptation(self, source: Any, target: Any, success: bool = True, error: str = None) -> None:
        """
        记录适配过程
        
        Args:
            source: 源对象
            target: 目标对象
            success: 是否成功
            error: 错误信息
        """
        if success:
            self.adapted_count += 1
            GLOG.DEBUG(f"适配器 {self.name} 成功适配: {type(source).__name__} -> {type(target).__name__}")
        else:
            self._error_count += 1
            error_record = {
                'timestamp': datetime.now(),
                'source_type': type(source).__name__,
                'error': error or "Unknown error",
                'source_repr': str(source)[:100]  # 限制长度避免日志过长
            }
            self._error_log.append(error_record)
            GLOG.ERROR(f"适配器 {self.name} 适配失败: {error}")
    
    def clear_error_log(self) -> None:
        """清空错误日志"""
        self._error_log.clear()
        self._error_count = 0
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """获取适配统计信息"""
        return {
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'adapted_count': self.adapted_count,
            'error_count': self._error_count,
            'success_rate': self.adapted_count / (self.adapted_count + self._error_count) if (self.adapted_count + self._error_count) > 0 else 0.0,
            'recent_errors': self._error_log[-5:] if self._error_log else []  # 最近5个错误
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.adapted_count = 0
        self.clear_error_log()
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, adapted={self.adapted_count}, errors={self._error_count})"
    
    def __repr__(self) -> str:
        return self.__str__()


class ChainableAdapter(BaseAdapter):
    """可链式调用的适配器"""
    
    def __init__(self, name: str = "ChainableAdapter"):
        super().__init__(name)
        self._next_adapter = None
    
    def set_next(self, adapter: 'BaseAdapter') -> 'BaseAdapter':
        """设置下一个适配器"""
        self._next_adapter = adapter
        return adapter
    
    def adapt_chain(self, source: Any, target_type: Type[T] = None, **kwargs) -> T:
        """
        链式适配
        
        Args:
            source: 源对象
            target_type: 最终目标类型
            **kwargs: 适配参数
            
        Returns:
            T: 适配后的对象
        """
        try:
            # 首先尝试当前适配器
            if self.can_adapt(source, target_type):
                result = self.adapt(source, target_type, **kwargs)
                self.log_adaptation(source, result, success=True)
                return result
            
            # 如果当前适配器无法处理，尝试下一个
            if self._next_adapter is not None:
                return self._next_adapter.adapt_chain(source, target_type, **kwargs)
            
            # 没有可用的适配器
            raise AdapterError(f"无法将 {type(source).__name__} 适配为 {target_type.__name__ if target_type else 'Unknown'}")
            
        except Exception as e:
            self.log_adaptation(source, None, success=False, error=str(e))
            raise AdapterError(f"链式适配失败: {e}")


class CompositeAdapter(BaseAdapter):
    """组合适配器 - 可以包含多个子适配器"""
    
    def __init__(self, name: str = "CompositeAdapter"):
        super().__init__(name)
        self._sub_adapters = []
    
    def add_adapter(self, adapter: BaseAdapter) -> None:
        """添加子适配器"""
        if adapter not in self._sub_adapters:
            self._sub_adapters.append(adapter)
    
    def remove_adapter(self, adapter: BaseAdapter) -> bool:
        """移除子适配器"""
        if adapter in self._sub_adapters:
            self._sub_adapters.remove(adapter)
            return True
        return False
    
    def can_adapt(self, source: Any, target_type: Type = None) -> bool:
        """检查是否有任何子适配器可以处理"""
        return any(adapter.can_adapt(source, target_type) for adapter in self._sub_adapters)
    
    def adapt(self, source: Any, target_type: Type[T] = None, **kwargs) -> T:
        """
        使用第一个可用的子适配器进行适配
        
        Args:
            source: 源对象
            target_type: 目标类型
            **kwargs: 适配参数
            
        Returns:
            T: 适配后的对象
        """
        for adapter in self._sub_adapters:
            if adapter.can_adapt(source, target_type):
                try:
                    result = adapter.adapt(source, target_type, **kwargs)
                    self.log_adaptation(source, result, success=True)
                    return result
                except Exception as e:
                    GLOG.WARN(f"子适配器 {adapter.name} 适配失败: {e}")
                    continue
        
        error_msg = f"所有子适配器都无法将 {type(source).__name__} 适配为 {target_type.__name__ if target_type else 'Unknown'}"
        self.log_adaptation(source, None, success=False, error=error_msg)
        raise AdapterError(error_msg)
    
    def get_sub_adapter_stats(self) -> List[Dict[str, Any]]:
        """获取所有子适配器的统计信息"""
        return [adapter.get_adaptation_stats() for adapter in self._sub_adapters]
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """获取组合适配器的统计信息"""
        stats = super().get_adaptation_stats()
        stats['sub_adapters_count'] = len(self._sub_adapters)
        stats['sub_adapters'] = self.get_sub_adapter_stats()
        return stats


class ConditionalAdapter(BaseAdapter):
    """条件适配器 - 根据条件选择适配策略"""
    
    def __init__(self, name: str = "ConditionalAdapter"):
        super().__init__(name)
        self._conditions = []  # [(condition_func, adapter), ...]
        self._default_adapter = None
    
    def add_condition(self, condition_func, adapter: BaseAdapter) -> None:
        """
        添加条件和对应的适配器
        
        Args:
            condition_func: 条件函数，接受(source, target_type)参数，返回bool
            adapter: 满足条件时使用的适配器
        """
        self._conditions.append((condition_func, adapter))
    
    def set_default_adapter(self, adapter: BaseAdapter) -> None:
        """设置默认适配器"""
        self._default_adapter = adapter
    
    def can_adapt(self, source: Any, target_type: Type = None) -> bool:
        """检查是否可以适配"""
        # 检查条件适配器
        for condition_func, adapter in self._conditions:
            if condition_func(source, target_type) and adapter.can_adapt(source, target_type):
                return True
        
        # 检查默认适配器
        if self._default_adapter and self._default_adapter.can_adapt(source, target_type):
            return True
        
        return False
    
    def adapt(self, source: Any, target_type: Type[T] = None, **kwargs) -> T:
        """
        根据条件选择适配器进行适配
        
        Args:
            source: 源对象
            target_type: 目标类型
            **kwargs: 适配参数
            
        Returns:
            T: 适配后的对象
        """
        # 检查条件适配器
        for condition_func, adapter in self._conditions:
            if condition_func(source, target_type):
                try:
                    result = adapter.adapt(source, target_type, **kwargs)
                    self.log_adaptation(source, result, success=True)
                    return result
                except Exception as e:
                    GLOG.WARN(f"条件适配器 {adapter.name} 适配失败: {e}")
                    continue
        
        # 使用默认适配器
        if self._default_adapter:
            try:
                result = self._default_adapter.adapt(source, target_type, **kwargs)
                self.log_adaptation(source, result, success=True)
                return result
            except Exception as e:
                GLOG.WARN(f"默认适配器 {self._default_adapter.name} 适配失败: {e}")
        
        error_msg = f"没有适配器可以将 {type(source).__name__} 适配为 {target_type.__name__ if target_type else 'Unknown'}"
        self.log_adaptation(source, None, success=False, error=error_msg)
        raise AdapterError(error_msg)