"""
RandomSignalStrategy - 随机信号生成策略

用于测试和验证的简单策略：
- 基于概率随机生成买入/卖出信号
- 支持自定义概率分布和信号强度
- 响应从portfolio传递的价格事件，不再维护自己的标的目录
- 只对portfolio关注的股票（通过selector配置）生成信号
- 独立于价格数据的随机决策
"""

import random
import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class RandomSignalStrategy(BaseStrategy):
    """
    随机信号生成策略

    特性：
    - 基于配置的概率随机生成交易信号
    - 支持买入/卖出/观望三种决策
    - 响应从portfolio传递的价格事件，不再维护自己的标的目录
    - 只对portfolio关注的股票（通过selector配置）生成信号
    - 独立于价格数据，纯粹基于随机数
    - 适用于回测框架验证和压力测试
    """

    def __init__(self,
                 name: str = "RandomSignalStrategy",
                 buy_probability: float = 0.3,
                 sell_probability: float = 0.3,
                 signal_reason_template: str = "随机信号-{direction}-{index}",
                 max_signals: int = -1,
                 *args, **kwargs):
        """
        初始化随机信号策略

        Args:
            name: 策略名称
            buy_probability: 买入信号概率 (0.0-1.0)
            sell_probability: 卖出信号概率 (0.0-1.0)
            signal_reason_template: 信号原因模板
            max_signals: 最大信号数量限制，-1表示无限
        """
        super().__init__(name=name, *args, **kwargs)

        # 参数类型转换处理 - 处理从数据库传来的字符串参数
        buy_probability = self._convert_to_float(buy_probability, 0.3)
        sell_probability = self._convert_to_float(sell_probability, 0.3)
        max_signals = self._convert_to_int(max_signals, -1)

        # 概率配置
        self.buy_probability = max(0.0, min(1.0, buy_probability))
        self.sell_probability = max(0.0, min(1.0, sell_probability))

        # 确保概率总和不超过1
        if self.buy_probability + self.sell_probability > 1.0:
            total = self.buy_probability + self.sell_probability
            self.buy_probability = self.buy_probability / total
            self.sell_probability = self.sell_probability / total

        # 信号原因模板
        self.signal_reason_template = signal_reason_template

        # 最大信号数量限制
        self.max_signals = max_signals

        # 随机数种子（可复现测试）
        self.random_seed = None

        # 策略状态
        self.signal_count = 0
        self.last_signal_time = None
        self.signal_history: List[Dict[str, Any]] = []

        # 调试计数器
        self.call_count = 0

        # 关注的股票代码列表（用于兼容性）
        self.target_codes = []

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

        基于从portfolio传递的价格事件生成随机交易信号，不再维护自己的标的目录

        Args:
            portfolio_info: Portfolio信息
            event: 价格更新事件（包含股票代码和价格信息）
            *args, **kwargs: 其他参数

        Returns:
            List[Signal]: 生成的信号列表
        """
        # 检查信号数量限制 - 关键业务逻辑
        if self.max_signals >= 0 and self.signal_count >= self.max_signals:
            return []

        signals = []

        # 获取事件中的股票代码
        event_code = getattr(event, 'code', None)
        if not event_code:
            return signals

        # 使用TimeProvider获取当前业务时间
        time_provider = self.get_time_provider()
        try:
            current_time = time_provider.now()
        except Exception:
            # 使用事件时间作为回退
            current_time = getattr(event, 'business_timestamp', None) or getattr(event, 'timestamp', None)

        # 为当前事件的股票生成随机决策
        decision = self._make_random_decision()

        if decision != "hold":  # 不为观望时生成信号
            signal = self._create_signal(
                code=event_code,
                direction=decision,
                timestamp=current_time,
                event=event
            )

            if signal:
                signals.append(signal)
                print(f"[SIGNAL] #{self.signal_count}/{self.max_signals} {decision.upper()} {signal.code} {signal.business_timestamp} Strategy:{self.uuid[:8]} Signal:{signal.uuid[:8]}")
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
            Signal: 创建的信号, 失败时返回None
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

            # 创建信号 - ID现在从绑定的引擎动态获取
            signal = Signal(
                portfolio_id=self.portfolio_id,  # 从绑定的portfolio动态获取
                engine_id=self.engine_id,         # 从绑定的引擎动态获取
                run_id=self.run_id,               # 从绑定的引擎动态获取
                code=code,
                direction=direction_enum,
                reason=reason,
                business_timestamp=timestamp      # 使用TimeProvider的业务时间
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
            "timestamp": signal.business_timestamp,  # 存储业务时间而不是系统时间
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
                         sell_probability: Optional[float] = None) -> None:
        """
        更新策略参数

        Args:
            buy_probability: 新的买入概率
            sell_probability: 新的卖出概率
        """
        if buy_probability is not None:
            buy_probability = self._convert_to_float(buy_probability, 0.3)
            self.buy_probability = max(0.0, min(1.0, buy_probability))

        if sell_probability is not None:
            sell_probability = self._convert_to_float(sell_probability, 0.3)
            self.sell_probability = max(0.0, min(1.0, sell_probability))

        # 重新调整概率
        if self.buy_probability + self.sell_probability > 1.0:
            total = self.buy_probability + self.sell_probability
            self.buy_probability = self.buy_probability / total
            self.sell_probability = self.sell_probability / total

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