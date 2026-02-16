# Upstream: typing, dataclasses
# Downstream: ginkgo.trading.optimization.base_optimizer, ginkgo.trading.optimization.grid_search
# Role: 参数优化数据模型 - 参数范围、优化结果等

"""
参数优化数据模型

定义参数优化相关的数据结构:
- ParameterRange: 参数范围定义
- OptimizationRun: 单次优化运行
- OptimizationResult: 优化结果汇总
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple, Union
import uuid


@dataclass
class ParameterRange:
    """
    参数范围定义

    支持连续值和离散值参数范围。

    Attributes:
        name: 参数名称
        min_value: 最小值 (连续参数)
        max_value: 最大值 (连续参数)
        step: 步长 (连续参数)
        values: 离散值列表 (离散参数)
    """

    name: str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    values: Optional[List[Any]] = None

    def __post_init__(self):
        """验证参数范围"""
        if self.values is None:
            # 连续参数需要 min, max
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"连续参数 {self.name} 需要 min_value 和 max_value")
            if self.step is None:
                self.step = 1
            if self.min_value > self.max_value:
                raise ValueError(f"min_value ({self.min_value}) 不能大于 max_value ({self.max_value})")

    def generate_values(self) -> List[Any]:
        """
        生成参数值序列

        Returns:
            参数值列表
        """
        if self.values is not None:
            return self.values.copy()

        # 生成连续值序列
        values = []
        current = self.min_value
        while current <= self.max_value:
            values.append(current)
            current += self.step

        return values

    def contains(self, value: Any) -> bool:
        """
        检查值是否在范围内

        Args:
            value: 待检查的值

        Returns:
            是否在范围内
        """
        if self.values is not None:
            return value in self.values

        return self.min_value <= value <= self.max_value

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "values": self.values,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterRange":
        """从字典反序列化"""
        return cls(
            name=data["name"],
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            step=data.get("step"),
            values=data.get("values"),
        )


@dataclass
class OptimizationRun:
    """
    单次优化运行

    存储单次参数组合的回测结果。

    Attributes:
        params: 参数组合
        score: 优化分数
        metrics: 详细指标
    """

    params: Dict[str, Any]
    score: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration: Optional[float] = None

    def set_result(
        self,
        score: float,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        """
        设置运行结果

        Args:
            score: 优化分数
            metrics: 详细指标
        """
        self.score = score
        if metrics:
            self.metrics = metrics

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "params": self.params,
            "score": self.score,
            "metrics": self.metrics,
            "error": self.error,
            "duration": self.duration,
        }


@dataclass
class OptimizationResult:
    """
    优化结果汇总

    存储完整的参数优化结果。

    Attributes:
        strategy_name: 策略名称
        optimizer_type: 优化器类型 (grid, genetic, bayesian)
        param_ranges: 参数范围列表
        results: 所有运行结果
        best_params: 最佳参数
        best_score: 最佳分数
    """

    strategy_name: str = ""
    optimizer_type: str = "grid"
    param_ranges: List[ParameterRange] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    best_params: Optional[Dict[str, Any]] = None
    best_score: Optional[float] = None
    total_runs: int = 0
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_result(
        self,
        params: Dict[str, Any],
        score: float,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        """
        添加运行结果

        Args:
            params: 参数组合
            score: 优化分数
            metrics: 详细指标
        """
        result = {
            "params": params,
            "score": score,
            "metrics": metrics or {},
        }
        self.results.append(result)
        self.total_runs = len(self.results)

        # 更新最佳结果
        if self.best_score is None or score > self.best_score:
            self.best_score = score
            self.best_params = params.copy()

    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """
        获取最佳参数

        Returns:
            最佳参数组合
        """
        if not self.results:
            return None

        best = max(self.results, key=lambda x: x["score"])
        return best["params"].copy()

    def get_top_n(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        获取 Top N 结果

        Args:
            n: 返回数量

        Returns:
            Top N 结果列表
        """
        sorted_results = sorted(
            self.results,
            key=lambda x: x["score"],
            reverse=True,
        )
        return sorted_results[:n]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "strategy_name": self.strategy_name,
            "optimizer_type": self.optimizer_type,
            "param_ranges": [pr.to_dict() for pr in self.param_ranges],
            "results": self.results,
            "best_params": self.best_params,
            "best_score": self.best_score,
            "total_runs": self.total_runs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizationResult":
        """从字典反序列化"""
        param_ranges = [
            ParameterRange.from_dict(pr)
            for pr in data.get("param_ranges", [])
        ]

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            strategy_name=data.get("strategy_name", ""),
            optimizer_type=data.get("optimizer_type", "grid"),
            param_ranges=param_ranges,
            results=data.get("results", []),
            best_params=data.get("best_params"),
            best_score=data.get("best_score"),
            total_runs=data.get("total_runs", 0),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )

    def to_dataframe(self):
        """
        转换为 pandas DataFrame

        Returns:
            结果 DataFrame
        """
        try:
            import pandas as pd
        except ImportError:
            return None

        if not self.results:
            return None

        rows = []
        for result in self.results:
            row = result["params"].copy()
            row["score"] = result["score"]
            row.update(result.get("metrics", {}))
            rows.append(row)

        return pd.DataFrame(rows)
