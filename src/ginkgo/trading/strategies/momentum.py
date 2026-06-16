# Upstream: Backtest Engines (调用cal方法)
# Downstream: BaseStrategy (继承提供cal/initialize/finalize等核心能力)、StrategyDataMixin (提供数据访问能力)
# Role: Momentum动量因子策略 — 对单只股票计算动量，根据阈值生成方向信号



"""
Momentum Strategy (动量因子策略)

策略逻辑：
- 计算当前股票在回溯期内的收益率（动量）
- 动量超过正阈值时生成买入信号
- 动量低于负阈值且持仓时生成卖出信号

使用示例：
    from ginkgo.trading.strategies.momentum import Momentum

    strategy = Momentum(
        name="Momentum_20",
        lookback_period=20,
        momentum_threshold=0.02,
    )
"""

from typing import List, Dict, Optional
from datetime import datetime

from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.interfaces.mixins.strategy_data_mixin import StrategyDataMixin
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import GLOG
from ginkgo.trading.events.price_update import EventPriceUpdate


class Momentum(BaseStrategy, StrategyDataMixin):
    """
    动量因子策略 (Momentum Strategy)

    根据单只股票的动量指标生成交易信号：
    - 计算回溯期内收益率作为动量指标
    - 动量超过正阈值时生成买入信号（无持仓）
    - 动量低于负阈值时生成卖出信号（有持仓）

    Attributes:
        lookback_period: 回溯期天数（默认20）
        momentum_threshold: 动量信号触发阈值（默认0.02，即2%）
        frequency: 数据频率（默认'1d'日线）

    Example:
        >>> strategy = Momentum(
        ...     name="Momentum20",
        ...     lookback_period=20,
        ...     momentum_threshold=0.02,
        ... )
    """

    def __init__(
        self,
        name: str = "Momentum",
        lookback_period: int = 20,
        momentum_threshold: float = 0.02,
        frequency: str = '1d',
        **kwargs
    ):
        """
        初始化动量因子策略

        Args:
            name: 策略名称
            lookback_period: 回溯期天数（计算收益率的时间窗口）
            momentum_threshold: 动量信号触发阈值
            frequency: 数据频率 ('1d'=日线, '1h'=小时, '1m'=分钟)
            **kwargs: 其他参数传递给父类
        """
        # 初始化父类
        super().__init__(name=name, **kwargs)

        # 显式初始化 StrategyDataMixin
        StrategyDataMixin.__init__(self)

        # 参数验证
        if lookback_period < 2:
            raise ValueError(f"lookback_period ({lookback_period}) 必须 >= 2")

        self.lookback_period = lookback_period
        self.momentum_threshold = momentum_threshold
        self.frequency = frequency

        GLOG.INFO(f"{self.name}: 初始化动量因子策略 "
                  f"(回溯期={lookback_period}, 阈值={momentum_threshold}, 频率={frequency})")

    def cal(self, portfolio_info: Dict, event: EventPriceUpdate, *args, **kwargs) -> List[Signal]:
        """
        处理价格更新事件，计算动量并生成信号

        Args:
            portfolio_info: 组合信息
            event: 价格更新事件

        Returns:
            List[Signal]: 信号列表
        """
        # 只处理价格更新事件
        if not isinstance(event, EventPriceUpdate):
            return []

        current_time = portfolio_info.get("now")
        if not isinstance(current_time, datetime):
            return []

        code = event.code
        has_position = code in portfolio_info.get("positions", {})

        # 获取K线数据
        try:
            bars = self.get_bars_cached(
                symbol=code,
                count=self.lookback_period + 1,
                frequency=self.frequency,
                use_cache=True,
            )

            if not bars or len(bars) < self.lookback_period:
                return []

            # 提取收盘价序列
            closes = []
            for bar in bars:
                if hasattr(bar, 'close'):
                    closes.append(float(bar.close))

            if len(closes) < 2:
                return []

            # 动量 = (末期收盘价 - 期初收盘价) / 期初收盘价
            first_close = closes[0]
            last_close = closes[-1]

            if first_close <= 0:
                return []

            momentum = (last_close - first_close) / first_close

        except Exception as e:
            GLOG.ERROR(f"{self.name}: 计算动量失败 {code}: {e}")
            return []

        # 生成信号
        signals = []

        if momentum > self.momentum_threshold and not has_position:
            signal = self.create_signal(
                code=code,
                direction=DIRECTION_TYPES.LONG,
                reason=f"动量买入: {momentum:.2%} > {self.momentum_threshold:.2%}",
                business_timestamp=current_time,
            )
            signals.append(signal)

        elif momentum < -self.momentum_threshold and has_position:
            signal = self.create_signal(
                code=code,
                direction=DIRECTION_TYPES.SHORT,
                reason=f"动量卖出: {momentum:.2%} < -{self.momentum_threshold:.2%}",
                business_timestamp=current_time,
            )
            signals.append(signal)

        return signals

    def reset_state(self) -> None:
        """
        重置策略状态

        在回测或实盘切换策略时调用，清除历史状态
        """
        # 直接清理缓存，避免调用 clear_data_cache 中的 GLOG.debug
        self._data_cache.clear()
        self._cache_timestamps.clear()
        GLOG.INFO(f"{self.name}: 策略状态已重置")
