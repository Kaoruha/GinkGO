# Upstream: BacktestEvaluator, AnalysisEngine, Portfolio
# Downstream: BaseAnalyzer, AnnualizedReturn, MaxDrawdown, SharpeRatio, Volatility, WinRate, Profit
# Role: 分析器包导出所有性能分析器

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
]

# 分析器注册名 -> 一句话描述(口径取各类 docstring)。
# list_analyzer_groups 组装 BacktestAnalyzerGroup.description 时查此表;
# API /backtests/{uuid}/analyzers 原样带出,前端展示层用其解释指标含义。
ANALYZER_DESCRIPTIONS = {
    "annualized_return": "年化收益率(按日收益折算的复合年化回报)",
    "avg_holding_period": "平均持仓周期(每笔持仓的平均持有天数)",
    "avg_win_loss_ratio": "平均盈亏比(平均每笔盈利 / 平均每笔亏损)",
    "calmar_ratio": "卡尔马比率(年化收益 / 最大回撤,回撤调整后收益)",
    "consecutive_pnl": "连续盈亏(最长连续盈利 / 亏损区间统计)",
    "hold_pct": "持仓比例(持仓市值占总资产的比例,按日记录)",
    "max_consecutive_losses": "最大连续亏损次数(连亏笔数的最大值)",
    "max_drawdown": "最大回撤(历史最高净值至谷底的比例,负值表示损失)",
    "net_value": "组合净值(初始资金归一化的每日总值曲线)",
    "order_count": "累计订单数(取最新值即为订单总数)",
    "profit": "累计利润(逐日盈亏累加,单位元)",
    "profit_factor": "利润因子(总盈利 / 总亏损,>1 为正期望)",
    "sharpe_ratio": "夏普比率(日收益率的风险调整后收益)",
    "signal_count": "累计信号数(取最新值即为信号总数)",
    "skew_kurtosis": "收益分布偏度/峰度(分布偏斜与尖峭程度)",
    "sortino_ratio": "索提诺比率(仅以下行波动计风险的风险调整收益)",
    "trade_win_rate": "交易维度胜率(按平仓交易笔数统计盈利占比)",
    "underwater_time": "水下时间(净值持续低于历史高点的时长)",
    "var_cvar": "VaR/CVaR(风险价值与条件风险价值,尾部损失度量)",
    "volatility": "波动率(日收益率的标准差)",
    "win_rate": "日胜率(按交易日统计当日盈利占比)",
}

