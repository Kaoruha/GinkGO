import tushare as ts
import pandas as pd
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_normalize import datetime_normalize


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
        r = self.pro.stock_basic()
        return r

    def fetch_cn_stock_daybar(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ) -> pd.DataFrame:
        start = datetime_normalize(date_start).strftime("YYYYmmdd")
        end = datetime_normalize(date_end).strftime("YYYYmmdd")
        r = self.pro.daily(ts_code=code, start_date=start, end_date=end)
        print(r)
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
