# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 分析器模块导出基类/年化收益/夏普比率/最大回撤/波动率等性能分析器支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.trading.analysis.analyzers.annualized_returns import AnnualizedReturn
from ginkgo.trading.analysis.analyzers.hold_pct import HoldPCT
from ginkgo.trading.analysis.analyzers.max_drawdown import MaxDrawdown
from ginkgo.trading.analysis.analyzers.net_value import NetValue
from ginkgo.trading.analysis.analyzers.order_count import OrderCount
from ginkgo.trading.analysis.analyzers.profit import Profit
from ginkgo.trading.analysis.analyzers.sharpe_ratio import SharpeRatio
from ginkgo.trading.analysis.analyzers.signal_count import SignalCount
from ginkgo.trading.analysis.analyzers.sortino_ratio import SortinoRatio
from ginkgo.trading.analysis.analyzers.calmar_ratio import CalmarRatio
from ginkgo.trading.analysis.analyzers.volatility import Volatility
from ginkgo.trading.analysis.analyzers.win_rate import WinRate
from ginkgo.trading.analysis.analyzers.underwater_time import UnderwaterTime
from ginkgo.trading.analysis.analyzers.var_cvar import VarCVar
from ginkgo.trading.analysis.analyzers.skew_kurtosis import SkewKurtosis
from ginkgo.trading.analysis.analyzers.consecutive_pnl import ConsecutivePnL

__all__ = [
    "BaseAnalyzer",
    "AnnualizedReturn",
    "HoldPCT",
    "MaxDrawdown",
    "NetValue",
    "OrderCount",
    "Profit",
    "SharpeRatio",
    "SignalCount",
    # 新增的高级量化指标
    "SortinoRatio",
    "CalmarRatio",
    "Volatility",
    "WinRate",
    "UnderwaterTime",
    "VarCVar",
    "SkewKurtosis",
    "ConsecutivePnL",
    # 配置
    "BASIC_ANALYZERS",
]


# ============= 基础分析器配置 =============
# BASIC_ANALYZERS: 回测时必须加载的基础分析器
# 这些分析器用于生成 BacktestTask 详情页所需的核心指标

BASIC_ANALYZERS = [
    NetValue,           # 净值曲线 - 最终资产、总盈亏
    MaxDrawdown,        # 最大回撤
    SharpeRatio,        # 夏普比率
    AnnualizedReturn,   # 年化收益
    WinRate,            # 胜率
    Profit,             # 每日利润
    Volatility,         # 波动率 - 风险基础指标
    SignalCount,        # 信号计数 - 执行统计
    OrderCount,         # 订单计数 - 执行统计
]
