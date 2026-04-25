# Upstream: Backtest Engines (调用cal方法)
# Downstream: BaseStrategy (继承提供cal/initialize/finalize等核心能力)、StrategyDataMixin (提供数据访问能力)
# Role: Momentum动量因子策略继承BaseStrategy基于截面动量排名选股



"""
Momentum Strategy (动量因子策略)

策略逻辑：
- 计算所有关注股票在回溯期内的收益率（动量）
- 按动量从高到低排名，买入排名前 N 的股票
- 每隔 rebalance_days 天重新平衡
- 卖出跌出前 N 的持仓，买入新进入前 N 的股票

使用示例：
    from ginkgo.trading.strategies.momentum import Momentum

    strategy = Momentum(
        name="Momentum_20_5",
        lookback_period=20,  # 回溯期
        top_n=5,             # 选取前5名
        rebalance_days=5,    # 每5天再平衡
    )
"""

from typing import List, Dict, Set, Optional
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

    通过截面动量排名选取表现最佳的股票：
    - 计算回溯期内收益率作为动量指标
    - 选取动量排名前 top_n 的股票
    - 定期再平衡，调出表现变差的股票

    Attributes:
        lookback_period: 回溯期天数（默认20）
        top_n: 选取排名前N只股票（默认5）
        rebalance_days: 再平衡间隔天数（默认5）
        frequency: 数据频率（默认'1d'日线）

    Example:
        >>> strategy = Momentum(
        ...     name="Momentum20",
        ...     lookback_period=20,
        ...     top_n=5,
        ...     rebalance_days=5
        ... )
    """

    def __init__(
        self,
        name: str = "Momentum",
        lookback_period: int = 20,
        top_n: int = 5,
        rebalance_days: int = 5,
        frequency: str = '1d',
        **kwargs
    ):
        """
        初始化动量因子策略

        Args:
            name: 策略名称
            lookback_period: 回溯期天数（计算收益率的时间窗口）
            top_n: 选取动量排名前N只股票
            rebalance_days: 再平衡间隔天数
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

        if top_n <= 0:
            raise ValueError(f"top_n ({top_n}) 必须 > 0")

        if rebalance_days < 1:
            raise ValueError(f"rebalance_days ({rebalance_days}) 必须 >= 1")

        self.lookback_period = lookback_period
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self.frequency = frequency

        # 再平衡状态
        self._last_rebalance: Optional[datetime] = None
        self._current_holdings: Set[str] = set()

        GLOG.INFO(f"{self.name}: 初始化动量因子策略 "
                  f"(回溯期={lookback_period}, Top{top_n}, 再平衡={rebalance_days}天, 频率={frequency})")

    def cal(self, portfolio_info: Dict, event: EventPriceUpdate, *args, **kwargs) -> List[Signal]:
        """
        处理价格更新事件，执行动量排名和再平衡

        Args:
            portfolio_info: 组合信息，包含 interested_codes 和 now
            event: 价格更新事件

        Returns:
            List[Signal]: 信号列表（买入新进入 top_n 的，卖出跌出的）
        """
        # 只处理价格更新事件
        if not isinstance(event, EventPriceUpdate):
            return []

        current_time = portfolio_info.get("now")
        if not isinstance(current_time, datetime):
            return []

        # 获取 engine_id 和 task_id（优先从上下文，后备从 portfolio_info）
        engine_id = self.engine_id or portfolio_info.get("engine_id", "")
        task_id = self.task_id or portfolio_info.get("task_id", "")
        portfolio_id = portfolio_info.get("uuid", "")

        # 检查是否到了再平衡时间
        if self._last_rebalance is not None:
            days_since_rebalance = (current_time - self._last_rebalance).days
            if days_since_rebalance < self.rebalance_days:
                return []

        # 获取关注股票列表
        interested_codes = portfolio_info.get("interested_codes", [])
        if not interested_codes:
            return []

        # 计算每只股票的动量
        momentum_scores: List[tuple] = []
        for code in interested_codes:
            try:
                bars = self.get_bars_cached(
                    symbol=code,
                    count=self.lookback_period + 1,
                    frequency=self.frequency,
                    use_cache=True,
                )

                if not bars or len(bars) < self.lookback_period:
                    continue

                # 提取收盘价序列
                closes = []
                for bar in bars:
                    if hasattr(bar, 'close'):
                        closes.append(float(bar.close))

                if len(closes) < 2:
                    continue

                # 动量 = (末期收盘价 - 期初收盘价) / 期初收盘价
                first_close = closes[0]
                last_close = closes[-1]

                if first_close <= 0:
                    continue

                momentum = (last_close - first_close) / first_close
                momentum_scores.append((code, momentum))

            except Exception as e:
                GLOG.ERROR(f"{self.name}: 计算动量失败 {code}: {e}")
                continue

        if not momentum_scores:
            return []

        # 按动量降序排名
        momentum_scores.sort(key=lambda x: x[1], reverse=True)
        top_codes = set(code for code, _ in momentum_scores[:self.top_n])

        # 生成信号
        signals = []
        new_holdings: Set[str] = set()

        # 买入新进入 top_n 的股票
        for code in top_codes:
            if code not in self._current_holdings:
                signal = self.create_signal(
                    code=code,
                    direction=DIRECTION_TYPES.LONG,
                    reason=f"动量入选: 排名前{self.top_n}",
                    business_timestamp=current_time,
                )
                signals.append(signal)
                new_holdings.add(code)

                GLOG.backtest.signal(
                    symbol=code,
                    direction=DIRECTION_TYPES.LONG.value,
                    signal_reason=signal.reason,
                    strategy_id=self.uuid,
                    portfolio_id=portfolio_id,
                    engine_id=engine_id,
                    task_id=task_id,
                    business_timestamp=current_time,
                )

        # 卖出跌出 top_n 的持仓
        for code in self._current_holdings:
            if code not in top_codes:
                signal = self.create_signal(
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"动量调出: 跌出前{self.top_n}",
                    business_timestamp=current_time,
                )
                signals.append(signal)

                GLOG.backtest.signal(
                    symbol=code,
                    direction=DIRECTION_TYPES.SHORT.value,
                    signal_reason=signal.reason,
                    strategy_id=self.uuid,
                    portfolio_id=portfolio_id,
                    engine_id=engine_id,
                    task_id=task_id,
                    business_timestamp=current_time,
                )
            else:
                new_holdings.add(code)

        # 更新状态
        self._last_rebalance = current_time
        self._current_holdings = new_holdings

        return signals

    def reset_state(self) -> None:
        """
        重置策略状态

        在回测或实盘切换策略时调用，清除历史状态
        """
        self._last_rebalance = None
        self._current_holdings = set()
        # 直接清理缓存，避免调用 clear_data_cache 中的 GLOG.debug
        self._data_cache.clear()
        self._cache_timestamps.clear()
        GLOG.INFO(f"{self.name}: 策略状态已重置")
