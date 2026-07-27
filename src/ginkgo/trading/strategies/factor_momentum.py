# Upstream: Backtest Engines (cal调度), Component Registry (DB实例化)
# Downstream: BaseStrategy (factor_reader 钩子), Signal (信号发射)
# Role: 因子动量示例策略 - 演示 BaseStrategy factor_reader 钩子的 PIT 用法(#6791 tracer)

from typing import List, Dict
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.trading.strategies.strategy_base import BaseStrategy


class FactorMomentumStrategy(BaseStrategy):
    """因子动量示例策略(#6791 Phase 0 tracer)。

    读 Alpha158 动量因子(默认 ROC5)的 PIT 值:
    - 因子值 > buy_threshold  → LONG
    - 因子值 < sell_threshold → SHORT
    其余情形不发信号。未绑定 factor_reader 或无因子值时静默返回。

    Note: PIT 硬约束由 factor_reader 负责(只返回 timestamp <= at_time 的值);
    本策略仅保证用 portfolio_info["now"] / event.timestamp 作为 at_time,
    不主动读未来(#6793 在 reader 层加泄漏反例套件)。
    """

    def __init__(self, name: str = "FactorMomentum",
                 factor_name: str = "ROC5",
                 buy_threshold: float = 0.0,
                 sell_threshold: float = 0.0,
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self._factor_name = factor_name
        self._buy_threshold = buy_threshold
        self._sell_threshold = sell_threshold

    def cal(self, portfolio_info: Dict, event, *args, **kwargs) -> List[Signal]:
        code = getattr(event, 'code', None)
        if code is None:
            return []

        # PIT: 用回测当前时间(event 时刻)读因子,不读未来
        now = (portfolio_info or {}).get("now") or getattr(event, 'timestamp', None)
        val = self.get_factor_value(code, self._factor_name, now)
        if val is None:
            return []

        if val > self._buy_threshold:
            return [self.create_signal(
                code=code, direction=DIRECTION_TYPES.LONG,
                reason=f"{self._factor_name}={val:.4f} > {self._buy_threshold}")]
        if val < self._sell_threshold:
            return [self.create_signal(
                code=code, direction=DIRECTION_TYPES.SHORT,
                reason=f"{self._factor_name}={val:.4f} < {self._sell_threshold}")]
        return []
