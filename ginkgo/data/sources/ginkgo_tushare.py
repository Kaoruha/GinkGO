import tushare as ts
import pandas as pd
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_logger import GLOG


class GinkgoTushare(object):
    def __init__(self) -> None:
        self.pro = None

    def connect(self) -> None:
        if self.pro == None:
            self.pro = ts.pro_api(GCONF.TUSHARETOKEN)

    def fetch_cn_stock_trade_day(self) -> pd.DataFrame:
        r = self.pro.trade_cal()
        print(r)
        print(r.columns)
        return r

    def fetch_cn_stock_list(self, date: str or datetime.datetime) -> pd.DataFrame:
        # r = self.pro.stock_basic()
        print(r)
        return r

    def fetch_cn_stock_daybar(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ) -> pd.DataFrame:
        pass

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
