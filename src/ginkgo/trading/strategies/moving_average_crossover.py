# Upstream: Backtest Engines (调用cal方法)
# Downstream: BaseStrategy (继承提供cal/initialize/finalize等核心能力)、StrategyDataMixin (提供数据访问能力)
# Role: MovingAverageCrossover均线交叉策略继承BaseStrategy基于均线金叉死叉






"""
Moving Average Crossover Strategy (金叉死叉策略)

策略逻辑：
- 当短期均线上穿长期均线时（金叉），产生买入信号
- 当短期均线下穿长期均线时（死叉），产生卖出信号

使用示例：
    from ginkgo.trading.strategies.moving_average_crossover import MovingAverageCrossover

    strategy = MovingAverageCrossover(
        name="MA_Crossover_20_60",
        short_period=20,  # 短期均线周期
        long_period=60    # 长期均线周期
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


class MovingAverageCrossover(BaseStrategy, StrategyDataMixin):
    """
    金叉死叉策略 (Moving Average Crossover Strategy)

    通过短期和长期移动平均线的交叉来判断买卖时机：
    - 金叉（短期上穿长期）：买入信号
    - 死叉（短期下穿长期）：卖出信号

    Attributes:
        short_period: 短期均线周期（默认20）
        long_period: 长期均线周期（默认60）
        frequency: 数据频率（默认'1d'日线）

    Example:
        >>> strategy = MovingAverageCrossover(
        ...     name="MA_Cross",
        ...     short_period=20,
        ...     long_period=60
        ... )
    """

    def __init__(
        self,
        name: str = "MovingAverageCrossover",
        short_period: int = 20,
        long_period: int = 60,
        frequency: str = '1d',
        **kwargs
    ):
        """
        初始化金叉死叉策略

        Args:
            name: 策略名称
            short_period: 短期均线周期
            long_period: 长期均线周期
            frequency: 数据频率 ('1d'=日线, '1h'=小时, '1m'=分钟)
            **kwargs: 其他参数传递给父类
        """
        # 初始化父类
        super().__init__(name=name, **kwargs)

        # 显式初始化 StrategyDataMixin
        StrategyDataMixin.__init__(self)

        # 参数验证
        if short_period >= long_period:
            raise ValueError(f"short_period ({short_period}) 必须小于 long_period ({long_period})")

        if short_period < 2 or long_period < 2:
            raise ValueError("均线周期必须 >= 2")

        self.short_period = short_period
        self.long_period = long_period
        self.frequency = frequency

        # 存储每个股票的前期均线状态，用于检测交叉
        # 格式: {code: {'prev_short': float, 'prev_long': float}}
        self._ma_states: Dict[str, Dict[str, Optional[float]]] = {}

        GLOG.INFO(f"{self.name}: 初始化金叉死叉策略 "
                  f"(短期={short_period}, 长期={long_period}, 频率={frequency})")

    def cal(self, portfolio_info: Dict, event: EventPriceUpdate, *args, **kwargs) -> List[Signal]:
        """
        处理价格更新事件，检测金叉死叉

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

        # 🔍 调试输出
        print(f"[MA_STRATEGY] {id(self)} 收到 {code} 价格事件 @ {event.timestamp}, 状态数量: {len(self._ma_states)}")

        # 获取足够的历史数据来计算两条均线
        # 需要至少 long_period 条数据
        try:
            bars = self.get_bars_cached(
                symbol=code,
                count=self.long_period + 1,  # 多获取1条用于计算前期状态
                frequency=self.frequency,
                use_cache=True
            )

            print(f"[MA_STRATEGY] {code} 获取到 {len(bars)} 条K线数据")

            if not bars or len(bars) < self.long_period:
                print(f"[MA_STRATEGY] {code} 数据不足，需要至少 {self.long_period} 条")
                return []

            # 计算移动平均线
            ma_values = self._calculate_moving_averages(bars)

            if ma_values is None:
                return []

            current_short_ma, current_long_ma = ma_values

            # 🔍 调试输出
            print(f"[MA_STRATEGY] {code} MA{self.short_period}={current_short_ma:.2f}, MA{self.long_period}={current_long_ma:.2f}")

            # 获取上一次的均线状态
            prev_state = self._ma_states.get(code, {'prev_short': None, 'prev_long': None})
            prev_short_ma = prev_state['prev_short']
            prev_long_ma = prev_state['prev_long']

            print(f"[MA_STRATEGY] {code} 前期: MA{self.short_period}={prev_short_ma}, MA{self.long_period}={prev_long_ma}")

            # 检测交叉
            signal = self._detect_crossover(
                portfolio_info=portfolio_info,
                event=event,
                code=code,
                prev_short=prev_short_ma,
                prev_long=prev_long_ma,
                current_short=current_short_ma,
                current_long=current_long_ma
            )

            # 更新状态（无论是否有信号都要更新）
            self._ma_states[code] = {
                'prev_short': current_short_ma,
                'prev_long': current_long_ma
            }
            print(f"[MA_STRATEGY] {code} 状态已更新: MA{self.short_period}={current_short_ma:.2f}, MA{self.long_period}={current_long_ma:.2f}")

            # 如果是首次运行（没有信号），返回空列表
            if signal is None:
                return []

            return signal if signal else []

        except Exception as e:
            GLOG.ERROR(f"{self.name}: 处理 {code} 时出错: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _calculate_moving_averages(self, bars: List) -> Optional[tuple]:
        """
        计算短期和长期移动平均线

        Args:
            bars: K线数据列表

        Returns:
            Optional[tuple]: (短期均线值, 长期均线值) 或 None
        """
        try:
            # 提取收盘价
            closes = []
            for bar in bars:
                if hasattr(bar, 'close'):
                    closes.append(bar.close)
                else:
                    # 兼容不同数据格式
                    closes.append(float(bar))

            if len(closes) < self.long_period:
                return None

            # 计算均线（使用最近的数据）
            # closes[-1] 是最新的价格
            short_ma = sum(closes[-self.short_period:]) / self.short_period
            long_ma = sum(closes[-self.long_period:]) / self.long_period

            return short_ma, long_ma

        except Exception as e:
            GLOG.ERROR(f"{self.name}: 计算均线失败: {e}")
            return None

    def _detect_crossover(
        self,
        portfolio_info: Dict,
        event,
        code: str,
        prev_short: Optional[float],
        prev_long: Optional[float],
        current_short: float,
        current_long: float
    ) -> Optional[List[Signal]]:
        """
        检测金叉和死叉

        Args:
            portfolio_info: 投资组合信息
            event: 价格事件
            code: 股票代码
            prev_short: 前一期短期均线
            prev_long: 前一期长期均线
            current_short: 当前短期均线
            current_long: 当前长期均线

        Returns:
            Optional[List[Signal]]: 信号列表或None
        """
        # 第一次运行，没有前期数据
        if prev_short is None or prev_long is None:
            print(f"[MA_STRATEGY] {code} 首次运行，无前期数据")
            return None

        signal = None
        direction = None
        reason = ""

        # 检测金叉：短期均线上穿长期均线
        # 前一期: short <= long
        # 当前: short > long
        if prev_short <= prev_long and current_short > current_long:
            direction = DIRECTION_TYPES.LONG
            reason = (
                f"金叉: MA{self.short_period}({current_short:.2f}) "
                f"上穿 MA{self.long_period}({current_long:.2f})"
            )

        # 检测死叉：短期均线下穿长期均线
        # 前一期: short >= long
        # 当前: short < long
        elif prev_short >= prev_long and current_short < current_long:
            direction = DIRECTION_TYPES.SHORT
            reason = (
                f"死叉: MA{self.short_period}({current_short:.2f}) "
                f"下穿 MA{self.long_period}({current_long:.2f})"
            )

        # 如果检测到交叉，生成信号
        if direction is not None:
            # 获取当前价格
            current_price = event.transaction_price if hasattr(event, 'transaction_price') else None

            # 使用 portfolio_info.get("now") 获取时间，与 RandomSignalStrategy 保持一致
            # 使用 business_timestamp 参数，避免数据库验证错误
            business_timestamp = portfolio_info.get("now")

            signal = self.create_signal(
                code=code,
                direction=direction,
                reason=reason,
                business_timestamp=business_timestamp,
            )

            # 如果有当前价格信息，添加到 reason 中
            if current_price is not None:
                signal.reason = f"{reason}, 当前价格: {current_price:.2f}"

            print(f"[MA_STRATEGY] {code} {signal.reason}")

            # 记录信号事件到ClickHouse（使用快捷访问）
            GLOG.backtest.signal(
                symbol=code,
                direction=direction.value if hasattr(direction, 'value') else str(direction),
                signal_reason=signal.reason,
                strategy_id=self.uuid,
                portfolio_id=portfolio_info.get("uuid"),
                engine_id=self.engine_id,
                task_id=self.task_id,
                business_timestamp=business_timestamp,
            )

        return [signal] if signal else None

    def reset_state(self) -> None:
        """
        重置策略状态

        在回测或实盘切换策略时调用，清除历史状态
        """
        super().reset_state()
        self._ma_states.clear()
        self.clear_data_cache()
        GLOG.INFO(f"{self.name}: 策略状态已重置")
