# Upstream: abc, typing, ginkgo.trading.optimization.models
# Downstream: ginkgo.trading.optimization.grid_search, genetic_optimizer, bayesian_optimizer
# Role: 优化器基类 - 定义抽象接口和通用方法

"""
BaseOptimizer - 优化器基类

定义参数优化器的通用接口。

核心功能:
- 定义抽象方法 optimize()
- 参数验证方法
- 参数组合生成
- 优化目标设置
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Tuple
import itertools

from ginkgo.trading.optimization.models import ParameterRange, OptimizationResult
from ginkgo.libs import GLOG


class BaseOptimizer(ABC):
    """
    优化器基类

    所有优化器的抽象基类，定义通用接口。

    Attributes:
        param_ranges: 参数范围列表
        objective_metric: 优化目标指标
        maximize: 是否最大化 (True) 或最小化 (False)
    """

    def __init__(
        self,
        param_ranges: List[ParameterRange],
        maximize: bool = True,
    ):
        """
        初始化优化器

        Args:
            param_ranges: 参数范围列表
            maximize: 是否最大化目标 (默认 True)
        """
        self.param_ranges = param_ranges
        self.maximize = maximize
        self.objective_metric = "score"
        self._backtest_function: Optional[Callable] = None
        self._progress = {"total": 0, "completed": 0}

        GLOG.INFO(f"BaseOptimizer 初始化: {len(param_ranges)} 个参数范围")

    @abstractmethod
    def optimize(self, data: Any, **kwargs) -> OptimizationResult:
        """
        执行优化

        Args:
            data: 回测数据
            **kwargs: 其他参数

        Returns:
            OptimizationResult 优化结果
        """
        pass

    def set_backtest_function(self, func: Callable):
        """
        设置回测函数

        Args:
            func: 回测函数，签名 func(params: Dict, data: Any) -> Dict
        """
        self._backtest_function = func

    def set_objective(self, metric: str, maximize: bool = True):
        """
        设置优化目标

        Args:
            metric: 目标指标名称
            maximize: 是否最大化
        """
        self.objective_metric = metric
        self.maximize = maximize

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        验证参数是否在范围内

        Args:
            params: 参数字典

        Returns:
            是否有效
        """
        param_dict = {pr.name: pr for pr in self.param_ranges}

        for name, value in params.items():
            if name not in param_dict:
                return False
            if not param_dict[name].contains(value):
                return False

        return True

    def generate_param_combinations(self) -> List[Dict[str, Any]]:
        """
        生成所有参数组合

        Returns:
            参数组合列表
        """
        if not self.param_ranges:
            return [{}]

        # 获取每个参数的值列表
        param_values = [pr.generate_values() for pr in self.param_ranges]
        param_names = [pr.name for pr in self.param_ranges]

        # 生成所有组合
        combinations = []
        for values in itertools.product(*param_values):
            combo = dict(zip(param_names, values))
            combinations.append(combo)

        return combinations

    def get_param_space_size(self) -> int:
        """
        获取参数空间大小

        Returns:
            参数组合总数
        """
        if not self.param_ranges:
            return 1

        size = 1
        for pr in self.param_ranges:
            size *= len(pr.generate_values())

        return size

    def get_progress(self) -> Dict[str, int]:
        """
        获取优化进度

        Returns:
            进度字典 {total, completed}
        """
        return self._progress.copy()

    def _run_backtest(
        self,
        params: Dict[str, Any],
        data: Any,
    ) -> Dict[str, Any]:
        """
        执行单次回测

        Args:
            params: 参数组合
            data: 回测数据

        Returns:
            回测结果字典
        """
        if self._backtest_function is None:
            raise ValueError("未设置回测函数，请调用 set_backtest_function()")

        try:
            result = self._backtest_function(params, data)
            return result
        except Exception as e:
            GLOG.ERROR(f"回测失败 (params={params}): {e}")
            return {"score": float("-inf"), "error": str(e)}

    def _create_result(self, optimizer_type: str) -> OptimizationResult:
        """
        创建优化结果对象

        Args:
            optimizer_type: 优化器类型

        Returns:
            OptimizationResult 对象
        """
        return OptimizationResult(
            optimizer_type=optimizer_type,
            param_ranges=self.param_ranges,
        )
