# Upstream: typing, dataclasses
# Downstream: ginkgo.validation.walk_forward
# Role: 验证模块数据模型 - 走步验证结果等

"""
验证模块数据模型

定义验证相关的数据结构:
- WalkForwardFold: 单折验证数据
- WalkForwardResult: 走步验证结果
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import uuid
import numpy as np


@dataclass
class WalkForwardFold:
    """
    单折验证数据

    存储走步验证中单个折的训练和测试结果。

    Attributes:
        fold_num: 折编号
        train_start: 训练期开始日期
        train_end: 训练期结束日期
        test_start: 测试期开始日期
        test_end: 测试期结束日期
        train_score: 训练期分数
        test_score: 测试期分数
    """

    fold_num: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_score: Optional[float] = None
    test_score: Optional[float] = None
    train_metrics: Dict[str, Any] = field(default_factory=dict)
    test_metrics: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "fold_num": self.fold_num,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "train_score": self.train_score,
            "test_score": self.test_score,
            "train_metrics": self.train_metrics,
            "test_metrics": self.test_metrics,
            "params": self.params,
        }


@dataclass
class WalkForwardResult:
    """
    走步验证结果

    存储完整的走步验证结果。

    Attributes:
        n_folds: 折数
        folds: 各折结果
        mean_train_score: 平均训练分数
        mean_test_score: 平均测试分数
        degradation: 退化程度
    """

    n_folds: int
    folds: List[WalkForwardFold] = field(default_factory=list)
    mean_train_score: float = 0.0
    mean_test_score: float = 0.0
    std_train_score: float = 0.0
    std_test_score: float = 0.0
    degradation: float = 0.0
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_fold_result(self, fold: WalkForwardFold):
        """
        添加折结果

        Args:
            fold: 单折结果
        """
        self.folds.append(fold)

        # 重新计算统计
        train_scores = [f.train_score for f in self.folds if f.train_score is not None]
        test_scores = [f.test_score for f in self.folds if f.test_score is not None]

        if train_scores:
            self.mean_train_score = sum(train_scores) / len(train_scores)
            if len(train_scores) > 1:
                self.std_train_score = (
                    sum((s - self.mean_train_score) ** 2 for s in train_scores)
                    / (len(train_scores) - 1)
                ) ** 0.5

        if test_scores:
            self.mean_test_score = sum(test_scores) / len(test_scores)
            if len(test_scores) > 1:
                self.std_test_score = (
                    sum((s - self.mean_test_score) ** 2 for s in test_scores)
                    / (len(test_scores) - 1)
                ) ** 0.5

    def calculate_degradation(self) -> float:
        """
        计算退化程度

        退化程度 = (train_score - test_score) / train_score

        Returns:
            退化程度 (0-1)
        """
        if self.mean_train_score == 0:
            return 0.0

        self.degradation = (
            self.mean_train_score - self.mean_test_score
        ) / self.mean_train_score
        return self.degradation

    def is_overfitting(self, threshold: float = 0.2) -> bool:
        """
        判断是否过拟合

        Args:
            threshold: 退化阈值 (默认 0.2)

        Returns:
            是否过拟合
        """
        degradation = self.calculate_degradation()
        return degradation > threshold

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "n_folds": self.n_folds,
            "folds": [f.to_dict() for f in self.folds],
            "mean_train_score": self.mean_train_score,
            "mean_test_score": self.mean_test_score,
            "std_train_score": self.std_train_score,
            "std_test_score": self.std_test_score,
            "degradation": self.calculate_degradation(),
            "is_overfitting": self.is_overfitting(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalkForwardResult":
        """从字典反序列化"""
        folds = [
            WalkForwardFold(**f) for f in data.get("folds", [])
        ]

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            n_folds=data.get("n_folds", 0),
            folds=folds,
            mean_train_score=data.get("mean_train_score", 0.0),
            mean_test_score=data.get("mean_test_score", 0.0),
            std_train_score=data.get("std_train_score", 0.0),
            std_test_score=data.get("std_test_score", 0.0),
            degradation=data.get("degradation", 0.0),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class MonteCarloResult:
    """
    蒙特卡洛模拟结果

    存储蒙特卡洛模拟的完整结果。

    Attributes:
        n_simulations: 模拟次数
        confidence_level: 置信水平
        mean: 模拟均值
        std: 模拟标准差
        var: 风险价值 (Value at Risk)
        cvar: 条件风险价值 (Conditional VaR / Expected Shortfall)
        percentiles: 分位数字典
    """

    n_simulations: int
    confidence_level: float = 0.95
    mean: float = 0.0
    std: float = 0.0
    var: float = 0.0
    cvar: float = 0.0
    percentiles: Dict[str, float] = field(default_factory=dict)
    time_horizon: int = 1
    paths: Optional[List[List[float]]] = None
    terminal_values: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def get_var(self, confidence: Optional[float] = None) -> float:
        """
        获取 VaR

        Args:
            confidence: 置信水平 (可选，默认使用初始化时的值)

        Returns:
            VaR 值
        """
        if confidence is not None and self.terminal_values:
            alpha = 1 - confidence
            return float(np.percentile(self.terminal_values, alpha * 100))
        return self.var

    def get_cvar(self, confidence: Optional[float] = None) -> float:
        """
        获取 CVaR (Expected Shortfall)

        Args:
            confidence: 置信水平 (可选，默认使用初始化时的值)

        Returns:
            CVaR 值
        """
        if confidence is not None and self.terminal_values:
            alpha = 1 - confidence
            var_threshold = np.percentile(self.terminal_values, alpha * 100)
            tail_values = [v for v in self.terminal_values if v <= var_threshold]
            if tail_values:
                return float(np.mean(tail_values))
        return self.cvar

    def get_probability_of_loss(self, threshold: float = 0.0) -> float:
        """
        获取损失概率

        Args:
            threshold: 损失阈值 (默认 0)

        Returns:
            损失概率
        """
        if self.terminal_values:
            losses = sum(1 for v in self.terminal_values if v < threshold)
            return losses / len(self.terminal_values)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "n_simulations": self.n_simulations,
            "confidence_level": self.confidence_level,
            "mean": self.mean,
            "std": self.std,
            "var": self.var,
            "cvar": self.cvar,
            "percentiles": self.percentiles,
            "time_horizon": self.time_horizon,
            "probability_of_loss": self.get_probability_of_loss(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonteCarloResult":
        """从字典反序列化"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            n_simulations=data.get("n_simulations", 0),
            confidence_level=data.get("confidence_level", 0.95),
            mean=data.get("mean", 0.0),
            std=data.get("std", 0.0),
            var=data.get("var", 0.0),
            cvar=data.get("cvar", 0.0),
            percentiles=data.get("percentiles", {}),
            time_horizon=data.get("time_horizon", 1),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )
