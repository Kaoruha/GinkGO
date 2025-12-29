# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: GinkgoAKShare AKShare数据源继承SourceBase提供A股数据获取支持交易系统功能






import pandas as pd
from ginkgo.data.sources.source_base import GinkgoSourceBase


class GinkgoAkShare(GinkgoSourceBase):
    def connect(self, *args, **kwargs):
        pass

    def fetch_cn_stock_trade_day(self, *args, **kwargs) -> pd.DataFrame:
        pass

    def fetch_cn_stock_list(self, date: any, *args, **kwargs):
        pass
