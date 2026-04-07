# Upstream: Portfolio (NEWDAY stage), BASIC_ANALYZERS
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES, to_decimal, pandas, GLOG
# Role: 夏普比率分析器 — 滚动365日计算(年化收益率-基准收益率)/收益率标准差






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.data.number import to_decimal
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.libs import GLOG
import pandas as pd


class SharpeRatio(BaseAnalyzer):
    """夏普比率分析器 - 计算风险调整后的收益指标"""
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "sharpe_ratio", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._base_value = None
        self._days = 0
        self._annual_returns = []
        self._base_profit = 0.05

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """激活夏普比率计算"""
        current_worth = float(to_decimal(portfolio_info.get("worth", 0)))

        if self._base_value is None:
            self._base_value = current_worth
            self.add_data(0)  # 初始夏普比率为0
            return

        self._days += 1
        if self._days > 365:
            self._days = self._days - 365
            self._base_value = current_worth

        if self._days > 0 and self._base_value > 0:
            times = 365 / self._days
            annual_return = (current_worth / self._base_value) ** times - 1
            self._annual_returns.append(annual_return)
            
            # 计算夏普比率
            if len(self._annual_returns) > 1:
                std = pd.Series(self._annual_returns).std()
                try:
                    value = (annual_return - self._base_profit) / std if std > 0 else 0
                except Exception as e:
                    GLOG.ERROR(f"SharpeRatio calculation error: {e}")
                    value = -1
            else:
                value = 0
        else:
            value = 0
            
        self.add_data(value)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录夏普比率数据到数据库"""
        self.add_record()
