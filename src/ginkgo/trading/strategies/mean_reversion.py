# Upstream: Backtest Engines (调用cal方法)
# Downstream: BaseStrategy (继承提供cal/initialize/finalize等核心能力)、StrategyDataMixin (提供数据访问能力)
# Role: MeanReversion均值回归策略基于RSI超买超卖阈值交叉


"""
Mean Reversion Strategy (均值回归策略)

策略逻辑：
- 计算收盘价的 RSI (Relative Strength Index)
- 当 RSI 从上方穿越超卖阈值时，产生买入信号 (LONG)
- 当 RSI 从下方穿越超买阈值时，产生卖出信号 (SHORT)

使用示例：
    from ginkgo.trading.strategies.mean_reversion import MeanReversion

    strategy = MeanReversion(
        name="MR_RSI",
        rsi_period=14,    # RSI计算周期
        oversold=30,      # 超卖阈值
        overbought=70     # 超买阈值
    )
"""

from typing import List, Dict, Optional

from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.interfaces.mixins.strategy_data_mixin import StrategyDataMixin
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import GLOG
from ginkgo.trading.events.price_update import EventPriceUpdate


class MeanReversion(BaseStrategy, StrategyDataMixin):
    """
    均值回归策略 (Mean Reversion Strategy)

    通过 RSI 指标的超买超卖阈值交叉来判断买卖时机：
    - RSI 下穿超卖线：买入信号（市场超卖，预期反弹）
    - RSI 上穿超买线：卖出信号（市场超买，预期回调）

    Attributes:
        rsi_period: RSI 计算周期（默认14）
        oversold: 超卖阈值（默认30）
        overbought: 超买阈值（默认70）
        frequency: 数据频率（默认'1d'日线）
    """

    def __init__(
        self,
        name: str = "MeanReversion",
        rsi_period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        frequency: str = '1d',
        **kwargs
    ):
        # 初始化父类
        super().__init__(name=name, **kwargs)

        # 显式初始化 StrategyDataMixin
        StrategyDataMixin.__init__(self)

        # 参数验证
        if rsi_period < 2:
            raise ValueError(f"rsi_period 必须 >= 2，当前值: {rsi_period}")

        if overbought <= oversold:
            raise ValueError(
                f"overbought ({overbought}) 必须 > oversold ({oversold})"
            )

        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.frequency = frequency

        # 存储每个股票的前一期 RSI，用于检测阈值穿越
        # 格式: {code: float}
        self._prev_rsi: Dict[str, Optional[float]] = {}

        GLOG.INFO(
            f"{self.name}: 初始化均值回归策略 "
            f"(RSI周期={rsi_period}, 超卖={oversold}, 超买={overbought}, 频率={frequency})"
        )

    def cal(
        self, portfolio_info: Dict, event: EventPriceUpdate, *args, **kwargs
    ) -> List[Signal]:
        """
        处理价格更新事件，检测 RSI 阈值交叉

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

        try:
            # 获取足够的历史数据计算 RSI（需要 rsi_period + 1 根 bar）
            bars = self.get_bars_cached(
                symbol=code,
                count=self.rsi_period + 1,
                frequency=self.frequency,
                use_cache=True,
            )

            if not bars or len(bars) < self.rsi_period + 1:
                return []

            # 计算 RSI
            rsi = self._calculate_rsi(bars)
            if rsi is None:
                return []

            # 获取上一次的 RSI
            prev_rsi = self._prev_rsi.get(code)

            # 首次调用，无前期数据，仅记录状态
            if prev_rsi is None:
                self._prev_rsi[code] = rsi
                return []

            # 检测阈值穿越
            signal = self._detect_crossing(
                portfolio_info=portfolio_info,
                event=event,
                code=code,
                prev_rsi=prev_rsi,
                current_rsi=rsi,
            )

            # 无论是否有信号都更新状态
            self._prev_rsi[code] = rsi

            if signal is None:
                return []

            return signal

        except Exception as e:
            GLOG.ERROR(f"{self.name}: 处理 {code} 时出错: {e}")
            return []

    def _calculate_rsi(self, bars: List) -> Optional[float]:
        """
        计算 RSI (Relative Strength Index)

        Args:
            bars: K线数据列表（至少 rsi_period + 1 根）

        Returns:
            Optional[float]: RSI 值 (0-100)，计算失败返回 None
        """
        try:
            # 提取收盘价
            closes = [bar.close for bar in bars[-(self.rsi_period + 1):]]

            # 计算价格变化
            changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

            if len(changes) < self.rsi_period:
                return None

            # 只看最近 rsi_period 个变化
            changes = changes[-self.rsi_period:]

            # 分离涨跌
            gains = [max(c, 0.0) for c in changes]
            losses = [abs(min(c, 0.0)) for c in changes]

            # 计算平均涨跌幅
            avg_gain = sum(gains) / self.rsi_period
            avg_loss = sum(losses) / self.rsi_period

            # RS 计算
            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

            return rsi

        except Exception as e:
            GLOG.ERROR(f"{self.name}: 计算 RSI 失败: {e}")
            return None

    def _detect_crossing(
        self,
        portfolio_info: Dict,
        event,
        code: str,
        prev_rsi: float,
        current_rsi: float,
    ) -> Optional[List[Signal]]:
        """
        检测 RSI 阈值穿越

        Args:
            portfolio_info: 投资组合信息
            event: 价格事件
            code: 股票代码
            prev_rsi: 前一期 RSI
            current_rsi: 当前 RSI

        Returns:
            Optional[List[Signal]]: 信号列表或 None
        """
        signal = None
        direction = None
        reason = ""

        # RSI 下穿超卖线：前一周期 >= oversold，当前 < oversold → 买入
        if prev_rsi >= self.oversold and current_rsi < self.oversold:
            direction = DIRECTION_TYPES.LONG
            reason = (
                f"均值回归买入: RSI({self.rsi_period})={current_rsi:.2f} "
                f"下穿超卖线({self.oversold})"
            )

        # RSI 上穿超买线：前一周期 <= overbought，当前 > overbought → 卖出
        elif prev_rsi <= self.overbought and current_rsi > self.overbought:
            direction = DIRECTION_TYPES.SHORT
            reason = (
                f"均值回归卖出: RSI({self.rsi_period})={current_rsi:.2f} "
                f"上穿超买线({self.overbought})"
            )

        if direction is not None:
            business_timestamp = portfolio_info.get("now")

            signal = Signal(
                portfolio_id=portfolio_info.get("uuid"),
                engine_id=self.engine_id,
                run_id=self.run_id,
                business_timestamp=business_timestamp,
                code=code,
                direction=direction,
                reason=reason,
            )

            GLOG.backtest.signal(
                symbol=code,
                direction=direction.value if hasattr(direction, 'value') else str(direction),
                signal_reason=signal.reason,
                strategy_id=self.uuid,
                portfolio_id=portfolio_info.get("uuid"),
                engine_id=self.engine_id,
                run_id=self.run_id,
                business_timestamp=business_timestamp,
            )

        return [signal] if signal else None

    def reset_state(self) -> None:
        """
        重置策略状态

        在回测或实盘切换策略时调用，清除历史状态
        """
        self._prev_rsi.clear()
        # 直接清理内部缓存，避免调用 clear_data_cache() 中 GLOG.debug() 的问题
        self._data_cache.clear()
        self._cache_timestamps.clear()
        GLOG.INFO(f"{self.name}: 策略状态已重置")
