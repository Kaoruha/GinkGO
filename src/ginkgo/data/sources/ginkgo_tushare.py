import tushare as ts
import threading
import pandas as pd
from ginkgo.libs import datetime_normalize, GCONF, retry, time_logger, GLOG
from rich.console import Console

console = Console()


class GinkgoTushare(object):
    def __init__(self, *args, **kwargs) -> None:
        self.pro = None
        self.connect()

    def connect(self, *args, **kwargs) -> None:
        if self.pro == None:
            self.pro = ts.pro_api(GCONF.TUSHARETOKEN)

    @time_logger
    @retry(max_try=5)
    def fetch_cn_stock_trade_day(self, *args, **kwargs) -> pd.DataFrame:
        GLOG.DEBUG("Trying get cn stock trade day.")
        try:
            r = self.pro.trade_cal()
            if r.shape[0] == 0:
                return pd.DataFrame()
            console.print(f":crab: Got {r.shape[0]} records about trade day.")
            return r
        except Exception as e:
            raise e
        finally:
            pass

    @time_logger
    @retry(max_try=5)
    def fetch_cn_stockinfo(self, *args, **kwargs) -> pd.DataFrame:
        GLOG.DEBUG("Trying get cn stock info.")
        try:
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
                return pd.DataFrame()
            console.print(f":crab: Got {r.shape[0]} records about stockinfo.")
            return r
        except Exception as e:
            raise e
        finally:
            pass

    @time_logger
    @retry(max_try=5)
    def fetch_cn_stock_daybar(
        self, code: str, start_date: any = GCONF.DEFAULTSTART, end_date: any = GCONF.DEFAULTEND, *args, **kwargs
    ) -> pd.DataFrame:
        start = datetime_normalize(start_date).strftime("%Y%m%d")
        end = datetime_normalize(end_date).strftime("%Y%m%d")
        try:
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
            if r.shape[0] == 0:
                return pd.DataFrame()
            r.fillna(0, inplace=True)
            return r
        except Exception as e:
            raise e
        finally:
            pass

    def fetch_cn_stock_min(
        self, code: str, start_date: any = GCONF.DEFAULTSTART, end_date: any = GCONF.DEFAULTEND, *args, **kwargs
    ) -> pd.DataFrame:
        pass

    @time_logger
    @retry(max_try=5)
    def fetch_cn_stock_adjustfactor(
        self, code: str, start_date: any = GCONF.DEFAULTSTART, end_date: any = GCONF.DEFAULTEND, *args, **kwargs
    ) -> pd.DataFrame:
        start = datetime_normalize(start_date).strftime("%Y-%m-%d")
        end = datetime_normalize(end_date).strftime("%Y-%m-%d")
        try:
            r = self.pro.adj_factor(ts_code=code, start_date=start, end_date=end, limit=10000)
            if r.shape[0] == 0:
                return pd.DataFrame()
            console.print(f":crab: Got {r.shape[0]} records about {code} adjustfactor.")
            r.reset_index(drop=True, inplace=True)
            return r
        except Exception as e:
            raise e
        finally:
            pass
