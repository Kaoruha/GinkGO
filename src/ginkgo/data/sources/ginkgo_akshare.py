import pandas as pd
from ginkgo.data.sources.source_base import GinkgoSourceBase


class GinkgoAkShare(GinkgoSourceBase):
    def connect(self, *args, **kwargs):
        pass

    def fetch_cn_stock_trade_day(self, *args, **kwargs) -> pd.DataFrame:
        pass

    def fetch_cn_stock_list(self, date: any, *args, **kwargs):
        pass
