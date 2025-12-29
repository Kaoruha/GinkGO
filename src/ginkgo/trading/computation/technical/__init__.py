# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Technical技术指标模块提供技术指标公共接口和导出功能支持指标计算和分析用于策略开发支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage
from ginkgo.trading.computation.technical.weighted_moving_average import WeightedMovingAverage
from ginkgo.trading.computation.technical.exponential_moving_average import ExponentialMovingAverage
from ginkgo.trading.computation.technical.average_true_range import AverageTrueRange
from ginkgo.trading.computation.technical.pinbar import PinBar
from ginkgo.trading.computation.technical.inflection_point import InflectionPoint
from ginkgo.trading.computation.technical.gap import Gap

# 新增技术指标
from ginkgo.trading.computation.technical.bollinger_bands import BollingerBands, BollingerBandsSignal
from ginkgo.trading.computation.technical.relative_strength_index import RelativeStrengthIndex, RSISignal

# Alpha158因子集成
from ginkgo.trading.computation.technical.alpha_factors import (
    KMID, KLEN, KLOW, KHIGH,
    MA, STD, BETA, ROC,
    MAX, MIN, QTLU, QTLD,
    RANK, RSV, IMAX, IMIN, IMXD
)
from ginkgo.trading.computation.technical.alpha158_factory import Alpha158Factory

# TODO MOVE to Analyzer