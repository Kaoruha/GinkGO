"""数据源域枚举：Tick 方向/价格信息/数据源/频率/市场/复权类型。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase


class TICKDIRECTION_TYPES(EnumBase):
    VOID = -1
    NEUTRAL = 0  # 中性盘 / Unknown direction
    ACTIVEBUY = 1  # 主动买盘 / Aggressor buy
    ACTIVESELL = 2  # 主动卖盘 / Aggressor sell
    CANCEL = 3  # 撤单 / Order cancelled
    REMAIN2LIMIT = 4  # 市价剩余转限价 / Market-to-limit remainder
    MARKET2LIMIT = 5  # 市价剩余转限价 (another flag) / Market-to-limit
    FOKIOC = 6  # 全额成交或撤销 / Fill-or-Kill / Immediate-or-Cancel
    SELFOPTIMAL = 7  # 本方最优 / Best on same side
    COUNTEROPTIMAL = 8  # 对手方最优 / Best on opposite side


class PRICEINFO_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    BAR = 1
    TICK = 2


class SOURCE_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    SIM = 1
    REALTIME = 2
    SINA = 3
    BAOSTOCK = 4
    AKSHARE = 5
    YAHOO = 6
    TUSHARE = 7
    TDX = 8
    TEST = 9
    DATABASE = 10
    BACKTESTFEEDER = 11
    STRATEGY = 12
    SELECTOR = 13
    SIMMATCH = 14
    BACKTEST = 15
    LIVE = 16
    BROKERMATCHMAKING = 17
    PAPER_REPLAY = 18   # 历史数据模拟（回测区间外的样本外验证）
    PAPER_LIVE = 19     # 实盘模拟（真实市场数据）
    MANUAL = 20         # 手动录入
    OKX = 21            # OKX 交易所
    RISK = 22           # 风控组件（RiskBase.create_signal 信号源）


class FREQUENCY_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    DAY = 1
    MIN1 = 2
    MIN5 = 3
    MIN15 = 4
    MIN30 = 5
    HOUR1 = 6
    HOUR2 = 7
    HOUR4 = 8
    WEEK = 9
    MONTH = 10
    QUARTER = 11
    YEAR = 12


class MARKET_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    CHINA = 1
    NASDAQ = 2


class ADJUSTMENT_TYPES(EnumBase):
    """Price adjustment types for stock data"""

    VOID = -1
    NONE = 0  # No adjustment (original data)
    FORE = 1  # Forward adjustment (前复权) - latest price as base
    BACK = 2  # Backward adjustment (后复权) - earliest price as base


__all__ = ['TICKDIRECTION_TYPES', 'PRICEINFO_TYPES', 'SOURCE_TYPES', 'FREQUENCY_TYPES', 'MARKET_TYPES', 'ADJUSTMENT_TYPES']
