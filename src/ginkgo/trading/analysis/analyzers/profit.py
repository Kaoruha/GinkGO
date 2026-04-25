# Upstream: Portfolio (NEWDAY/ENDDAY stage), BASIC_ANALYZERS, ResultPlot
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES, to_decimal, pandas
# Role: 利润分析器 — 计算每日盈亏（当日资产-前日资产），记录日度利润序列






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.data.number import to_decimal
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
        current_worth = float(to_decimal(portfolio_info.get("worth", 0)))
        
        if self._last_worth is None:
            self._last_worth = current_worth
            value = 0
        else:
            value = current_worth - self._last_worth
            self._last_worth = current_worth
            
        self.add_data(value)

