import tushare as ts
import threading
import pandas as pd
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize
from ginkgo.libs.ginkgo_logger import GLOG


class GinkgoTushare(object):
    def __init__(self) -> None:
        self.pro = None
        self.connect()
        self.try_max = 5

    def connect(self) -> None:
        if self.pro == None:
            self.pro = ts.pro_api(GCONF.TUSHARETOKEN)

    def fetch_cn_stock_trade_day(self) -> pd.DataFrame:
        try_time = 0
        while try_time <= self.try_max:
            GLOG.DEBUG("Trying get cn stock trade day.")
            r = self.pro.trade_cal()
            if r.shape[0] == 0:
                try_time += 1
                GLOG.ERROR(
                    f"Tushare API: TradeCalendar returns nothing. Retry: {try_time}"
                )
            else:
                r = r.drop(["exchange", "pretrade_date"], axis=1)
                return r
            if try_time >= self.try_max:
                return

    def fetch_cn_stock_info(self) -> pd.DataFrame:
        try_time = 0
        while try_time <= self.try_max:
            GLOG.DEBUG("Trying get cn stock info.")
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
            if r.shape[0] == 0:
                try_time += 1
                GLOG.ERROR(
                    f"Tushare API: CN Stock Info returns nothing. Retry: {try_time}"
                )
            else:
                return r
            if try_time >= self.try_max:
                return

    def fetch_cn_stock_daybar(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
    ) -> pd.DataFrame:
        start = datetime_normalize(date_start).strftime("%Y%m%d")
        end = datetime_normalize(date_end).strftime("%Y%m%d")
        r = self.pro.daily(
            **{
                "ts_code": code,
                "trade_date": "",
                "start_date": start,
                "end_date": end,
                "offset": "",
                "limit": "50000",
            }
        )
        return r

    def fetch_cn_stock_min(
        self,
        code: str,
        date_start: str or datetime.datetime = GCONF.DEFAULTSTART,
        date_end: str or datetime.datetime = GCONF.DEFAULTEND,
    ) -> pd.DataFrame:
        pass

    def fetch_cn_stock_adjustfactor(
        self,
        code: str,
        date_start: str or datetime.datetime = GCONF.DEFAULTSTART,
        date_end: str or datetime.datetime = GCONF.DEFAULTEND,
    ) -> pd.DataFrame:
        # if "BJ" in code:
        #     GLOG.WARN("Tushare API: BJ stock not supported.")
        #     return
        start = datetime_normalize(date_start).strftime("%Y-%m-%d")
        end = datetime_normalize(date_end).strftime("%Y-%m-%d")
        r = self.pro.adj_factor(
            ts_code=code, start_date=start, end_date=end, limit=10000
        )
        if r.shape[0] == 0:
            return pd.DataFrame()
        r.reset_index(drop=True, inplace=True)
        return r
