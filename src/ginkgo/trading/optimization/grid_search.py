# Upstream: ginkgo.trading.optimization.base_optimizer, models
# Downstream: ginkgo.client.optimization_cli
# Role: 网格搜索优化器 - 遍历所有参数组合

"""
GridSearchOptimizer - 网格搜索优化器

遍历所有参数组合，找到最优参数。

核心功能:
- 生成完整参数网格
- 遍历所有组合并回测
- 按目标指标排序
- 支持并行执行

Usage:
    from ginkgo.trading.optimization.grid_search import GridSearchOptimizer
    from ginkgo.trading.optimization.models import ParameterRange

    param_ranges = [
        ParameterRange(name="fast", min_value=5, max_value=20, step=5),
        ParameterRange(name="slow", min_value=20, max_value=60, step=10),
    ]

    optimizer = GridSearchOptimizer(param_ranges=param_ranges)
    optimizer.set_backtest_function(my_backtest)
    result = optimizer.optimize(data=backtest_data)
    print(f"最佳参数: {result.best_params}")
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
from ginkgo.trading.optimization.models import OptimizationResult
from ginkgo.libs import GLOG


class GridSearchOptimizer(BaseOptimizer):
    """
    网格搜索优化器

    遍历所有参数组合进行优化。

    Attributes:
        n_jobs: 并行任务数 (默认 1，串行)
        early_stopping: 是否启用早停
        target_score: 目标分数 (早停阈值)
    """

    def __init__(
        self,
        param_ranges: List,
        maximize: bool = True,
        n_jobs: int = 1,
        early_stopping: bool = False,
        target_score: Optional[float] = None,
    ):
        """
        初始化网格搜索优化器

        Args:
            param_ranges: 参数范围列表
            maximize: 是否最大化目标 (默认 True)
            n_jobs: 并行任务数 (默认 1)
            early_stopping: 是否启用早停
            target_score: 早停目标分数
        """
        super().__init__(param_ranges=param_ranges, maximize=maximize)
        self.n_jobs = n_jobs
        self.early_stopping = early_stopping
        self.target_score = target_score

        # 计算总组合数
        self._grid = None
        GLOG.INFO(f"GridSearchOptimizer 初始化: 参数空间大小 {self.get_param_space_size()}")

    def generate_grid(self) -> List[Dict[str, Any]]:
        """
        生成参数网格

        Returns:
            参数组合列表
        """
        if self._grid is None:
            self._grid = self.generate_param_combinations()
        return self._grid

    def optimize(self, data: Any, **kwargs) -> OptimizationResult:
        """
        执行网格搜索优化

        Args:
            data: 回测数据
            **kwargs: 其他参数

        Returns:
            OptimizationResult 优化结果
        """
        start_time = time.time()
        result = self._create_result("grid")

        # 生成网格
        grid = self.generate_grid()
        total = len(grid)
        self._progress = {"total": total, "completed": 0}

        GLOG.INFO(f"开始网格搜索: {total} 个组合")

        if self.n_jobs > 1:
            # 并行执行
            self._optimize_parallel(grid, data, result)
        else:
            # 串行执行
            self._optimize_serial(grid, data, result)

        # 按分数排序
        if self.maximize:
            result.results.sort(key=lambda x: x["score"], reverse=True)
        else:
            result.results.sort(key=lambda x: x["score"], reverse=False)

        # 设置最佳结果（根据 maximize 参数选择）
        if result.results:
            if self.maximize:
                best = max(result.results, key=lambda x: x["score"])
            else:
                best = min(result.results, key=lambda x: x["score"])
            result.best_params = best["params"].copy()
            result.best_score = best["score"]

        duration = time.time() - start_time
        GLOG.INFO(f"网格搜索完成: {total} 个组合, 耗时 {duration:.2f}s, 最佳分数 {result.best_score}")

        return result

    def _optimize_serial(
        self,
        grid: List[Dict[str, Any]],
        data: Any,
        result: OptimizationResult,
    ):
        """串行优化"""
        for params in grid:
            backtest_result = self._run_backtest(params, data)
            score = backtest_result.get("score", float("-inf"))
            metrics = {k: v for k, v in backtest_result.items() if k != "score"}

            result.add_result(params, score, metrics)
            self._progress["completed"] += 1

            # 检查早停
            if self.early_stopping and self.target_score is not None:
                if self.maximize and score >= self.target_score:
                    GLOG.INFO(f"达到目标分数 {score} >= {self.target_score}，早停")
                    break
                elif not self.maximize and score <= self.target_score:
                    GLOG.INFO(f"达到目标分数 {score} <= {self.target_score}，早停")
                    break

    def _optimize_parallel(
        self,
        grid: List[Dict[str, Any]],
        data: Any,
        result: OptimizationResult,
    ):
        """并行优化"""
        early_stop = False

        with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
            futures = {
                executor.submit(self._run_backtest, params, data): params
                for params in grid
            }

            for future in as_completed(futures):
                if early_stop:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                params = futures[future]
                try:
                    backtest_result = future.result()
                    score = backtest_result.get("score", float("-inf"))
                    metrics = {k: v for k, v in backtest_result.items() if k != "score"}

                    result.add_result(params, score, metrics)
                    self._progress["completed"] += 1

                    # 检查早停
                    if self.early_stopping and self.target_score is not None:
                        if self.maximize and score >= self.target_score:
                            GLOG.INFO(f"达到目标分数 {score} >= {self.target_score}，早停")
                            early_stop = True
                        elif not self.maximize and score <= self.target_score:
                            GLOG.INFO(f"达到目标分数 {score} <= {self.target_score}，早停")
                            early_stop = True

                except Exception as e:
                    GLOG.ERROR(f"并行回测失败 (params={params}): {e}")
                    result.add_result(params, float("-inf"), {"error": str(e)})
                    self._progress["completed"] += 1

    def get_progress(self) -> Dict[str, int]:
        """获取优化进度"""
        return self._progress.copy()
