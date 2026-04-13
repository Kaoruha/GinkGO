# Upstream: 外部应用和CLI命令(统一服务访问入口from ginkgo import service_hub)
# Downstream: DataContainer/Data/Trading/Core/ML/Features容器(懒加载各模块容器提供依赖注入)
# Role: ServiceHub服务访问协调器提供懒加载/错误处理


"""
Ginkgo ServiceHub - 统一服务访问协调器

通过注册表驱动的懒加载提供到各模块 dependency_injector 容器的统一访问。

Usage:
    from ginkgo import services
    bar_crud = services.data.cruds.bar()
    engine = services.trading.engines.time_controlled()
"""

from typing import Dict, Any, Optional, List

from ginkgo.libs import GLOG


# 模块注册表: name → (module_path, attribute_name, post_load_hook_name)
_MODULE_REGISTRY: Dict[str, tuple] = {
    'data': ('ginkgo.data.containers', 'container', None),
    'trading': ('ginkgo.trading.core.containers', 'backtest_container', None),
    'core': ('ginkgo.core.core_containers', 'container', None),
    'ml': ('ginkgo.quant_ml.containers', 'container', None),
    'features': ('ginkgo.features.containers', 'feature_container', '_configure_features'),
    'notifier': ('ginkgo.notifier.containers', 'container', None),
    'research': ('ginkgo.research.containers', 'research_container', None),
    'validation': ('ginkgo.validation.containers', 'validation_container', None),
    'comparison': ('ginkgo.trading.comparison.containers', 'comparison_container', None),
    'optimization': ('ginkgo.trading.optimization.containers', 'optimization_container', None),
    'logging': ('ginkgo.services.logging.containers', 'container', None),
}


class ServiceHubError(Exception):
    """ServiceHub相关异常"""
    pass


class ServiceHub:
    """
    统一服务访问协调器

    通过注册表驱动的方式提供到各模块容器的懒加载访问。
    """

    def __init__(self):
        self._module_cache: Dict[str, Any] = {}
        self._module_errors: Dict[str, str] = {}
        self._debug_mode: bool = False

    def enable_debug(self) -> None:
        """启用调试模式"""
        self._debug_mode = True

    def disable_debug(self) -> None:
        """禁用调试模式"""
        self._debug_mode = False

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)
        if name not in _MODULE_REGISTRY:
            raise AttributeError(f"ServiceHub has no module '{name}'")

        if name in self._module_cache:
            return self._module_cache[name]

        return self._load_module(name)

    def _load_module(self, name: str) -> Any:
        """加载并缓存模块容器"""
        module_path, attr_name, post_hook = _MODULE_REGISTRY[name]

        try:
            module = __import__(module_path, fromlist=[attr_name])
            container = getattr(module, attr_name)

            if post_hook:
                getattr(self, post_hook)(container)

            self._module_cache[name] = container
            return container
        except Exception as e:
            self._module_errors[name] = str(e)
            if self._debug_mode:
                GLOG.ERROR(f"{name} module error: {e}")
            return None

    def _configure_features(self, container) -> None:
        """features 模块后置配置"""
        from ginkgo.features.containers import configure_features_container
        configure_features_container(self.data)

    def get_module_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模块状态"""
        status = {}
        for name in _MODULE_REGISTRY:
            try:
                module = getattr(self, name)
                status[name] = {
                    'available': module is not None,
                    'error': self._module_errors.get(name)
                }
            except Exception as e:
                status[name] = {'available': False, 'error': str(e)}
        return status

    def diagnose_issues(self) -> List[str]:
        """诊断并报告服务问题"""
        issues = []
        for name, info in self.get_module_status().items():
            if not info['available']:
                issues.append(f"{name}: {info['error']}")
        if issues:
            GLOG.ERROR(f"ServiceHub issues: {issues}")
        return issues

    def list_available_modules(self) -> List[str]:
        """列出可用模块"""
        return [name for name in _MODULE_REGISTRY if getattr(self, name, None) is not None]

    def clear_cache(self, module_name: Optional[str] = None) -> None:
        """清理模块缓存"""
        if module_name and module_name in self._module_cache:
            del self._module_cache[module_name]
        elif module_name is None:
            self._module_cache.clear()


# 创建全局ServiceHub实例
service_hub = ServiceHub()

# 为了向后兼容，保留services别名
services = service_hub

__all__ = ['service_hub', 'services']

