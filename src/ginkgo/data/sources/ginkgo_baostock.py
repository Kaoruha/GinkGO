# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: GinkgoBaoStock BaoStock数据源继承SourceBase提供A股数据获取支持交易系统功能






import baostock as bs
import pandas as pd
import datetime

from time import sleep

from ginkgo.data.sources.source_base import GinkgoSourceBase
from ginkgo.libs import time_logger, datetime_normalize, retry, GLOG
from rich.console import Console

console = Console()


class GinkgoBaoStock(GinkgoSourceBase):
    def __init__(self, *args, **kwargs):
        super(GinkgoBaoStock, self).__init__(*args, **kwargs)
        self._updated = {}
        self.max_try = 5

    def connect(self, *args, **kwargs):
        self.login()

    def login(self, *args, **kwargs):
        self._client = bs.login()

    def logout(self, *args, **kwargs):
        self._client = bs.logout()

    @time_logger
    @retry(max_try=3)
    def fetch_cn_stock_trade_day(self, *args, **kwargs) -> pd.DataFrame:
        """
        Get A share trade day data from baostock
        """
        for i in range(self.max_try):
            try:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                rs = bs.query_trade_dates(start_date="1990-12-19", end_date=today)
                # If not login
                if rs.error_code == "10001001":
                    self.login()
                    rs = bs.query_trade_dates(start_date="1990-12-19", end_date=today)

                # Merge the records
                data_list = []
                while (rs.error_code == "0") & rs.next():
                    data_list.append(rs.get_row_data())
                rs.fields[0] = "timestamp"
                result = pd.DataFrame(data_list, columns=rs.fields)
                console.print(f":crab: Got {result.shape[0]} records about trade day from [bold #E4C1C0]Baostock[/].")

                return result
            except Exception as e:
                GLOG.ERROR(f"fetch cn stock trade day failed {i+1}/{self.max_try}")
            finally:
                pass

    @time_logger
    @retry(max_try=3)
    def fetch_cn_stock_list(self, date: any, *args, **kwargs):
        """
        Get the stock list of china.
        """
        date = datetime_normalize(date).strftime("%Y-%m-%d")
        rs = bs.query_all_stock(day=date)
        if rs.error_code == "10001001":
            self.login()
            rs = bs.query_all_stock(day=date)
        data_list = []
        while (rs.error_code == "0") & rs.next():
            data_list.append(rs.get_row_data())
        rs.fields[1] = "trade_status"
        result = pd.DataFrame(data_list, columns=rs.fields)
        console.print(f":crab: Got {result.shape[0]} records about stock from [bold #E4C1C0]Baostock[/].")
        return result

    @time_logger
    @retry(max_try=3)
    def fetch_cn_stock_daybar(
        self,
        code: str,
        date_start: any,
        date_end: any,
        adjustflag: str = "3",
    ):
        if isinstance(date_start, datetime.datetime):
            date_start = date_start.strftime("%Y-%m-%d")
        if isinstance(date_end, datetime.datetime):
            date_en = date_end.strftime("%Y-%m-%d")

        GLOG.DEBUG("Date Transformed.")
        rs = bs.query_history_k_data_plus(
            code,
            "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
            start_date=date_start,
            end_date=date_end,
            frequency="d",
            adjustflag="3",
        )
        if rs.error_code == "10001001":
            self.login()
            rs = bs.query_history_k_data_plus(
                code,
                "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                start_date=date_start,
                end_date=date_end,
                frequency="d",
                adjustflag="3",
            )

        if rs.error_code == "10002007":
            sleep(1)
            self.logout()
            self.login()
            rs = bs.query_history_k_data_plus(
                code,
                "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                start_date=date_start,
                end_date=date_end,
                frequency="d",
                adjustflag="3",
            )

        if rs.error_code == "10004011":
            return pd.DataFrame()
        data_list = []
        while (rs.error_code == "0") & rs.next():
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        float_column = [
            "open",
            "high",
            "low",
            "close",
        ]
        for i in float_column:
            result[i] = result[i].astype("float")

        console.print(f":crab: Got {result.shape[0]} records about daybar from [bold #E4C1C0]Baostock[/].")
        return result

    @time_logger
    @retry(max_try=3)
    def fetch_cn_stock_min5(
        self,
        code: str,
        date_start: any,
        date_end: any,
        adjustflag: str = "3",
    ):
        """
        Seems not work.
        """
        date_start = datetime_normalize(date_start).strftime("%Y-%m-%d")
        date_end = datetime_normalize(date_end).strftime("%Y-%m-%d")

        rs = bs.query_history_k_data_plus(
            code,
            "date,time,code,open,high,low,close,volume,amount,adjustflag",
            start_date=date_start,
            end_date=date_end,
            frequency="5",
            adjustflag="3",
        )
        if rs.error_code == "10001001":
            self.login()
            rs = bs.query_history_k_data_plus(
                code,
                "date,time,code,open,high,low,close,volume,amount,adjustflag",
                start_date=date_start,
                end_date=date_end,
                frequency="5",
                adjustflag="3",
            )
        data_list = []
        while (rs.error_code == "0") & rs.next():
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        console.print(f":crab: Got {result.shape[0]} records about stock min5 from [bold #E4C1C0]Baostock[/].")

        return result

    @time_logger
    @retry(max_try=3)
    def fetch_cn_stock_adjustfactor(
        self,
        code: str,
        date_start: any,
        date_end: any,
    ):
        date_start = datetime_normalize(date_start).strftime("%Y-%m-%d")
        date_end = datetime_normalize(date_end).strftime("%Y-%m-%d")
        rs_list = []
        rs_factor = bs.query_adjust_factor(code=code, start_date=date_start, end_date=date_end)
        if rs_factor.error_code == "10001001":
            self.login()
            rs_factor = bs.query_adjust_factor(code=code, start_date=date_start, end_date=date_end)
        while (rs_factor.error_code == "0") & rs_factor.next():
            rs_list.append(rs_factor.get_row_data())
        result = pd.DataFrame(rs_list, columns=rs_factor.fields)

        console.print(f":crab: Got {result.shape[0]} records about adjustfactor from [bold #E4C1C0]Baostock[/].")
        return result
