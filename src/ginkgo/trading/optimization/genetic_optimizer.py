# Upstream: ginkgo.trading.optimization.base_optimizer, models
# Downstream: ginkgo.client.optimization_cli
# Role: 遗传算法优化器 - 使用 deap 库实现进化优化

"""
GeneticOptimizer - 遗传算法优化器

使用遗传算法进行参数优化。

核心功能:
- 种群初始化
- 适应度评估
- 选择、交叉、变异操作
- 多代进化

Usage:
    from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer
    from ginkgo.trading.optimization.models import ParameterRange

    param_ranges = [
        ParameterRange(name="fast", min_value=5, max_value=20, step=1),
        ParameterRange(name="slow", min_value=20, max_value=60, step=1),
    ]

    optimizer = GeneticOptimizer(
        param_ranges=param_ranges,
        population_size=50,
        generations=20,
    )
    optimizer.set_backtest_function(my_backtest)
    result = optimizer.optimize(data=backtest_data)
    print(f"最佳参数: {result.best_params}")
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import time
import random

from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
from ginkgo.trading.optimization.models import OptimizationResult, ParameterRange
from ginkgo.libs import GLOG

# Optional dependency
try:
    from deap import base, creator, tools, algorithms
    DEAP_AVAILABLE = True
except ImportError:
    DEAP_AVAILABLE = False


class GeneticOptimizer(BaseOptimizer):
    """
    遗传算法优化器

    使用 deap 库实现遗传算法优化。

    Attributes:
        population_size: 种群大小
        generations: 迭代代数
        crossover_prob: 交叉概率
        mutation_prob: 变异概率
    """

    def __init__(
        self,
        param_ranges: List[ParameterRange],
        maximize: bool = True,
        population_size: int = 50,
        generations: int = 20,
        crossover_prob: float = 0.7,
        mutation_prob: float = 0.2,
    ):
        """
        初始化遗传算法优化器

        Args:
            param_ranges: 参数范围列表
            maximize: 是否最大化目标 (默认 True)
            population_size: 种群大小 (默认 50)
            generations: 迭代代数 (默认 20)
            crossover_prob: 交叉概率 (默认 0.7)
            mutation_prob: 变异概率 (默认 0.2)
        """
        super().__init__(param_ranges=param_ranges, maximize=maximize)

        if not DEAP_AVAILABLE:
            raise ImportError(
                "deap 库未安装。请使用: pip install deap 或 pip install -e '.[optimization]'"
            )

        self.population_size = population_size
        self.generations = generations
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob

        self._toolbox = None
        self._setup_deap()

        GLOG.INFO(
            f"GeneticOptimizer 初始化: 种群 {population_size}, 代数 {generations}"
        )

    def _setup_deap(self):
        """设置 DEAP 工具箱"""
        # 清理之前创建的类（避免重复运行时的警告）
        if hasattr(creator, "FitnessMax"):
            delattr(creator, "FitnessMax")
        if hasattr(creator, "FitnessMin"):
            delattr(creator, "FitnessMin")
        if hasattr(creator, "Individual"):
            delattr(creator, "Individual")

        # 创建适应度类
        if self.maximize:
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
            fitness_class = creator.FitnessMax
        else:
            creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
            fitness_class = creator.FitnessMin

        # 创建个体类
        creator.create("Individual", list, fitness=fitness_class)

        # 创建工具箱
        self._toolbox = base.Toolbox()

        # 注册属性生成器
        for i, pr in enumerate(self.param_ranges):
            values = pr.generate_values()
            attr_name = f"attr_{i}"
            self._toolbox.register(attr_name, random.choice, values)

        # 注册个体和种群生成器
        attr_names = [f"attr_{i}" for i in range(len(self.param_ranges))]

        def create_individual():
            return creator.Individual([
                getattr(self._toolbox, attr)() for attr in attr_names
            ])

        self._toolbox.register("individual", create_individual)
        self._toolbox.register("population", tools.initRepeat, list, self._toolbox.individual)

        # 注册遗传操作
        self._toolbox.register("mate", tools.cxTwoPoint)
        self._toolbox.register(
            "mutate",
            self._mutate_individual,
            ind_prob=self.mutation_prob,
        )
        self._toolbox.register("select", tools.selTournament, tournsize=3)

    def _mutate_individual(self, individual, ind_prob):
        """变异操作"""
        for i in range(len(individual)):
            if random.random() < ind_prob:
                values = self.param_ranges[i].generate_values()
                individual[i] = random.choice(values)
        return individual,

    def _evaluate(self, individual, data):
        """评估个体适应度"""
        params = {
            pr.name: individual[i]
            for i, pr in enumerate(self.param_ranges)
        }
        result = self._run_backtest(params, data)
        score = result.get("score", float("-inf"))
        return (score,)

    def optimize(self, data: Any, **kwargs) -> OptimizationResult:
        """
        执行遗传算法优化

        Args:
            data: 回测数据
            **kwargs: 其他参数

        Returns:
            OptimizationResult 优化结果
        """
        start_time = time.time()
        result = self._create_result("genetic")

        # 注册评估函数
        self._toolbox.register("evaluate", self._evaluate, data=data)

        # 创建初始种群
        population = self._toolbox.population(n=self.population_size)

        # 评估初始种群
        fitnesses = list(map(self._toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit
            params = {
                pr.name: ind[i]
                for i, pr in enumerate(self.param_ranges)
            }
            result.add_result(params, fit[0])

        self._progress = {
            "total": self.population_size * self.generations,
            "completed": self.population_size,
        }

        GLOG.INFO(f"开始遗传算法优化: 种群 {self.population_size}, 代数 {self.generations}")

        # 进化循环
        for gen in range(self.generations):
            # 选择下一代
            offspring = self._toolbox.select(population, len(population))
            offspring = list(map(self._toolbox.clone, offspring))

            # 交叉
            for i in range(1, len(offspring), 2):
                if random.random() < self.crossover_prob:
                    offspring[i - 1], offspring[i] = self._toolbox.mate(
                        offspring[i - 1], offspring[i]
                    )
                    del offspring[i - 1].fitness.values
                    del offspring[i].fitness.values

            # 变异
            for i in range(len(offspring)):
                if random.random() < self.mutation_prob:
                    offspring[i], = self._toolbox.mutate(offspring[i])
                    del offspring[i].fitness.values

            # 评估新个体
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = list(map(self._toolbox.evaluate, invalid_ind))
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
                params = {
                    pr.name: ind[i]
                    for i, pr in enumerate(self.param_ranges)
                }
                result.add_result(params, fit[0])

            # 替换种群
            population[:] = offspring
            self._progress["completed"] += len(invalid_ind)

            # 日志
            fits = [ind.fitness.values[0] for ind in population]
            GLOG.INFO(
                f"代 {gen + 1}/{self.generations}: "
                f"最佳 {max(fits):.4f}, 平均 {sum(fits)/len(fits):.4f}"
            )

        # 设置最佳结果
        if result.results:
            if self.maximize:
                best = max(result.results, key=lambda x: x["score"])
            else:
                best = min(result.results, key=lambda x: x["score"])
            result.best_params = best["params"].copy()
            result.best_score = best["score"]

        duration = time.time() - start_time
        GLOG.INFO(
            f"遗传算法完成: {result.total_runs} 次评估, "
            f"耗时 {duration:.2f}s, 最佳分数 {result.best_score}"
        )

        return result

    def get_progress(self) -> Dict[str, int]:
        """获取优化进度"""
        return self._progress.copy()
