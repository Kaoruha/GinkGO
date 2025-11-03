"""
RandomSignalStrategy - 随机信号生成策略

用于测试和验证的简单策略：
- 基于概率随机生成买入/卖出信号
- 支持自定义概率分布和信号强度
- 可配置的目标股票代码池
- 独立于市场数据的随机决策
"""

import random
from typing import List, Dict, Any, Optional
from decimal import Decimal

from ginkgo.trading.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class RandomSignalStrategy(BaseStrategy):
    """
    随机信号生成策略

    特性：
    - 基于配置的概率随机生成交易信号
    - 支持买入/卖出/观望三种决策
    - 可配置目标股票代码池
    - 独立于价格数据，纯粹基于随机数
    - 适用于回测框架验证和压力测试
    """

    def __init__(self,
                 buy_probability: float = 0.3,
                 sell_probability: float = 0.3,
                 target_codes: Optional[List[str]] = None,
                 signal_reason_template: str = "随机信号-{direction}-{index}"):
        """
        初始化随机信号策略

        Args:
            buy_probability: 买入信号概率 (0.0-1.0)
            sell_probability: 卖出信号概率 (0.0-1.0)
            target_codes: 目标股票代码列表，默认为几个主要股票
            signal_reason_template: 信号原因模板
        """
        super().__init__()

        # 概率配置
        self.buy_probability = max(0.0, min(1.0, buy_probability))
        self.sell_probability = max(0.0, min(1.0, sell_probability))

        # 确保概率总和不超过1
        if self.buy_probability + self.sell_probability > 1.0:
            total = self.buy_probability + self.sell_probability
            self.buy_probability = self.buy_probability / total
            self.sell_probability = self.sell_probability / total

        # 目标股票代码池
        self.target_codes = target_codes or [
            "000001.SZ", "000002.SZ", "600000.SH",
            "600036.SH", "000858.SZ"
        ]

        # 信号原因模板
        self.signal_reason_template = signal_reason_template

        # 策略状态
        self.signal_count = 0
        self.last_signal_time = None
        self.signal_history: List[Dict[str, Any]] = []

        # 随机数种子（可复现测试）
        self.random_seed = None

    def set_random_seed(self, seed: int) -> None:
        """
        设置随机数种子，用于可复现的测试

        Args:
            seed: 随机数种子
        """
        self.random_seed = seed
        random.seed(seed)

    def cal(self, portfolio_info: Dict[str, Any], event: EventPriceUpdate, *args, **kwargs) -> List[Signal]:
        """
        策略主要计算逻辑

        基于随机数生成交易信号，不依赖价格数据

        Args:
            portfolio_info: Portfolio信息
            event: 价格更新事件
            *args, **kwargs: 其他参数

        Returns:
            List[Signal]: 生成的信号列表
        """
        signals = []

        # 更新策略状态
        current_time = getattr(event, 'timestamp', None) or getattr(event, 'business_timestamp', None)

        # 为每个目标股票生成信号决策
        for code in self.target_codes:
            # 生成随机决策
            decision = self._make_random_decision()

            if decision != "hold":  # 不为观望时生成信号
                signal = self._create_signal(
                    code=code,
                    direction=decision,
                    timestamp=current_time,
                    event=event
                )

                if signal:
                    signals.append(signal)
                    self._record_signal(signal, event)

        return signals

    def _make_random_decision(self) -> str:
        """
        基于概率做出随机决策

        Returns:
            str: 决策结果 ("buy", "sell", "hold")
        """
        rand_val = random.random()

        if rand_val < self.buy_probability:
            return "buy"
        elif rand_val < self.buy_probability + self.sell_probability:
            return "sell"
        else:
            return "hold"

    def _create_signal(self,
                      code: str,
                      direction: str,
                      timestamp: Any,
                      event: EventPriceUpdate) -> Optional[Signal]:
        """
        创建交易信号

        Args:
            code: 股票代码
            direction: 方向 ("buy" 或 "sell")
            timestamp: 时间戳
            event: 触发事件

        Returns:
            Signal: 创建的信号，失败时返回None
        """
        try:
            # 转换方向枚举
            if direction == "buy":
                direction_enum = DIRECTION_TYPES.LONG
            elif direction == "sell":
                direction_enum = DIRECTION_TYPES.SHORT
            else:
                return None

            # 增加信号计数
            self.signal_count += 1

            # 生成信号原因
            reason = self.signal_reason_template.format(
                direction=direction.upper(),
                index=self.signal_count
            )

            # 创建信号
            signal = Signal(
                code=code,
                direction=direction_enum,
                reason=reason,
                timestamp=timestamp
            )

            # 设置信号来源
            if hasattr(signal, 'set_source'):
                signal.set_source(SOURCE_TYPES.STRATEGY)

            return signal

        except Exception as e:
            # 记录错误但不中断策略执行
            self.log_error(f"创建信号失败: {e}")
            return None

    def _record_signal(self, signal: Signal, event: EventPriceUpdate) -> None:
        """
        记录信号历史

        Args:
            signal: 生成的信号
            event: 触发事件
        """
        record = {
            "signal_id": self.signal_count,
            "code": signal.code,
            "direction": signal.direction.name,
            "reason": signal.reason,
            "timestamp": signal.timestamp,
            "trigger_event_code": getattr(event, 'code', None),
            "trigger_event_price": getattr(event, 'close', None)
        }

        self.signal_history.append(record)
        self.last_signal_time = signal.timestamp

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息

        Returns:
            Dict[str, Any]: 策略状态信息
        """
        return {
            "strategy_name": "RandomSignalStrategy",
            "buy_probability": self.buy_probability,
            "sell_probability": self.sell_probability,
            "hold_probability": 1.0 - self.buy_probability - self.sell_probability,
            "target_codes_count": len(self.target_codes),
            "target_codes": self.target_codes.copy(),
            "total_signals_generated": self.signal_count,
            "last_signal_time": self.last_signal_time,
            "signal_history_count": len(self.signal_history),
            "random_seed": self.random_seed
        }

    def get_signal_statistics(self) -> Dict[str, Any]:
        """
        获取信号统计信息

        Returns:
            Dict[str, Any]: 信号统计数据
        """
        if not self.signal_history:
            return {
                "total_signals": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "buy_ratio": 0.0,
                "sell_ratio": 0.0,
                "most_traded_code": None,
                "signals_by_code": {}
            }

        # 统计信号类型
        buy_count = sum(1 for s in self.signal_history if s["direction"] == "LONG")
        sell_count = sum(1 for s in self.signal_history if s["direction"] == "SHORT")
        total_count = len(self.signal_history)

        # 统计每个股票的信号数量
        signals_by_code = {}
        for record in self.signal_history:
            code = record["code"]
            signals_by_code[code] = signals_by_code.get(code, 0) + 1

        # 找出交易最多的股票
        most_traded_code = max(signals_by_code.items(), key=lambda x: x[1])[0] if signals_by_code else None

        return {
            "total_signals": total_count,
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "buy_ratio": buy_count / total_count if total_count > 0 else 0.0,
            "sell_ratio": sell_count / total_count if total_count > 0 else 0.0,
            "most_traded_code": most_traded_code,
            "signals_by_code": signals_by_code
        }

    def reset_statistics(self) -> None:
        """重置统计数据"""
        self.signal_count = 0
        self.last_signal_time = None
        self.signal_history.clear()

    def update_parameters(self,
                         buy_probability: Optional[float] = None,
                         sell_probability: Optional[float] = None,
                         target_codes: Optional[List[str]] = None) -> None:
        """
        更新策略参数

        Args:
            buy_probability: 新的买入概率
            sell_probability: 新的卖出概率
            target_codes: 新的目标股票代码列表
        """
        if buy_probability is not None:
            self.buy_probability = max(0.0, min(1.0, buy_probability))

        if sell_probability is not None:
            self.sell_probability = max(0.0, min(1.0, sell_probability))

        # 重新调整概率
        if self.buy_probability + self.sell_probability > 1.0:
            total = self.buy_probability + self.sell_probability
            self.buy_probability = self.buy_probability / total
            self.sell_probability = self.sell_probability / total

        if target_codes is not None:
            self.target_codes = target_codes.copy()

    def log_error(self, message: str) -> None:
        """
        记录策略错误

        Args:
            message: 错误消息
        """
        try:
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"[RandomSignalStrategy] {message}")
        except ImportError:
            # 如果GLOG不可用，使用print
            print(f"ERROR [RandomSignalStrategy] {message}")

    def __repr__(self) -> str:
        """策略字符串表示"""
        return (f"RandomSignalStrategy(buy_prob={self.buy_probability:.2f}, "
                f"sell_prob={self.sell_probability:.2f}, "
                f"codes={len(self.target_codes)})")