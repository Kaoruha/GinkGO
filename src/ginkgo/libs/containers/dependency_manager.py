"""
跨模块依赖管理器

管理不同模块容器之间的依赖关系，提供统一的依赖解析和生命周期管理。
"""

from typing import Dict, Any, List, Set, Optional, Tuple
from enum import Enum
import threading
import time
from dataclasses import dataclass, field

from .base_container import BaseContainer, ContainerState
from .container_registry import registry
from .exceptions import (
    ContainerNotRegisteredError,
    ServiceNotFoundError,
    CircularDependencyError,
    ContainerLifecycleError
)
from ginkgo.libs import GLOG


class DependencyType(Enum):
    """依赖类型"""
    REQUIRED = "required"      # 必需依赖
    OPTIONAL = "optional"      # 可选依赖
    LAZY = "lazy"             # 懒加载依赖
    SINGLETON = "singleton"    # 单例依赖
    TRANSIENT = "transient"   # 瞬态依赖


@dataclass
class DependencyRule:
    """依赖规则定义"""
    source_module: str
    target_module: str
    service_name: str
    dependency_type: DependencyType = DependencyType.REQUIRED
    alias: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0


@dataclass
class DependencyInstance:
    """依赖实例信息"""
    service_name: str
    instance: Any
    source_module: str
    dependency_type: DependencyType
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class DependencyManager:
    """
    跨模块依赖管理器
    
    功能：
    - 跨模块依赖规则定义和管理
    - 依赖解析和缓存
    - 依赖生命周期管理
    - 循环依赖检测
    - 条件依赖支持
    """
    
    def __init__(self):
        self._dependency_rules: Dict[str, List[DependencyRule]] = {}
        self._dependency_cache: Dict[str, DependencyInstance] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        self._logger = GLOG
        
        # 性能统计
        self._resolution_stats: Dict[str, Dict[str, Any]] = {}
    
    def add_dependency_rule(self, rule: DependencyRule) -> None:
        """
        添加依赖规则
        
        Args:
            rule: 依赖规则
        """
        with self._lock:
            source_key = f"{rule.source_module}:{rule.service_name}"
            
            if rule.source_module not in self._dependency_rules:
                self._dependency_rules[rule.source_module] = []
            
            # 检查重复规则
            for existing_rule in self._dependency_rules[rule.source_module]:
                if (existing_rule.target_module == rule.target_module and 
                    existing_rule.service_name == rule.service_name):
                    self._logger.WARN(f"依赖规则已存在，将被覆盖: {source_key}")
                    self._dependency_rules[rule.source_module].remove(existing_rule)
                    break
            
            self._dependency_rules[rule.source_module].append(rule)
            
            # 更新依赖图
            self._update_dependency_graph(rule)
            
            self._logger.DEBUG(f"已添加依赖规则: {source_key} -> {rule.target_module}")
    
    def remove_dependency_rule(self, source_module: str, target_module: str, service_name: str) -> bool:
        """
        移除依赖规则
        
        Args:
            source_module: 源模块
            target_module: 目标模块
            service_name: 服务名称
            
        Returns:
            是否成功移除
        """
        with self._lock:
            if source_module not in self._dependency_rules:
                return False
            
            for rule in self._dependency_rules[source_module]:
                if (rule.target_module == target_module and 
                    rule.service_name == service_name):
                    self._dependency_rules[source_module].remove(rule)
                    
                    # 清理缓存
                    cache_key = f"{source_module}:{service_name}"
                    if cache_key in self._dependency_cache:
                        del self._dependency_cache[cache_key]
                    
                    # 更新依赖图
                    self._rebuild_dependency_graph()
                    
                    self._logger.DEBUG(f"已移除依赖规则: {cache_key} -> {target_module}")
                    return True
            
            return False
    
    def resolve_dependency(self, source_module: str, service_name: str) -> Any:
        """
        解析依赖
        
        Args:
            source_module: 源模块
            service_name: 服务名称
            
        Returns:
            依赖实例
            
        Raises:
            ServiceNotFoundError: 服务未找到
            CircularDependencyError: 循环依赖
            ContainerLifecycleError: 容器状态错误
        """
        cache_key = f"{source_module}:{service_name}"
        
        # 检查缓存
        if cache_key in self._dependency_cache:
            dependency_instance = self._dependency_cache[cache_key]
            dependency_instance.access_count += 1
            dependency_instance.last_accessed = time.time()
            return dependency_instance.instance
        
        # 查找匹配的依赖规则
        rule = self._find_dependency_rule(source_module, service_name)
        if not rule:
            raise ServiceNotFoundError(
                service_name, 
                f"No dependency rule found for {source_module}:{service_name}"
            )
        
        # 解析依赖
        start_time = time.time()
        try:
            instance = self._resolve_with_rule(rule, source_module)
            
            # 缓存实例（根据依赖类型）
            if rule.dependency_type in (DependencyType.SINGLETON, DependencyType.LAZY):
                dependency_instance = DependencyInstance(
                    service_name=service_name,
                    instance=instance,
                    source_module=source_module,
                    dependency_type=rule.dependency_type
                )
                self._dependency_cache[cache_key] = dependency_instance
            
            # 记录解析统计
            resolution_time = time.time() - start_time
            self._record_resolution_stats(cache_key, resolution_time, True)
            
            return instance
            
        except Exception as e:
            resolution_time = time.time() - start_time
            self._record_resolution_stats(cache_key, resolution_time, False)
            raise
    
    def _find_dependency_rule(self, source_module: str, service_name: str) -> Optional[DependencyRule]:
        """查找匹配的依赖规则"""
        if source_module not in self._dependency_rules:
            return None
        
        for rule in self._dependency_rules[source_module]:
            if rule.service_name == service_name:
                # 检查条件
                if self._check_rule_conditions(rule):
                    return rule
        
        return None
    
    def _resolve_with_rule(self, rule: DependencyRule, source_module: str) -> Any:
        """根据规则解析依赖"""
        # 检查循环依赖
        if self._has_circular_dependency(source_module, rule.target_module):
            raise CircularDependencyError([source_module, rule.target_module])
        
        # 获取目标容器
        try:
            target_container = registry.get_container(rule.target_module)
        except ContainerNotRegisteredError:
            if rule.dependency_type == DependencyType.OPTIONAL:
                return None
            raise
        
        # 检查容器状态
        if not target_container.is_ready:
            if rule.dependency_type == DependencyType.LAZY:
                # 懒加载：等待容器准备就绪
                self._wait_for_container_ready(target_container, rule.timeout)
            elif rule.dependency_type == DependencyType.OPTIONAL:
                return None
            else:
                raise ContainerLifecycleError(
                    rule.target_module,
                    "resolve_dependency",
                    f"Container not ready (state: {target_container.state.value})"
                )
        
        # 获取服务
        service_name = rule.alias or rule.service_name
        return target_container.get(service_name)
    
    def _check_rule_conditions(self, rule: DependencyRule) -> bool:
        """检查规则条件"""
        if not rule.conditions:
            return True
        
        for condition_type, condition_value in rule.conditions.items():
            if condition_type == "container_state":
                try:
                    container = registry.get_container(rule.target_module)
                    if container.state.value != condition_value:
                        return False
                except ContainerNotRegisteredError:
                    return False
            
            elif condition_type == "service_available":
                try:
                    container = registry.get_container(rule.target_module)
                    if not container.has(condition_value):
                        return False
                except ContainerNotRegisteredError:
                    return False
        
        return True
    
    def _has_circular_dependency(self, source_module: str, target_module: str) -> bool:
        """检查循环依赖"""
        if source_module == target_module:
            return True
        
        def _dfs(current: str, visited: Set[str]) -> bool:
            if current in visited:
                return current == source_module
            
            visited.add(current)
            
            if current in self._dependency_graph:
                for dependent in self._dependency_graph[current]:
                    if _dfs(dependent, visited.copy()):
                        return True
            
            return False
        
        return _dfs(target_module, set())
    
    def _wait_for_container_ready(self, container: BaseContainer, timeout: float) -> None:
        """等待容器准备就绪"""
        start_time = time.time()
        
        while not container.is_ready:
            if time.time() - start_time > timeout:
                raise ContainerLifecycleError(
                    container.module_name,
                    "wait_for_ready",
                    f"Timeout waiting for container to be ready (timeout: {timeout}s)"
                )
            
            time.sleep(0.1)
    
    def _update_dependency_graph(self, rule: DependencyRule) -> None:
        """更新依赖图"""
        if rule.target_module not in self._dependency_graph:
            self._dependency_graph[rule.target_module] = set()
        
        self._dependency_graph[rule.target_module].add(rule.source_module)
    
    def _rebuild_dependency_graph(self) -> None:
        """重建依赖图"""
        self._dependency_graph.clear()
        
        for source_module, rules in self._dependency_rules.items():
            for rule in rules:
                self._update_dependency_graph(rule)
    
    def _record_resolution_stats(self, cache_key: str, resolution_time: float, success: bool) -> None:
        """记录解析统计信息"""
        if cache_key not in self._resolution_stats:
            self._resolution_stats[cache_key] = {
                'total_resolutions': 0,
                'successful_resolutions': 0,
                'failed_resolutions': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'last_resolution_time': 0.0
            }
        
        stats = self._resolution_stats[cache_key]
        stats['total_resolutions'] += 1
        stats['total_time'] += resolution_time
        stats['last_resolution_time'] = resolution_time
        
        if success:
            stats['successful_resolutions'] += 1
        else:
            stats['failed_resolutions'] += 1
        
        if stats['total_resolutions'] > 0:
            stats['avg_time'] = stats['total_time'] / stats['total_resolutions']
    
    def clear_cache(self, source_module: str = None) -> None:
        """
        清理依赖缓存
        
        Args:
            source_module: 可选，指定模块。如果不指定则清理所有缓存
        """
        with self._lock:
            if source_module:
                keys_to_remove = [
                    key for key in self._dependency_cache.keys() 
                    if key.startswith(f"{source_module}:")
                ]
                for key in keys_to_remove:
                    del self._dependency_cache[key]
                self._logger.DEBUG(f"已清理模块 {source_module} 的依赖缓存")
            else:
                self._dependency_cache.clear()
                self._logger.DEBUG("已清理所有依赖缓存")
    
    def get_dependency_info(self, source_module: str = None) -> Dict[str, Any]:
        """
        获取依赖信息
        
        Args:
            source_module: 可选，指定模块
            
        Returns:
            依赖信息字典
        """
        info = {
            'total_rules': sum(len(rules) for rules in self._dependency_rules.values()),
            'cached_dependencies': len(self._dependency_cache),
            'resolution_stats': self._resolution_stats.copy()
        }
        
        if source_module:
            if source_module in self._dependency_rules:
                info['module_rules'] = [
                    {
                        'target_module': rule.target_module,
                        'service_name': rule.service_name,
                        'dependency_type': rule.dependency_type.value,
                        'alias': rule.alias,
                        'conditions': rule.conditions
                    }
                    for rule in self._dependency_rules[source_module]
                ]
            else:
                info['module_rules'] = []
            
            # 模块特定的缓存信息
            module_cache = {
                key: {
                    'service_name': dep.service_name,
                    'source_module': dep.source_module,
                    'dependency_type': dep.dependency_type.value,
                    'access_count': dep.access_count,
                    'created_at': dep.created_at,
                    'last_accessed': dep.last_accessed
                }
                for key, dep in self._dependency_cache.items()
                if key.startswith(f"{source_module}:")
            }
            info['module_cache'] = module_cache
        else:
            info['all_rules'] = {
                module: [
                    {
                        'target_module': rule.target_module,
                        'service_name': rule.service_name,
                        'dependency_type': rule.dependency_type.value,
                        'alias': rule.alias,
                        'conditions': rule.conditions
                    }
                    for rule in rules
                ]
                for module, rules in self._dependency_rules.items()
            }
            
            info['dependency_graph'] = {
                target: list(sources) 
                for target, sources in self._dependency_graph.items()
            }
        
        return info
    
    def validate_dependencies(self) -> List[str]:
        """
        验证所有依赖规则
        
        Returns:
            验证错误列表
        """
        errors = []
        
        for source_module, rules in self._dependency_rules.items():
            for rule in rules:
                try:
                    # 检查目标容器是否存在
                    registry.get_container(rule.target_module)
                    
                    # 检查服务是否存在（如果容器已准备就绪）
                    target_container = registry.get_container(rule.target_module)
                    if target_container.is_ready:
                        service_name = rule.alias or rule.service_name
                        if not target_container.has(service_name):
                            errors.append(
                                f"Service '{service_name}' not found in container '{rule.target_module}'"
                            )
                
                except ContainerNotRegisteredError:
                    if rule.dependency_type != DependencyType.OPTIONAL:
                        errors.append(
                            f"Target container '{rule.target_module}' not registered for dependency '{source_module}:{rule.service_name}'"
                        )
        
        return errors


# 全局依赖管理器实例
dependency_manager = DependencyManager()