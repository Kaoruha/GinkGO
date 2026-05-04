# Upstream: Portfolio (ORDERPARTIALLYFILLED stage, hooks fire post-deal)
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES
# Role: 平均盈亏比分析器 — 平均每笔盈利 / 平均每笔亏损

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class AvgWinLossRatio(BaseAnalyzer):
    """平均盈亏比分析器

    avg_win_loss_ratio = 平均盈利 / |平均亏损|
    从已完成平仓的 position 的 realized_pnl 逐笔统计。
    """

    __abstract__ = False

    def __init__(self, name: str = "avg_win_loss_ratio", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        self._counted_positions = set()
        self._wins = []
        self._losses = []

    def _do_activate(self, stage, portfolio_info, *args, **kwargs):
        positions = portfolio_info.get("positions", {})
        for code, pos in positions.items():
            if pos.total_position == 0 and pos.uuid not in self._counted_positions:
                self._counted_positions.add(pos.uuid)
                pnl = float(pos.realized_pnl)
                if pnl > 0:
                    self._wins.append(pnl)
                elif pnl < 0:
                    self._losses.append(abs(pnl))

        avg_win = sum(self._wins) / len(self._wins) if self._wins else 0.0
        avg_loss = sum(self._losses) / len(self._losses) if self._losses else 0.0
        ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        self.add_data(ratio)

    @property
    def avg_win(self) -> float:
        return sum(self._wins) / len(self._wins) if self._wins else 0.0

    @property
    def avg_loss(self) -> float:
        return sum(self._losses) / len(self._losses) if self._losses else 0.0
