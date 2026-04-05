# Upstream: AnalysisEngine, 分析报告模块
# Downstream: 具体指标实现 (Portfolio/Position/Signal/Order 层级)
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

    管理所有已注册的指标类，支持按名称查找、实例化和依赖检查。

    用法：
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        registry.register(SharpeMetric)

        # 检查依赖
        available, missing = registry.check_availability(data_provider)

        # 实例化
        sharpe = registry.instantiate("sharpe_ratio", risk_free_rate=0.05)
    """

    def __init__(self):
        self._registry: Dict[str, type] = {}

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

    def list_metrics(self) -> List[str]:
        """列出所有已注册的指标名称"""
        return list(self._registry.keys())

    def check_availability(
        self, data: Union[DataProvider, Dict[str, pd.DataFrame]]
    ) -> tuple:
        """检查指标依赖数据的可用性。

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
        for name, cls in self._registry.items():
            # requires 可能是类属性或实例属性
            reqs = getattr(cls, 'requires', [])
            if all(req in available_keys for req in reqs):
                available.append(name)
            else:
                missing.append(name)
        return available, missing

    def instantiate(self, name: str, **params) -> Any:
        """实例化指定指标，支持参数覆盖。

        Raises:
            KeyError: 指标名称不存在时抛出
        """
        cls = self._registry.get(name)
        if cls is None:
            raise KeyError(f"Metric '{name}' not registered")
        if params:
            return cls(**params)
        return cls()
