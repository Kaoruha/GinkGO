# Upstream: ginkgo.data.cruds, pandas, numpy
# Downstream: ginkgo.research.ic_analysis, ginkgo.client
# Role: 因子研究数据模型 - IC统计、分层结果、正交化结果等

"""
因子研究数据模型

定义因子研究相关的数据结构:
- ICStatistics: IC 统计指标
- ICAnalysisResult: IC 分析结果
- LayeringResult: 分层分析结果
- LayerGroup: 单层分组数据
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import uuid


@dataclass
class ICStatistics:
    """
    IC 统计指标

    存储因子 IC 的统计特征。

    Attributes:
        mean: IC 均值
        std: IC 标准差
        icir: 信息系数信息比 (ICIR = mean / std)
        t_stat: t 统计量
        p_value: p 值
        pos_ratio: 正向 IC 比例 (IC > 0 的比例)
        abs_mean: IC 绝对值均值
    """
    mean: Decimal = Decimal("0")
    std: Decimal = Decimal("0")
    icir: Decimal = Decimal("0")
    t_stat: Optional[Decimal] = None
    p_value: Optional[Decimal] = None
    pos_ratio: Decimal = Decimal("0")
    abs_mean: Decimal = Decimal("0")
    count: int = 0

    def __post_init__(self):
        """初始化后处理"""
        # 自动计算 ICIR（如果未提供）
        if self.icir == 0 and self.std != 0:
            self.icir = self.mean / self.std

    def is_significant(self, alpha: Decimal = Decimal("0.05")) -> bool:
        """
        判断 IC 是否显著

        Args:
            alpha: 显著性水平 (默认 0.05)

        Returns:
            是否显著
        """
        if self.p_value is None:
            return False
        return self.p_value < alpha

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "mean": str(self.mean),
            "std": str(self.std),
            "icir": str(self.icir),
            "t_stat": str(self.t_stat) if self.t_stat else None,
            "p_value": str(self.p_value) if self.p_value else None,
            "pos_ratio": str(self.pos_ratio),
            "abs_mean": str(self.abs_mean),
            "count": self.count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ICStatistics":
        """从字典反序列化"""
        decimal_fields = ["mean", "std", "icir", "t_stat", "p_value", "pos_ratio", "abs_mean"]
        for field_name in decimal_fields:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = Decimal(data[field_name])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ICAnalysisResult:
    """
    IC 分析结果

    存储完整的因子 IC 分析结果。

    Attributes:
        factor_name: 因子名称
        periods: 分析周期列表
        date_range: 日期范围 (start, end)
        ic_series: IC 序列 {period: [ic_values]}
        rank_ic_series: Rank IC 序列 {period: [ic_values]}
        statistics: 统计指标 {period: ICStatistics}
    """
    factor_name: str = ""
    periods: List[int] = field(default_factory=list)
    date_range: Optional[Tuple[str, str]] = None
    ic_series: Dict[int, List[float]] = field(default_factory=dict)
    rank_ic_series: Dict[int, List[float]] = field(default_factory=dict)
    statistics: Dict[int, ICStatistics] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def get_best_period(self, metric: str = "icir") -> Optional[int]:
        """
        获取最佳周期

        Args:
            metric: 评价指标 (icir, mean, pos_ratio)

        Returns:
            最佳周期
        """
        if not self.statistics:
            return None

        best_period = None
        best_value = None

        for period, stats in self.statistics.items():
            value = getattr(stats, metric, None)
            if value is None:
                continue

            if best_value is None or value > best_value:
                best_value = value
                best_period = period

        return best_period

    def get_statistics_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要

        Returns:
            统计摘要字典
        """
        summary = {
            "factor_name": self.factor_name,
            "periods": self.periods,
            "date_range": self.date_range,
        }

        for period, stats in self.statistics.items():
            summary[f"period_{period}"] = {
                "mean": float(stats.mean),
                "icir": float(stats.icir),
                "pos_ratio": float(stats.pos_ratio),
            }

        return summary

    def to_dataframe(self):
        """
        转换为 pandas DataFrame

        Returns:
            IC 序列 DataFrame
        """
        try:
            import pandas as pd
        except ImportError:
            return None

        if not self.ic_series:
            return None

        # 找到最长的序列
        max_len = max(len(v) for v in self.ic_series.values())

        data = {}
        for period in sorted(self.ic_series.keys()):
            values = self.ic_series[period]
            # 填充到相同长度
            padded = values + [None] * (max_len - len(values))
            data[f"IC_{period}d"] = padded

        return pd.DataFrame(data)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "factor_name": self.factor_name,
            "periods": self.periods,
            "date_range": self.date_range,
            "ic_series": self.ic_series,
            "rank_ic_series": self.rank_ic_series,
            "statistics": {
                str(k): v.to_dict() for k, v in self.statistics.items()
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ICAnalysisResult":
        """从字典反序列化"""
        # 转换 statistics
        statistics = {}
        for k, v in data.get("statistics", {}).items():
            statistics[int(k)] = ICStatistics.from_dict(v)

        # 转换 created_at
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            factor_name=data.get("factor_name", ""),
            periods=data.get("periods", []),
            date_range=tuple(data["date_range"]) if data.get("date_range") else None,
            ic_series=data.get("ic_series", {}),
            rank_ic_series=data.get("rank_ic_series", {}),
            statistics=statistics,
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class LayerGroup:
    """
    分层组数据

    存储单个分层组的收益数据。

    Attributes:
        group_id: 组 ID (1-N)
        name: 组名称 (如 "Q1", "Q5")
        mean_return: 平均收益率
        cumulative_return: 累计收益率
        count: 样本数
    """
    group_id: int
    name: str = ""
    mean_return: Decimal = Decimal("0")
    cumulative_return: Decimal = Decimal("0")
    std_return: Decimal = Decimal("0")
    count: int = 0
    returns: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "group_id": self.group_id,
            "name": self.name,
            "mean_return": str(self.mean_return),
            "cumulative_return": str(self.cumulative_return),
            "std_return": str(self.std_return),
            "count": self.count,
        }


@dataclass
class LayeringResult:
    """
    分层分析结果

    存储因子分层分析结果。

    Attributes:
        factor_name: 因子名称
        n_groups: 分组数
        groups: 分组数据 {group_id: LayerGroup}
        spread: 顶底组收益差 (Q_N - Q_1)
    """
    factor_name: str = ""
    n_groups: int = 5
    groups: Dict[int, LayerGroup] = field(default_factory=dict)
    spread: Decimal = Decimal("0")
    date_range: Optional[Tuple[str, str]] = None
    period: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_monotonicity(self) -> Decimal:
        """
        计算单调性

        Returns:
            单调性指标 (0-1，越接近 1 越单调)
        """
        if len(self.groups) < 2:
            return Decimal("0")

        sorted_groups = sorted(self.groups.items(), key=lambda x: x[0])
        returns = [float(g.mean_return) for _, g in sorted_groups]

        # 计算单调性：相邻组收益递增的比例
        increases = sum(1 for i in range(len(returns) - 1) if returns[i + 1] > returns[i])
        return Decimal(str(increases / (len(returns) - 1)))

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "factor_name": self.factor_name,
            "n_groups": self.n_groups,
            "groups": {str(k): v.to_dict() for k, v in self.groups.items()},
            "spread": str(self.spread),
            "date_range": self.date_range,
            "period": self.period,
            "monotonicity": str(self.get_monotonicity()),
            "metadata": self.metadata,
        }
