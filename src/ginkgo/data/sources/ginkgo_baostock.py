import baostock as bs
import pandas as pd
import datetime
from time import sleep

from ginkgo.data.sources.source_base import GinkgoSourceBase


class GinkgoBaoStock(GinkgoSourceBase):
    def __init__(self, *args, **kwargs):
        super(GinkgoBaoStock, self).__init__(*args, **kwargs)
        self._updated = {}

    def connect(self):
        self.login()

    def login(self):
        self._client = bs.login()

    def logout(self):
        self._client = bs.logout()

    def fetch_cn_stock_trade_day(self) -> pd.DataFrame:
        """
        Get A share trade day data from baostock
        """
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

        return result

    def fetch_cn_stock_list(self, date: str or datetime.datetime):
        """
        Get the stock list of china.
        """
        if isinstance(date, datetime.datetime):
            date = date.strftime("%Y-%m-%d")
        rs = bs.query_all_stock(day=date)
        print(rs.error_code)
        print(rs.error_msg)
        if rs.error_code == "10001001":
            self.login()
            rs = bs.query_all_stock(day=date)
        data_list = []
        while (rs.error_code == "0") & rs.next():
            data_list.append(rs.get_row_data())
        rs.fields[1] = "trade_status"
        result = pd.DataFrame(data_list, columns=rs.fields)
        return result

    def fetch_cn_stock_daybar(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
        adjustflag: str = "3",
    ):
        print("Function IN...")
        if isinstance(date_start, datetime.datetime):
            date_start = date_start.strftime("%Y-%m-%d")
        if isinstance(date_end, datetime.datetime):
            date_en = date_end.strftime("%Y-%m-%d")

        print("Date Transformed.")
        rs = bs.query_history_k_data_plus(
            code,
            "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
            start_date=date_start,
            end_date=date_end,
            frequency="d",
            adjustflag="3",
        )
        print(rs.error_code)
        print(rs.error_msg)
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
            print(rs.error_code)
            print(rs.error_msg)

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
            print(rs.error_code)
            print(rs.error_msg)

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

        return result

    def fetch_cn_stock_min5(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
        adjustflag: str = "3",
    ):
        if isinstance(date_start, datetime.datetime):
            date_start = date_start.strftime("%Y-%m-%d")
        if isinstance(date_end, datetime.datetime):
            date_en = date_end.strftime("%Y-%m-%d")

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

        return result

    def fetch_cn_stock_adjustfactor(
        self,
        code: str,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ):
        if isinstance(date_start, datetime.datetime):
            date_start = date_start.strftime("%Y-%m-%d")
        if isinstance(date_end, datetime.datetime):
            date_en = date_end.strftime("%Y-%m-%d")

        rs_list = []
        rs_factor = bs.query_adjust_factor(
            code=code, start_date="2015-01-01", end_date="2017-12-31"
        )
        if rs_factor.error_code == "10001001":
            self.login()
            rs_factor = bs.query_adjust_factor(
                code=code, start_date="2015-01-01", end_date="2017-12-31"
            )
        while (rs_factor.error_code == "0") & rs_factor.next():
            rs_list.append(rs_factor.get_row_data())
        result_factor = pd.DataFrame(rs_list, columns=rs_factor.fields)

        return result_factor
