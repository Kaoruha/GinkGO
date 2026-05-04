# Upstream: Portfolio (ORDERPARTIALLYFILLED stage, hooks fire post-deal)
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES
# Role: 最大连续亏损分析器 — 记录最长连续亏损笔数

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class MaxConsecutiveLosses(BaseAnalyzer):
    """最大连续亏损分析器

    追踪每笔完整交易的盈亏序列，统计最长连续亏损笔数。
    """

    __abstract__ = False

    def __init__(self, name: str = "max_consecutive_losses", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        self._counted_positions = set()
        self._current_streak = 0
        self._max_streak = 0

    def _do_activate(self, stage, portfolio_info, *args, **kwargs):
        positions = portfolio_info.get("positions", {})
        for code, pos in positions.items():
            if pos.total_position == 0 and pos.uuid not in self._counted_positions:
                self._counted_positions.add(pos.uuid)
                pnl = float(pos.realized_pnl)
                if pnl < 0:
                    self._current_streak += 1
                    if self._current_streak > self._max_streak:
                        self._max_streak = self._current_streak
                else:
                    self._current_streak = 0

        self.add_data(self._max_streak)

    @property
    def max_streak(self) -> int:
        return self._max_streak

    @property
    def current_streak(self) -> int:
        return self._current_streak
