# Upstream: AnalysisEngine, 分析报告模块
# Downstream: 具体指标实现 (analyzer_metrics 等参数化指标)
# Role: 定义 Metric Protocol、DataProvider 数据容器、MetricRegistry 注册中心


"""
分析指标基础抽象层

提供统一的指标定义协议、数据容器和注册中心，
为后续各层级指标实现提供标准化基础设施。
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable, Union

import pandas as pd


# ============================================================
# Metric Protocol
# ============================================================

@runtime_checkable
class Metric(Protocol):
    """指标计算协议 (Metric Protocol)

    定义所有分析指标必须实现的核心接口。
    使用 Protocol 支持结构化子类型（鸭子类型的静态检查）。

    Attributes:
        name: 指标唯一标识名称
        requires: 计算所需的数据 key 列表
        params: 指标参数字典
    """

    name: str
    requires: List[str]
    params: Dict[str, Any]

    def compute(self, data: Dict[str, pd.DataFrame]) -> Any: ...


# ============================================================
# DataProvider
# ============================================================

class DataProvider:
    """数据容器 (Data Provider)

    简单的字典封装，用于向 Metric 提供 DataFrame 数据。
    支持构造函数传入和 add 方法追加。

    用法：
        dp = DataProvider(bars=df_bars, trades=df_trades)
        dp.add("daily_returns", df_returns)
        assert "bars" in dp.available
    """

    def __init__(self, **kwargs: pd.DataFrame):
        self._data: Dict[str, pd.DataFrame] = dict(kwargs)

    def add(self, key: str, df: pd.DataFrame) -> None:
        """添加数据到容器"""
        self._data[key] = df

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """获取数据，不存在时返回None"""
        return self._data.get(key)

    @property
    def available(self) -> List[str]:
        """返回所有已注册的数据 key 列表"""
        return list(self._data.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._data


# ============================================================
# MetricRegistry
# ============================================================

class MetricRegistry:
    """指标注册中心 (Metric Registry)

    管理所有已注册的指标类和实例，支持按名称查找、实例化和依赖检查。
    同时支持类级别注册 (register) 和实例级别注册 (register_instance)。

    用法：
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        registry.register(SharpeMetric)

        # 参数化指标通过实例注册
        registry.register_instance(RollingMean(analyzer_name="sharpe", window=10))

        # 检查依赖
        available, missing = registry.check_availability(data_provider)

        # 实例化类级别指标
        sharpe = registry.instantiate("sharpe_ratio", risk_free_rate=0.05)

        # 获取已注册的实例
        rm = registry.get_instance("rolling_mean.sharpe")
    """

    def __init__(self):
        # 类级别注册（向后兼容）
        self._registry: Dict[str, type] = {}
        # 实例级别注册（参数化指标）
        self._instances: Dict[str, Any] = {}

    def register(self, metric_cls: type) -> None:
        """注册指标类，以 name 属性为键

        优先使用类属性 name，若不存在则尝试通过无参构造获取实例的 name。
        """
        if hasattr(metric_cls, 'name') and isinstance(getattr(metric_cls, 'name', None), str):
            name = metric_cls.name
        else:
            # 尝试无参构造来获取 name（适用于 name 在 __init__ 中设置的类）
            try:
                tmp = metric_cls()
                name = tmp.name
            except Exception:
                raise AttributeError(
                    f"Cannot determine 'name' for metric class {metric_cls.__name__}"
                )
        self._registry[name] = metric_cls

    def get(self, name: str) -> Optional[type]:
        """按名称获取指标类"""
        return self._registry.get(name)

    def register_instance(self, instance: Any) -> None:
        """注册指标实例，以 instance.name 为键

        用于参数化指标（如不同 window 的 RollingMean），
        同名实例会覆盖旧的。

        Args:
            instance: 必须有 name 和 requires 属性
        """
        if not hasattr(instance, 'name') or not isinstance(instance.name, str):
            raise AttributeError(
                f"Instance {type(instance).__name__} must have a 'name' attribute"
            )
        self._instances[instance.name] = instance

    def get_instance(self, name: str) -> Optional[Any]:
        """按名称获取已注册的指标实例"""
        return self._instances.get(name)

    def list_metrics(self) -> List[str]:
        """列出所有已注册的指标名称（类级别 + 实例级别）"""
        class_names = list(self._registry.keys())
        instance_names = list(self._instances.keys())
        return class_names + instance_names

    def check_availability(
        self, data: Union[DataProvider, Dict[str, pd.DataFrame]]
    ) -> tuple:
        """检查指标依赖数据的可用性。

        同时检查类级别注册和实例级别注册的指标。

        Args:
            data: DataProvider 实例或普通字典

        Returns:
            (available, missing) 两个列表
        """
        if isinstance(data, DataProvider):
            available_keys = set(data.available)
        else:
            available_keys = set(data.keys())

        available = []
        missing = []
        # 检查类级别注册
        for name, cls in self._registry.items():
            reqs = getattr(cls, 'requires', [])
            if all(req in available_keys for req in reqs):
                available.append(name)
            else:
                missing.append(name)
        # 检查实例级别注册
        for name, instance in self._instances.items():
            reqs = getattr(instance, 'requires', [])
            if all(req in available_keys for req in reqs):
                available.append(name)
            else:
                missing.append(name)
        return available, missing

    def instantiate(self, name: str, **params) -> Any:
        """实例化指定指标，支持参数覆盖。

        优先返回已注册的实例（参数化指标），其次尝试类级别实例化。

        Raises:
            KeyError: 指标名称不存在时抛出
        """
        # 实例级别（参数化指标）
        if name in self._instances:
            return self._instances[name]
        # 类级别
        cls = self._registry.get(name)
        if cls is None:
            raise KeyError(f"Metric '{name}' not registered")
        if params:
            return cls(**params)
        return cls()
