# Upstream: Backtest Engines (cal调度 t1backtest.py:447), Component Registry
# Downstream: BaseStrategy factor_reader 钩子, Signal (信号发射), Selector.pick (universe)
# Role: 多因子截面 top-decile 组合策略 - 因子能力 capstone (#6796)

"""多因子截面 top-decile 组合策略 (#6796 capstone)。

读多个已物化因子的 PIT 值, 对当日 universe 做截面加权排名,
做多排名 top 分位 (默认 decile=10 即 top 10%) 的标的。

PIT (#6793): get_factor_value 内部只返 timestamp <= at_time 的值;
              策略用 portfolio_info["now"] / event.timestamp 作 at_time, 不读未来。

截面聚合: 引擎 per-price 事件驱动 (每标的每次行情调一次 cal),
          引擎不批量回调 "当日全部 universe", 策略侧自聚合 universe
          (selector.pick + 循环 get_factor_value) 组当日截面再排名。
"""

from typing import List, Dict, Optional

from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.trading.strategies.strategy_base import BaseStrategy


class FactorTopDecileStrategy(BaseStrategy):
    """多因子截面 top-decile 做多策略 (#6796)。

    Args:
        factors: {factor_name: weight} 多因子权重; 默认 {"ROC5": 1.0} 单因子
        decile: top 分位 (decile=10 → top 10%; decile=5 → top 20%)

    截面任一因子缺值 (None) 的 code 从排名中剔除 (PIT 无值不赌)。
    """

    def __init__(self, name: str = "FactorTopDecile",
                 factors: Optional[Dict[str, float]] = None,
                 decile: int = 10,
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self._factors = factors if factors else {"ROC5": 1.0}
        self._decile = max(1, int(decile))

    def _resolve_universe(self, portfolio_info: Dict, now) -> List[str]:
        """从 selector.pick(now) 聚合 universe; 空则退化 [event.code] (单标的)。"""
        universe: List[str] = []
        for sel in (portfolio_info or {}).get("selector", []) or []:
            picked = sel.pick(now) if hasattr(sel, "pick") else []
            if picked:
                universe.extend(picked)
        # dict 保序去重 (Python 3.7+)
        return list(dict.fromkeys(universe))

    def _cross_section_scores(self, universe: List[str], now) -> Dict[str, float]:
        """对 universe 各 code 算多因子加权 score。任一因子 None → 剔除该 code。"""
        scores: Dict[str, float] = {}
        for code in universe:
            total = 0.0
            ok = True
            for fname, weight in self._factors.items():
                v = self.get_factor_value(code, fname, now)
                if v is None:
                    ok = False
                    break
                total += weight * v
            if ok:
                scores[code] = total
        return scores

    def cal(self, portfolio_info: Dict, event, *args, **kwargs) -> List[Signal]:
        code = getattr(event, "code", None)
        if code is None:
            return []

        now = (portfolio_info or {}).get("now") or getattr(event, "timestamp", None)
        universe = self._resolve_universe(portfolio_info, now) or [code]
        scores = self._cross_section_scores(universe, now)
        if code not in scores or not scores:
            return []

        ranked = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
        n_top = max(1, len(ranked) // self._decile)
        if code in ranked[:n_top]:
            return [self.create_signal(
                code=code, direction=DIRECTION_TYPES.LONG,
                reason=f"cross-section top {n_top}/{len(ranked)} "
                       f"(score={scores[code]:.4f})")]
        return []
