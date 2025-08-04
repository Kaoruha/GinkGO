from ginkgo.backtest.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class Profit(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "ProfitAna", *args, **kwargs):
        super(Profit, self).__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._last_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """激活利润计算，计算当日利润"""
        current_worth = portfolio_info.get("worth", 0)
        
        if self._last_worth is None:
            self._last_worth = current_worth
            value = 0
        else:
            value = current_worth - self._last_worth
            self._last_worth = current_worth
            
        self.add_data(value)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录利润数据到数据库"""
        self.add_record()
