import tushare as ts
import pandas as pd
from ginkgo import GCONF
from ginkgo.libs import datetime_normalize


class GinkgoTushare(object):
    def __init__(self) -> None:
        self.pro = None
        self.connect()

    def connect(self) -> None:
        if self.pro == None:
            self.pro = ts.pro_api(GCONF.TUSHARETOKEN)

    def fetch_cn_stock_trade_day(self) -> pd.DataFrame:
        self.connect()
        r = self.pro.trade_cal()
        r = r.drop(["exchange", "pretrade_date"], axis=1)
        return r

    def fetch_cn_stock_info(self) -> pd.DataFrame:
        r = self.pro.stock_basic(
            fields=[
                "ts_code",
                "symbol",
                "name",
                "area",
                "industry",
                "list_date",
                "curr_type",
                "delist_date",
            ]
        )
        return r

    def fetch_cn_stock_daybar(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ) -> pd.DataFrame:
        start = datetime_normalize(date_start).strftime("%Y-%m-%d")
        end = datetime_normalize(date_end).strftime("%Y-%m-%d")
        r = self.pro.daily(ts_code=code, start_date=start, end_date=end, limit=50000)
        return r

    def fetch_cn_stock_min(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ) -> pd.DataFrame:
        pass

    def fetch_cn_stock_adjustfactor(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ) -> pd.DataFrame:
        pass
