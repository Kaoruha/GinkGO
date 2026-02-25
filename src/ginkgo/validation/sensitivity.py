# Upstream: numpy, pandas, ginkgo.validation.models
# Downstream: ginkgo.client.validation_cli
# Role: 参数敏感性分析 - 分析单个参数变化的影响

"""
SensitivityAnalyzer - 参数敏感性分析

分析单个参数变化对策略表现的影响。

核心功能:
- 测试参数在不同值下的表现
- 计算敏感性分数
- 计算弹性系数
- 找出最优参数值

Usage:
    from ginkgo.validation.sensitivity import SensitivityAnalyzer

    analyzer = SensitivityAnalyzer(
        param_name="fast_period",
        base_value=10,
        test_values=[5, 10, 15, 20, 25],
    )
    analyzer.set_backtest_function(my_backtest)
    result = analyzer.analyze()
    print(f"敏感性分数: {result.get_sensitivity_score()}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Union
import time

import numpy as np
import pandas as pd

from ginkgo.libs import GLOG


@dataclass
class SensitivityResult:
    """
    敏感性分析结果

    存储参数敏感性分析的完整结果。

    Attributes:
        param_name: 参数名
        base_value: 基准值
        values: 测试值列表
        scores: 各值对应分数
    """

    param_name: str
    base_value: Union[int, float]
    values: List[Union[int, float]] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def get_sensitivity_score(self) -> float:
        """
        获取敏感性分数

        计算分数变化范围相对于基准分数的比例。

        Returns:
            敏感性分数
        """
        if not self.scores:
            return 0.0

        score_range = max(self.scores) - min(self.scores)
        base_score = self.scores[self.values.index(self.base_value)] if self.base_value in self.values else np.mean(self.scores)

        if base_score == 0:
            return score_range

        return score_range / abs(base_score)

    def get_elasticity(self) -> float:
        """
        获取弹性系数

        计算分数对参数变化的敏感程度。

        Returns:
            弹性系数
        """
        if len(self.values) < 2 or len(self.scores) < 2:
            return 0.0

        # 使用线性回归估计弹性
        x = np.array(self.values)
        y = np.array(self.scores)

        # 计算斜率
        slope = np.polyfit(x, y, 1)[0]

        # 归一化斜率
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        if x_mean == 0 or y_mean == 0:
            return 0.0

        elasticity = slope * x_mean / y_mean
        return float(elasticity)

    def get_optimal_value(self) -> Union[int, float]:
        """
        获取最优参数值

        Returns:
            分数最高的参数值
        """
        if not self.scores:
            return self.base_value

        best_idx = np.argmax(self.scores)
        return self.values[best_idx]

    def get_optimal_score(self) -> float:
        """获取最优分数"""
        if not self.scores:
            return 0.0
        return max(self.scores)

    def to_dataframe(self) -> pd.DataFrame:
        """
        转换为 DataFrame

        Returns:
            结果 DataFrame
        """
        if not self.values:
            return pd.DataFrame()

        return pd.DataFrame({
            "value": self.values,
            "score": self.scores,
        })

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "param_name": self.param_name,
            "base_value": self.base_value,
            "values": self.values,
            "scores": self.scores,
            "sensitivity_score": self.get_sensitivity_score(),
            "elasticity": self.get_elasticity(),
            "optimal_value": self.get_optimal_value(),
            "optimal_score": self.get_optimal_score(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }


class SensitivityAnalyzer:
    """
    参数敏感性分析器

    分析单个参数变化对策略表现的影响。

    Attributes:
        param_name: 参数名
        base_value: 基准值
        test_values: 测试值列表
    """

    def __init__(
        self,
        param_name: str,
        base_value: Union[int, float],
        test_values: List[Union[int, float]],
    ):
        """
        初始化敏感性分析器

        Args:
            param_name: 参数名
            base_value: 基准值
            test_values: 测试值列表
        """
        self.param_name = param_name
        self.base_value = base_value
        self.test_values = test_values

        self._backtest_function: Optional[Callable] = None
        self._result: Optional[SensitivityResult] = None

        GLOG.INFO(
            f"SensitivityAnalyzer 初始化: 参数 {param_name}, "
            f"基准值 {base_value}, 测试值数量 {len(test_values)}"
        )

    def set_backtest_function(self, func: Callable):
        """
        设置回测函数

        Args:
            func: 回测函数，签名 func(params: Dict, data: Any) -> Dict
        """
        self._backtest_function = func

    def analyze(self, data: Any = None) -> SensitivityResult:
        """
        执行敏感性分析

        Args:
            data: 回测数据 (可选)

        Returns:
            SensitivityResult 分析结果
        """
        start_time = time.time()

        if self._backtest_function is None:
            raise ValueError("未设置回测函数，请调用 set_backtest_function()")

        result = SensitivityResult(
            param_name=self.param_name,
            base_value=self.base_value,
        )

        GLOG.INFO(f"开始敏感性分析: {self.param_name}")

        for value in self.test_values:
            params = {self.param_name: value}

            try:
                backtest_result = self._backtest_function(params, data)
                score = backtest_result.get("score", 0.0)

                result.values.append(value)
                result.scores.append(score)
                result.metrics.append(backtest_result)

            except Exception as e:
                GLOG.ERROR(f"回测失败 ({self.param_name}={value}): {e}")
                result.values.append(value)
                result.scores.append(float("-inf"))
                result.metrics.append({"error": str(e)})

        duration = time.time() - start_time
        GLOG.INFO(
            f"敏感性分析完成: {len(result.values)} 个值, "
            f"敏感性分数 {result.get_sensitivity_score():.4f}, "
            f"耗时 {duration:.2f}s"
        )

        self._result = result
        return result

    def get_result(self) -> Optional[SensitivityResult]:
        """获取分析结果"""
        return self._result

    def get_summary(self) -> Dict[str, Any]:
        """
        获取分析摘要

        Returns:
            摘要字典
        """
        if self._result is None:
            return {"status": "not_analyzed"}

        return self._result.to_dict()
