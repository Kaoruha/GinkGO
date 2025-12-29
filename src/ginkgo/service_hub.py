# Upstream: 外部应用和CLI命令(统一服务访问入口from ginkgo import service_hub)
# Downstream: DataContainer/Data/Trading/Core/ML/Features容器(懒加载各模块容器提供依赖注入)
# Role: ServiceHub服务访问协调器提供懒加载/错误处理/诊断/兼容性支持交易系统功能和组件集成提供完整业务支持






"""
Ginkgo ServiceHub - 统一服务访问协调器

ServiceHub作为服务访问器的协调中心，明确分离服务访问器与业务服务的边界。
提供懒加载、错误处理、诊断功能和向后兼容性。

Usage:
    from ginkgo import service_hub

    # Data services - 完善的数据访问层
    bar_crud = service_hub.data.cruds.bar()
    bar_service = service_hub.data.services.bar_service()

    # Trading services - 交易引擎和组件
    engine = service_hub.trading.engines.time_controlled()
    portfolio = service_hub.trading.base_portfolio()

    # Core services - 核心基础服务
    config_service = service_hub.core.services.config()

    # Features services - 因子工程服务
    feature_container = service_hub.features

Architecture:
    ServiceHub (服务访问器协调器)
    ├── data (数据模块访问器)
    │   ├── cruds (CRUD访问器)
    │   ├── services (业务服务访问器)
    │   └── sources (数据源访问器)
    ├── trading (交易模块访问器)
    │   ├── engines (引擎访问器)
    │   ├── portfolios (组合访问器)
    │   └── strategies (策略访问器)
    ├── core (核心模块访问器)
    └── features (因子模块访问器)
"""

from typing import Dict, Any, Optional, List
import time
from functools import wraps


class ServiceHubError(Exception):
    """ServiceHub相关异常"""
    pass


class ServiceHub:
    """
    统一服务访问协调器

    ServiceHub作为服务访问器的协调中心，不直接包含业务逻辑，
    而是提供到各个模块容器的统一访问接口。
    """

    def __init__(self):
        """初始化ServiceHub"""
        self._module_errors: Dict[str, str] = {}
        self._debug_mode: bool = False
        self._performance_stats: Dict[str, Dict[str, Any]] = {}
        self._start_time = time.time()

        # 缓存已加载的模块容器
        self._module_cache: Dict[str, Any] = {}

    def enable_debug(self) -> None:
        """启用调试模式以获取详细错误报告"""
        self._debug_mode = True
        print(":magnifying_glass_tilted_left: ServiceHub调试模式已启用 - 详细错误报告现已激活")

    def disable_debug(self) -> None:
        """禁用调试模式"""
        self._debug_mode = False
        print(":muted_speaker: ServiceHub调试模式已禁用")

    def get_uptime(self) -> float:
        """获取ServiceHub运行时间"""
        return time.time() - self._start_time

    def get_module_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模块的详细状态"""
        status = {}
        for module_name in ['data', 'trading', 'core', 'ml', 'features']:
            try:
                module = getattr(self, module_name)
                if module is not None:
                    status[module_name] = {
                        'available': True,
                        'type': type(module).__name__,
                        'error': None,
                        'cached': module_name in self._module_cache,
                        'load_time': self._performance_stats.get(module_name, {}).get('load_time', 0.0)
                    }
                else:
                    status[module_name] = {
                        'available': False,
                        'type': None,
                        'error': self._module_errors.get(module_name, '未知错误'),
                        'cached': False,
                        'load_time': 0.0
                    }
            except Exception as e:
                status[module_name] = {
                    'available': False,
                    'type': None,
                    'error': str(e),
                    'cached': False,
                    'load_time': 0.0
                }
        return status

    def diagnose_issues(self) -> List[str]:
        """诊断并报告服务问题"""
        status = self.get_module_status()
        issues = []

        for module_name, info in status.items():
            if not info['available']:
                issues.append(f"{module_name}模块: {info['error']}")

        if issues:
            print(":magnifying_glass_tilted_left: ServiceHub诊断报告:")
            for issue in issues:
                print(f"  :x: {issue}")
            print("\n建议:")
            print("  1. 检查模块依赖和导入")
            print("  2. 验证容器配置")
            print("  3. 运行: service_hub.enable_debug() 获取详细错误信息")
        else:
            print(":white_check_mark: ServiceHub所有服务运行正常!")

        return issues

    def list_available_modules(self) -> List[str]:
        """列出所有可用模块"""
        available = ["data"]  # data模块始终可用

        for module_name in ["trading", "core", "ml", "features"]:
            try:
                module = getattr(self, module_name)
                if module is not None:
                    available.append(module_name)
            except Exception:
                # 模块不可用，跳过
                pass

        return available

    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取性能统计信息"""
        stats = {
            'uptime': self.get_uptime(),
            'total_errors': len(self._module_errors),
            'cached_modules': len(self._module_cache),
            'module_performance': self._performance_stats
        }
        return stats

    def clear_cache(self, module_name: Optional[str] = None) -> None:
        """清理模块缓存"""
        if module_name and module_name in self._module_cache:
            del self._module_cache[module_name]
            print(f":recycle: 已清理{module_name}模块缓存")
        elif module_name is None:
            self._module_cache.clear()
            print(":recycle: 已清理所有模块缓存")

    def _measure_performance(self, module_name: str):
        """性能测量装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    load_time = time.time() - start_time

                    # 记录性能统计
                    if module_name not in self._performance_stats:
                        self._performance_stats[module_name] = {}
                    self._performance_stats[module_name]['load_time'] = load_time
                    self._performance_stats[module_name]['last_access'] = time.time()

                    return result
                except Exception as e:
                    # 记录错误统计
                    if module_name not in self._performance_stats:
                        self._performance_stats[module_name] = {}
                    self._performance_stats[module_name]['last_error'] = str(e)
                    self._performance_stats[module_name]['error_time'] = time.time()
                    raise
            return wrapper
        return decorator

    @property
    def data(self):
        """数据模块访问器 (始终可用)"""
        if 'data' in self._module_cache:
            return self._module_cache['data']

        @self._measure_performance('data')
        def _load_data():
            from ginkgo.data.containers import container as data_container
            return data_container

        try:
            container = _load_data()
            self._module_cache['data'] = container
            return container
        except Exception as e:
            self._module_errors['data'] = str(e)
            if self._debug_mode:
                print(f":x: 数据模块错误: {e}")
                import traceback
                traceback.print_exc()
            return None

    @property
    def trading(self):
        """交易模块访问器"""
        if 'trading' in self._module_cache:
            return self._module_cache['trading']

        @self._measure_performance('trading')
        def _load_trading():
            from ginkgo.trading.core.containers import backtest_container
            return backtest_container

        try:
            container = _load_trading()
            self._module_cache['trading'] = container
            return container
        except Exception as e:
            self._module_errors['trading'] = str(e)
            if self._debug_mode:
                print(f":x: 交易模块错误: {e}")
                import traceback
                traceback.print_exc()
            return None

    @property
    def core(self):
        """核心模块访问器"""
        if 'core' in self._module_cache:
            return self._module_cache['core']

        @self._measure_performance('core')
        def _load_core():
            from ginkgo.core.core_containers import container as core_container
            return core_container

        try:
            container = _load_core()
            self._module_cache['core'] = container
            return container
        except Exception as e:
            self._module_errors['core'] = str(e)
            if self._debug_mode:
                print(f":x: 核心模块错误: {e}")
                import traceback
                traceback.print_exc()
            return None

    @property
    def ml(self):
        """机器学习模块访问器"""
        if 'ml' in self._module_cache:
            return self._module_cache['ml']

        @self._measure_performance('ml')
        def _load_ml():
            from ginkgo.quant_ml.containers import container as ml_container
            return ml_container

        try:
            container = _load_ml()
            self._module_cache['ml'] = container
            return container
        except Exception as e:
            self._module_errors['ml'] = str(e)
            if self._debug_mode:
                print(f":x: 机器学习模块错误: {e}")
                import traceback
                traceback.print_exc()
            return None

    @property
    def features(self):
        """因子模块访问器"""
        if 'features' in self._module_cache:
            return self._module_cache['features']

        @self._measure_performance('features')
        def _load_features():
            from ginkgo.features.containers import feature_container, configure_features_container

            # 配置features容器的外部依赖
            configure_features_container(self.data)

            return feature_container

        try:
            container = _load_features()
            self._module_cache['features'] = container
            return container
        except Exception as e:
            self._module_errors['features'] = str(e)
            if self._debug_mode:
                print(f":x: 因子模块错误: {e}")
                import traceback
                traceback.print_exc()
            return None


# 创建全局ServiceHub实例
service_hub = ServiceHub()

# 为了向后兼容，保留services别名
services = service_hub

# 导出主要接口
__all__ = ['service_hub', 'services']