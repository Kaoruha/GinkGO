# Upstream: Portfolio (ORDERPARTIALLYFILLED stage, hooks fire post-deal)
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES
# Role: 平均持仓周期分析器 — 从建仓到清仓的平均天数

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class AvgHoldingPeriod(BaseAnalyzer):
    """平均持仓周期分析器

    每笔完整交易（买入→全部卖出）的持仓天数平均值。
    持仓天数 = 平仓时间 - Position.init_time 的自然日数。
    """

    __abstract__ = False

    def __init__(self, name: str = "avg_holding_period", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        self._counted_positions = set()
        self._holding_days = []

    def _do_activate(self, stage, portfolio_info, *args, **kwargs):
        current_time = portfolio_info.get("now") or portfolio_info.get("current_time")
        if current_time is None:
            return

        positions = portfolio_info.get("positions", {})
        for code, pos in positions.items():
            if pos.total_position == 0 and pos.uuid not in self._counted_positions:
                self._counted_positions.add(pos.uuid)
                init_time = pos.init_time
                if init_time is not None:
                    delta = (current_time - init_time).days
                    self._holding_days.append(max(delta, 1))

        avg = sum(self._holding_days) / len(self._holding_days) if self._holding_days else 0.0
        self.add_data(avg)

    @property
    def avg_days(self) -> float:
        return sum(self._holding_days) / len(self._holding_days) if self._holding_days else 0.0

    @property
    def total_trades(self) -> int:
        return len(self._holding_days)
