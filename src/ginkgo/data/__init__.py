# Upstream: 回测引擎, 策略模块, 分析器模块, CLI命令, Web UI, Worker系统
# Downstream: containers(Container), seeding(数据初始化), utils(get_crud)
# Role: 数据层包入口，暴露依赖注入容器container和工具函数，统一数据访问入口
# See #2715: 聚合导入改为 __getattr__ 懒加载，打断全量模块加载链




"""
Ginkgo Data Module

Data layer module with dependency injection container for managing services.

Usage:
    from ginkgo.data import container
    result = container.bar_service().get(code="000001.SZ")

Available services:
- container.bar_service() - K线数据服务
- container.tick_service() - Tick数据服务
- container.stockinfo_service() - 股票信息服务
- container.adjustfactor_service() - 复权因子服务
- container.file_service() - 文件管理服务
- container.engine_service() - 回测引擎服务
- container.portfolio_service() - 投资组合服务
- container.component_service() - 组件实例化服务
"""

# See #2715: 懒加载注册表，避免 import 时触发全量加载
_LAZY_IMPORTS = {
    "container": ("ginkgo.data.containers", "container"),
    "seeding": ("ginkgo.data.seeding", None),
    "get_crud": ("ginkgo.data.utils", "get_crud"),
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        if attr_name is None:
            return module
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(_LAZY_IMPORTS.keys()) + list(globals().keys())


__all__ = ["container", "seeding", "get_crud"]
