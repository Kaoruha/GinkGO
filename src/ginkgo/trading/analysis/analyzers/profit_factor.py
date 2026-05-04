# Upstream: Portfolio (ORDERPARTIALLYFILLED stage, hooks fire post-deal)
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES
# Role: 盈亏比分析器 — 总盈利 / 总亏损（profit factor）

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class ProfitFactor(BaseAnalyzer):
    """盈亏比分析器

    profit_factor = 总盈利 / |总亏损|
    从已完成平仓的 position 的 realized_pnl 累加。
    """

    __abstract__ = False

    def __init__(self, name: str = "profit_factor", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        self._counted_positions = set()
        self._total_profit = 0.0
        self._total_loss = 0.0

    def _do_activate(self, stage, portfolio_info, *args, **kwargs):
        positions = portfolio_info.get("positions", {})
        for code, pos in positions.items():
            if pos.total_position == 0 and pos.uuid not in self._counted_positions:
                self._counted_positions.add(pos.uuid)
                pnl = float(pos.realized_pnl)
                if pnl > 0:
                    self._total_profit += pnl
                elif pnl < 0:
                    self._total_loss += abs(pnl)

        pf = self._total_profit / self._total_loss if self._total_loss > 0 else 0.0
        self.add_data(pf)

    @property
    def total_profit(self) -> float:
        return self._total_profit

    @property
    def total_loss(self) -> float:
        return self._total_loss
