# Upstream: numpy, scipy, ginkgo.validation.models
# Downstream: ginkgo.client.validation_cli
# Role: 蒙特卡洛模拟 - 随机模拟，计算 VaR/CVaR

"""
MonteCarloSimulator - 蒙特卡洛模拟器

使用蒙特卡洛方法进行风险评估。

核心功能:
- 基于历史收益分布生成随机路径
- 计算 VaR (Value at Risk)
- 计算 CVaR (Conditional VaR / Expected Shortfall)
- 计算各种分位数统计

Usage:
    from ginkgo.validation.monte_carlo import MonteCarloSimulator
    import numpy as np

    returns = np.random.randn(252) * 0.02  # 历史收益率

    simulator = MonteCarloSimulator(
        returns=returns,
        n_simulations=10000,
        confidence_level=0.95,
    )

    result = simulator.run()
    print(f"VaR (95%): {result.var:.2%}")
    print(f"CVaR (95%): {result.cvar:.2%}")
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import time

import numpy as np
import pandas as pd

from ginkgo.validation.models import MonteCarloResult
from ginkgo.libs import GLOG


class MonteCarloSimulator:
    """
    蒙特卡洛模拟器

    使用蒙特卡洛方法模拟资产收益分布，计算风险指标。

    Attributes:
        returns: 历史收益率序列
        n_simulations: 模拟次数
        confidence_level: 置信水平
        time_horizon: 时间范围 (天数)
    """

    def __init__(
        self,
        returns: Union[np.ndarray, pd.DataFrame, pd.Series, List[float]],
        n_simulations: int = 10000,
        confidence_level: float = 0.95,
        time_horizon: int = 1,
        return_col: str = "return",
        seed: Optional[int] = None,
    ):
        """
        初始化蒙特卡洛模拟器

        Args:
            returns: 历史收益率数据
            n_simulations: 模拟次数 (默认 10000)
            confidence_level: 置信水平 (默认 0.95)
            time_horizon: 时间范围/天数 (默认 1)
            return_col: 如果 returns 是 DataFrame，指定收益列名
            seed: 随机种子 (可选，用于可重复性)

        Raises:
            ValueError: 如果收益数据为空或无效
        """
        # 处理不同输入格式
        if isinstance(returns, pd.DataFrame):
            if return_col not in returns.columns:
                raise ValueError(f"DataFrame 中未找到列: {return_col}")
            self.returns = returns[return_col].values
        elif isinstance(returns, pd.Series):
            self.returns = returns.values
        elif isinstance(returns, list):
            self.returns = np.array(returns)
        else:
            self.returns = np.asarray(returns)

        if len(self.returns) == 0:
            raise ValueError("收益数据不能为空")

        self.n_simulations = n_simulations
        self.confidence_level = confidence_level
        self.time_horizon = time_horizon
        self.seed = seed

        # 计算历史统计量
        self._mean = np.mean(self.returns)
        self._std = np.std(self.returns, ddof=1)

        # 缓存结果
        self._result: Optional[MonteCarloResult] = None
        self._simulated_returns: Optional[np.ndarray] = None

        GLOG.INFO(
            f"MonteCarloSimulator 初始化: {n_simulations} 次模拟, "
            f"置信水平 {confidence_level:.0%}, "
            f"时间范围 {time_horizon} 天"
        )

    def run(self) -> MonteCarloResult:
        """
        执行蒙特卡洛模拟

        Returns:
            MonteCarloResult 模拟结果
        """
        start_time = time.time()

        # 设置随机种子
        if self.seed is not None:
            np.random.seed(self.seed)

        GLOG.INFO(f"开始蒙特卡洛模拟: {self.n_simulations} 次")

        # 生成模拟收益
        if self.time_horizon == 1:
            # 单期模拟：直接从历史分布采样
            self._simulated_returns = np.random.choice(
                self.returns,
                size=self.n_simulations,
                replace=True,
            )
        else:
            # 多期模拟：使用 Bootstrap 或参数化方法
            self._simulated_returns = self._simulate_multi_period()

        # 计算统计量
        terminal_values = self._simulated_returns.tolist()
        mean = float(np.mean(self._simulated_returns))
        std = float(np.std(self._simulated_returns))

        # 计算分位数
        percentiles = {
            "p1": float(np.percentile(self._simulated_returns, 1)),
            "p5": float(np.percentile(self._simulated_returns, 5)),
            "p10": float(np.percentile(self._simulated_returns, 10)),
            "p25": float(np.percentile(self._simulated_returns, 25)),
            "p50": float(np.percentile(self._simulated_returns, 50)),
            "p75": float(np.percentile(self._simulated_returns, 75)),
            "p90": float(np.percentile(self._simulated_returns, 90)),
            "p95": float(np.percentile(self._simulated_returns, 95)),
            "p99": float(np.percentile(self._simulated_returns, 99)),
        }

        # 计算 VaR 和 CVaR
        var, cvar = self._calculate_var_cvar(
            self._simulated_returns,
            self.confidence_level,
        )

        # 创建结果
        result = MonteCarloResult(
            n_simulations=self.n_simulations,
            confidence_level=self.confidence_level,
            mean=mean,
            std=std,
            var=var,
            cvar=cvar,
            percentiles=percentiles,
            time_horizon=self.time_horizon,
            terminal_values=terminal_values,
        )

        duration = time.time() - start_time
        GLOG.INFO(
            f"蒙特卡洛模拟完成: 均值 {mean:.4f}, 标准差 {std:.4f}, "
            f"VaR {var:.4f}, CVaR {cvar:.4f}, 耗时 {duration:.2f}s"
        )

        self._result = result
        return result

    def _simulate_multi_period(self) -> np.ndarray:
        """
        多期模拟

        Returns:
            模拟的累计收益数组
        """
        # 使用 Bootstrap 方法
        # 每次模拟随机选择 time_horizon 个日收益并累加
        cumulative_returns = np.zeros(self.n_simulations)

        for i in range(self.n_simulations):
            daily_returns = np.random.choice(
                self.returns,
                size=self.time_horizon,
                replace=True,
            )
            # 累计收益（简单加法，近似对数收益）
            cumulative_returns[i] = np.sum(daily_returns)

        return cumulative_returns

    def _calculate_var_cvar(
        self,
        returns: np.ndarray,
        confidence: float,
    ) -> tuple:
        """
        计算 VaR 和 CVaR

        Args:
            returns: 收益数组
            confidence: 置信水平

        Returns:
            (VaR, CVaR) 元组
        """
        alpha = 1 - confidence

        # VaR = alpha 分位数 (左侧)
        var = float(np.percentile(returns, alpha * 100))

        # CVaR = 低于 VaR 的期望值
        tail_returns = returns[returns <= var]
        if len(tail_returns) > 0:
            cvar = float(np.mean(tail_returns))
        else:
            cvar = var

        return var, cvar

    def calculate_var(self, confidence: Optional[float] = None) -> float:
        """
        计算风险价值 (VaR)

        Args:
            confidence: 置信水平 (可选，默认使用初始化时的值)

        Returns:
            VaR 值
        """
        if self._simulated_returns is None:
            self.run()

        conf = confidence or self.confidence_level
        alpha = 1 - conf
        return float(np.percentile(self._simulated_returns, alpha * 100))

    def calculate_cvar(self, confidence: Optional[float] = None) -> float:
        """
        计算条件风险价值 (CVaR / Expected Shortfall)

        Args:
            confidence: 置信水平 (可选，默认使用初始化时的值)

        Returns:
            CVaR 值
        """
        if self._simulated_returns is None:
            self.run()

        conf = confidence or self.confidence_level
        var = self.calculate_var(conf)

        tail_returns = self._simulated_returns[self._simulated_returns <= var]
        if len(tail_returns) > 0:
            return float(np.mean(tail_returns))
        return var

    def get_summary(self) -> Dict[str, Any]:
        """
        获取模拟摘要

        Returns:
            摘要字典
        """
        if self._result is None:
            return {"status": "not_run"}

        return {
            "n_simulations": self.n_simulations,
            "confidence_level": self.confidence_level,
            "time_horizon": self.time_horizon,
            "historical_mean": self._mean,
            "historical_std": self._std,
            "simulated_mean": self._result.mean,
            "simulated_std": self._result.std,
            "var": self._result.var,
            "cvar": self._result.cvar,
        }

    def get_percentile(self, percentile: int) -> float:
        """
        获取指定分位数的值

        Args:
            percentile: 分位数 (0-100)

        Returns:
            分位数值
        """
        if self._simulated_returns is None:
            self.run()

        return float(np.percentile(self._simulated_returns, percentile))
