# Upstream: Portfolio (ORDERPARTIALLYFILLED stage, hooks fire post-deal)
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES
# Role: 交易维度胜率分析器 — 每个完整仓位生命周期（买入→全部卖出）算一笔交易

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class TradeWinRate(BaseAnalyzer):
    """交易维度胜率分析器

    每个完整仓位生命周期（买入→全部卖出）算一笔交易。
    win_rate = 盈利笔数 / (盈利笔数 + 亏损笔数)
    """

    __abstract__ = False

    def __init__(self, name: str = "trade_win_rate", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        self._counted_positions = set()
        self._win_count = 0
        self._loss_count = 0

    def _do_activate(self, stage, portfolio_info, *args, **kwargs):
        positions = portfolio_info.get("positions", {})
        for code, pos in positions.items():
            if pos.total_position == 0 and pos.uuid not in self._counted_positions:
                self._counted_positions.add(pos.uuid)
                pnl = float(pos.realized_pnl)
                if pnl > 0:
                    self._win_count += 1
                elif pnl < 0:
                    self._loss_count += 1

        total = self._win_count + self._loss_count
        win_rate = self._win_count / total if total > 0 else 0.0
        self.add_data(win_rate)

    @property
    def win_count(self) -> int:
        return self._win_count

    @property
    def loss_count(self) -> int:
        return self._loss_count

    @property
    def total_trades(self) -> int:
        return self._win_count + self._loss_count
