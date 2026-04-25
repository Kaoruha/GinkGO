# Upstream: Backtest Engines (调用cal方法)
# Downstream: BaseStrategy (继承提供cal/initialize/finalize等核心能力)、StrategyDataMixin (提供数据访问能力)
# Role: TrendFollow趋势跟踪策略继承BaseStrategy基于三均线排列判断趋势方向


"""
Trend Follow Strategy (趋势跟踪策略)

策略逻辑：
- 计算短期、中期、长期三条移动平均线
- 看多排列（短期 > 中期 > 长期）产生买入信号
- 看空排列（短期 < 中期 < 长期）产生卖出信号
- ATR 用于动态止损参考（MVP阶段仅计算存储，不用于信号生成）

使用示例：
    from ginkgo.trading.strategies.trend_reverse import TrendFollow

    strategy = TrendFollow(
        name="TrendFollow_5_20_60",
        short_period=5,
        medium_period=20,
        long_period=60
    )
"""

from typing import List, Dict, Optional

from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.interfaces.mixins.strategy_data_mixin import StrategyDataMixin
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import GLOG
from ginkgo.trading.events.price_update import EventPriceUpdate


class TrendFollow(BaseStrategy, StrategyDataMixin):
    """
    趋势跟踪策略 (Trend Follow Strategy)

    通过短期、中期、长期三条移动平均线的排列来判断趋势方向：
    - 多头排列（短期 > 中期 > 长期）：买入信号
    - 空头排列（短期 < 中期 < 长期）：卖出信号

    Attributes:
        short_period: 短期均线周期（默认5）
        medium_period: 中期均线周期（默认20）
        long_period: 长期均线周期（默认60）
        atr_period: ATR计算周期（默认14）
        atr_multiplier: ATR乘数（默认2.0）
        frequency: 数据频率（默认'1d'日线）

    Example:
        >>> strategy = TrendFollow(
        ...     name="TrendFollow",
        ...     short_period=5,
        ...     medium_period=20,
        ...     long_period=60
        ... )
    """

    def __init__(
        self,
        name: str = "TrendFollow",
        short_period: int = 5,
        medium_period: int = 20,
        long_period: int = 60,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        frequency: str = '1d',
        **kwargs
    ):
        """
        初始化趋势跟踪策略

        Args:
            name: 策略名称
            short_period: 短期均线周期
            medium_period: 中期均线周期
            long_period: 长期均线周期
            atr_period: ATR计算周期
            atr_multiplier: ATR乘数（用于止损参考）
            frequency: 数据频率 ('1d'=日线, '1h'=小时, '1m'=分钟)
            **kwargs: 其他参数传递给父类
        """
        # 初始化父类
        super().__init__(name=name, **kwargs)

        # 显式初始化 StrategyDataMixin
        StrategyDataMixin.__init__(self)

        # 参数验证
        if short_period >= medium_period:
            raise ValueError(
                f"short_period ({short_period}) 必须小于 medium_period ({medium_period})"
            )
        if medium_period >= long_period:
            raise ValueError(
                f"medium_period ({medium_period}) 必须小于 long_period ({long_period})"
            )
        if short_period < 2 or medium_period < 2 or long_period < 2:
            raise ValueError("均线周期必须 >= 2")

        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.frequency = frequency

        # 存储每个股票的前期排列状态，用于检测排列变化
        # 格式: {code: bool}  True=看多排列, False=看空/中性排列
        self._prev_alignment: Dict[str, Optional[bool]] = {}

        GLOG.INFO(f"{self.name}: 初始化趋势跟踪策略 "
                  f"(短期={short_period}, 中期={medium_period}, 长期={long_period}, "
                  f"ATR周期={atr_period}, ATR乘数={atr_multiplier}, 频率={frequency})")

    def cal(self, portfolio_info: Dict, event, *args, **kwargs) -> List[Signal]:
        """
        处理价格更新事件，检测均线排列变化

        Args:
            portfolio_info: 组合信息
            event: 价格更新事件

        Returns:
            List[Signal]: 信号列表（可能有0或1个信号）
        """
        # 只处理价格更新事件
        if not isinstance(event, EventPriceUpdate):
            return []

        code = event.code

        # 获取足够的历史数据来计算三条均线
        try:
            bars = self.get_bars_cached(
                symbol=code,
                count=self.long_period + 1,
                frequency=self.frequency,
                use_cache=True
            )

            if not bars or len(bars) < self.long_period:
                return []

            # 提取收盘价、最高价、最低价
            closes = []
            highs = []
            lows = []
            for bar in bars:
                if hasattr(bar, 'close'):
                    closes.append(bar.close)
                    highs.append(bar.high if hasattr(bar, 'high') else bar.close)
                    lows.append(bar.low if hasattr(bar, 'low') else bar.close)
                else:
                    closes.append(float(bar))
                    highs.append(float(bar))
                    lows.append(float(bar))

            if len(closes) < self.long_period:
                return []

            # 计算移动平均线
            short_ma = sum(closes[-self.short_period:]) / self.short_period
            medium_ma = sum(closes[-self.medium_period:]) / self.medium_period
            long_ma = sum(closes[-self.long_period:]) / self.long_period

            # 计算ATR（存储但MVP阶段不用于信号生成）
            atr = self._calculate_atr(highs, lows, closes)

            # 判断当前排列状态
            is_bullish = short_ma > medium_ma > long_ma
            is_bearish = short_ma < medium_ma < long_ma

            # 获取前一次的排列状态
            prev_bullish = self._prev_alignment.get(code, None)

            signals = []

            # 只在排列变化时生成信号
            # 从非看多 变为 看多 → 买入
            if prev_bullish is not None and not prev_bullish and is_bullish:
                direction = DIRECTION_TYPES.LONG
                reason = (
                    f"多头排列: MA{self.short_period}({short_ma:.2f}) > "
                    f"MA{self.medium_period}({medium_ma:.2f}) > "
                    f"MA{self.long_period}({long_ma:.2f})"
                )
                if atr is not None:
                    reason += f", ATR={atr:.2f}"

                signal = self.create_signal(
                    code=code,
                    direction=direction,
                    reason=reason,
                    business_timestamp=portfolio_info.get("now"),
                )
                signals.append(signal)

                GLOG.backtest.signal(
                    symbol=code,
                    direction=direction.value if hasattr(direction, 'value') else str(direction),
                    signal_reason=signal.reason,
                    strategy_id=self.uuid,
                    portfolio_id=portfolio_info.get("uuid"),
                    engine_id=self.engine_id,
                    task_id=self.task_id,
                    business_timestamp=portfolio_info.get("now"),
                )

            # 从看多 变为 非看多（看空） → 卖出
            elif prev_bullish is not None and prev_bullish and is_bearish:
                direction = DIRECTION_TYPES.SHORT
                reason = (
                    f"空头排列: MA{self.short_period}({short_ma:.2f}) < "
                    f"MA{self.medium_period}({medium_ma:.2f}) < "
                    f"MA{self.long_period}({long_ma:.2f})"
                )
                if atr is not None:
                    reason += f", ATR={atr:.2f}"

                signal = self.create_signal(
                    code=code,
                    direction=direction,
                    reason=reason,
                    business_timestamp=portfolio_info.get("now"),
                )
                signals.append(signal)

                GLOG.backtest.signal(
                    symbol=code,
                    direction=direction.value if hasattr(direction, 'value') else str(direction),
                    signal_reason=signal.reason,
                    strategy_id=self.uuid,
                    portfolio_id=portfolio_info.get("uuid"),
                    engine_id=self.engine_id,
                    task_id=self.task_id,
                    business_timestamp=portfolio_info.get("now"),
                )

            # 更新状态：True=看多排列, False=其他
            self._prev_alignment[code] = is_bullish

            return signals

        except Exception as e:
            GLOG.ERROR(f"{self.name}: 处理 {code} 时出错: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Optional[float]:
        """
        计算平均真实波幅（ATR）

        Args:
            highs: 最高价列表
            lows: 最低价列表
            closes: 收盘价列表

        Returns:
            Optional[float]: ATR值或None（数据不足时）
        """
        if len(closes) < self.atr_period + 1:
            return None

        try:
            true_ranges = []
            for i in range(1, len(closes)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1])
                )
                true_ranges.append(tr)

            # 使用最近 atr_period 个真实波幅
            recent_tr = true_ranges[-self.atr_period:]
            atr = sum(recent_tr) / len(recent_tr)
            return atr

        except Exception:
            return None

    def reset_state(self) -> None:
        """
        重置策略状态

        在回测或实盘切换策略时调用，清除历史状态
        """
        self._prev_alignment.clear()
        GLOG.INFO(f"{self.name}: 策略状态已重置")
