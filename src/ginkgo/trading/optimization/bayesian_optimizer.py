# Upstream: ginkgo.trading.optimization.base_optimizer, models
# Downstream: ginkgo.client.optimization_cli
# Role: 贝叶斯优化器 - 使用 optuna 库实现

"""
BayesianOptimizer - 贝叶斯优化器

使用贝叶斯优化进行参数搜索。

核心功能:
- 高斯过程建模
- 采集函数优化
- 自适应采样

Usage:
    from ginkgo.trading.optimization.bayesian_optimizer import BayesianOptimizer
    from ginkgo.trading.optimization.models import ParameterRange

    param_ranges = [
        ParameterRange(name="fast", min_value=5, max_value=20, step=1),
        ParameterRange(name="slow", min_value=20, max_value=60, step=1),
    ]

    optimizer = BayesianOptimizer(
        param_ranges=param_ranges,
        n_trials=50,
    )
    optimizer.set_backtest_function(my_backtest)
    result = optimizer.optimize(data=backtest_data)
    print(f"最佳参数: {result.best_params}")
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import time

from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
from ginkgo.trading.optimization.models import OptimizationResult, ParameterRange
from ginkgo.libs import GLOG

# Optional dependency
try:
    import optuna
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


class BayesianOptimizer(BaseOptimizer):
    """
    贝叶斯优化器

    使用 optuna 库实现贝叶斯优化。

    Attributes:
        n_trials: 优化迭代次数
        sampler_type: 采样器类型
    """

    def __init__(
        self,
        param_ranges: List[ParameterRange],
        maximize: bool = True,
        n_trials: int = 50,
        sampler_type: str = "tpe",
    ):
        """
        初始化贝叶斯优化器

        Args:
            param_ranges: 参数范围列表
            maximize: 是否最大化目标 (默认 True)
            n_trials: 优化迭代次数 (默认 50)
            sampler_type: 采样器类型 (默认 "tpe")
        """
        super().__init__(param_ranges=param_ranges, maximize=maximize)

        if not OPTUNA_AVAILABLE:
            raise ImportError(
                "optuna 库未安装。请使用: pip install optuna 或 pip install -e '.[optimization]'"
            )

        self.n_trials = n_trials
        self.sampler_type = sampler_type
        self._study = None
        self._data = None

        GLOG.INFO(f"BayesianOptimizer 初始化: {n_trials} 次迭代")

    def _objective(self, trial) -> float:
        """
        Optuna 目标函数

        Args:
            trial: Optuna trial 对象

        Returns:
            目标值
        """
        params = {}

        for pr in self.param_ranges:
            values = pr.generate_values()

            if len(values) == 1:
                # 只有一个值
                params[pr.name] = values[0]
            elif isinstance(values[0], int):
                # 整数参数
                params[pr.name] = trial.suggest_int(
                    pr.name,
                    min(values),
                    max(values),
                )
            elif isinstance(values[0], float):
                # 浮点参数
                params[pr.name] = trial.suggest_float(
                    pr.name,
                    min(values),
                    max(values),
                )
            else:
                # 离散参数
                params[pr.name] = trial.suggest_categorical(pr.name, values)

        # 运行回测
        result = self._run_backtest(params, self._data)
        score = result.get("score", float("-inf"))

        return score

    def optimize(self, data: Any, **kwargs) -> OptimizationResult:
        """
        执行贝叶斯优化

        Args:
            data: 回测数据
            **kwargs: 其他参数

        Returns:
            OptimizationResult 优化结果
        """
        start_time = time.time()
        result = self._create_result("bayesian")

        # 存储数据供目标函数使用
        self._data = data

        # 创建采样器
        if self.sampler_type == "tpe":
            sampler = TPESampler(seed=42)
        else:
            sampler = TPESampler(seed=42)

        # 创建方向字符串
        direction = "maximize" if self.maximize else "minimize"

        # 创建 study
        self._study = optuna.create_study(
            direction=direction,
            sampler=sampler,
        )

        # 自定义回调来记录结果
        def callback(study, trial):
            params = trial.params
            score = trial.value
            result.add_result(params, score)
            self._progress["completed"] += 1

        self._progress = {"total": self.n_trials, "completed": 0}

        GLOG.INFO(f"开始贝叶斯优化: {self.n_trials} 次迭代")

        # 运行优化
        self._study.optimize(
            self._objective,
            n_trials=self.n_trials,
            callbacks=[callback],
            show_progress_bar=False,
        )

        # 设置最佳结果
        if self._study.best_trial:
            result.best_params = self._study.best_trial.params.copy()
            result.best_score = self._study.best_trial.value

        duration = time.time() - start_time
        GLOG.INFO(
            f"贝叶斯优化完成: {result.total_runs} 次评估, "
            f"耗时 {duration:.2f}s, 最佳分数 {result.best_score}"
        )

        return result

    def get_progress(self) -> Dict[str, int]:
        """获取优化进度"""
        return self._progress.copy()

    def get_importance(self) -> Dict[str, float]:
        """
        获取参数重要性

        Returns:
            参数重要性字典
        """
        if self._study is None:
            return {}

        try:
            importance = optuna.importance.get_param_importances(self._study)
            return dict(importance)
        except Exception:
            return {}
