# Upstream: base.Metric Protocol, base.DataProvider
# Downstream: AnalysisEngine, 分析报告
# Role: 组合层级指标实现 (年化收益、最大回撤、夏普比率等)


"""
组合层级分析指标

提供8个核心组合级指标：年化收益率、最大回撤、夏普比率、索提诺比率、
波动率、卡尔玛比率、滚动夏普比率和滚动波动率。
"""

import math
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .base import Metric


# ============================================================
# Helper
# ============================================================

def _daily_returns(nav: pd.Series) -> pd.Series:
    """计算日收益率序列

    Args:
        nav: 净值序列

    Returns:
        去除NaN的日收益率序列
    """
    return nav.pct_change().dropna()


# ============================================================
# 1. AnnualizedReturn
# ============================================================

class AnnualizedReturn(Metric):
    """年化收益率

    公式: (final_value / initial_value) ** (252 / n) - 1
    """
    name: str = "annualized_return"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self):
        self.params = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        nav = data["net_value"]["value"]
        n = len(nav) - 1
        if n <= 0:
            return 0.0
        initial = nav.iloc[0]
        final = nav.iloc[-1]
        if initial <= 0:
            return 0.0
        return (final / initial) ** (252 / n) - 1


# ============================================================
# 2. MaxDrawdown
# ============================================================

class MaxDrawdown(Metric):
    """最大回撤

    公式: (nav - cummax) / cummax 的最小值 (负数)
    """
    name: str = "max_drawdown"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self):
        self.params = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        nav = data["net_value"]["value"]
        cummax = nav.cummax()
        drawdown = (nav - cummax) / cummax
        return float(drawdown.min())


# ============================================================
# 3. SharpeRatio
# ============================================================

class SharpeRatio(Metric):
    """夏普比率

    公式: (mean(returns) - rf/252) / std(returns) * sqrt(252)
    """
    name: str = "sharpe_ratio"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self, risk_free_rate: float = 0.03):
        self.params = {"risk_free_rate": risk_free_rate}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        nav = data["net_value"]["value"]
        returns = _daily_returns(nav)
        if len(returns) < 2:
            return 0.0
        rf = self.params.get("risk_free_rate", 0.03)
        std = returns.std()
        if std == 0 or np.isnan(std):
            return 0.0
        return (returns.mean() - rf / 252) / std * math.sqrt(252)


# ============================================================
# 4. SortinoRatio
# ============================================================

class SortinoRatio(Metric):
    """索提诺比率

    分母仅使用下行波动率:
    (mean(returns) - rf/252) / std(returns[returns < 0]) * sqrt(252)
    """
    name: str = "sortino_ratio"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self, risk_free_rate: float = 0.03):
        self.params = {"risk_free_rate": risk_free_rate}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        nav = data["net_value"]["value"]
        returns = _daily_returns(nav)
        if len(returns) < 2:
            return 0.0
        rf = self.params.get("risk_free_rate", 0.03)
        downside = returns[returns < 0]
        if len(downside) == 0:
            return float("inf") if returns.mean() > rf / 252 else 0.0
        downside_std = downside.std()
        if downside_std == 0 or np.isnan(downside_std):
            return 0.0
        return (returns.mean() - rf / 252) / downside_std * math.sqrt(252)


# ============================================================
# 5. Volatility
# ============================================================

class Volatility(Metric):
    """年化波动率

    公式: std(returns) * sqrt(252)
    """
    name: str = "volatility"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self):
        self.params = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        nav = data["net_value"]["value"]
        returns = _daily_returns(nav)
        if len(returns) < 2:
            return 0.0
        std = returns.std()
        if np.isnan(std):
            return 0.0
        return std * math.sqrt(252)


# ============================================================
# 6. CalmarRatio
# ============================================================

class CalmarRatio(Metric):
    """卡尔玛比率

    公式: annualized_return / abs(max_drawdown)
    max_drawdown 为零时返回 0.0
    """
    name: str = "calmar_ratio"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self):
        self.params = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        nav = data["net_value"]["value"]
        n = len(nav) - 1
        if n <= 0:
            return 0.0
        initial = nav.iloc[0]
        final = nav.iloc[-1]
        if initial <= 0:
            return 0.0
        annualized = (final / initial) ** (252 / n) - 1

        cummax = nav.cummax()
        drawdown = (nav - cummax) / cummax
        max_dd = drawdown.min()

        if max_dd == 0:
            return 0.0

        return annualized / abs(max_dd)


# ============================================================
# 7. RollingSharpe
# ============================================================

class RollingSharpe(Metric):
    """滚动夏普比率

    在滚动窗口内应用夏普公式，返回 pd.Series。
    """
    name: str = "rolling_sharpe"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self, window: int = 60, risk_free_rate: float = 0.03):
        self.params = {"window": window, "risk_free_rate": risk_free_rate}

    def compute(self, data: Dict[str, pd.DataFrame]) -> pd.Series:
        nav = data["net_value"]["value"]
        returns = _daily_returns(nav)
        window = self.params.get("window", 60)
        rf = self.params.get("risk_free_rate", 0.03)

        rolling_mean = returns.rolling(window=window).mean()
        rolling_std = returns.rolling(window=window).std()
        result = (rolling_mean - rf / 252) / rolling_std * math.sqrt(252)
        return result


# ============================================================
# 8. RollingVolatility
# ============================================================

class RollingVolatility(Metric):
    """滚动波动率

    在滚动窗口内应用波动率公式，返回 pd.Series。
    """
    name: str = "rolling_volatility"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self, window: int = 20):
        self.params = {"window": window}

    def compute(self, data: Dict[str, pd.DataFrame]) -> pd.Series:
        nav = data["net_value"]["value"]
        returns = _daily_returns(nav)
        window = self.params.get("window", 20)

        rolling_std = returns.rolling(window=window).std()
        result = rolling_std * math.sqrt(252)
        return result
