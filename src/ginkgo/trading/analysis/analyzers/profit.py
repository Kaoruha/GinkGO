# Upstream: Portfolio (NEWDAY/ENDDAY stage), BASIC_ANALYZERS, ResultPlot
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES, worth_delta, get_worth, pandas
# Role: 利润分析器 — 计算每日盈亏（当日资产-前日资产），记录日度利润序列






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.trading.analysis.worth_delta import worth_delta
from ginkgo.trading.bases.portfolio_info_access import get_worth
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class Profit(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "ProfitAna", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        self._last_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """激活利润计算，计算当日利润"""
        current_worth = get_worth(portfolio_info)
        delta = worth_delta(current_worth, self._last_worth)

        if delta is None:
            value = 0
        else:
            value = delta.pnl

        self._last_worth = current_worth
        self.add_data(value)

