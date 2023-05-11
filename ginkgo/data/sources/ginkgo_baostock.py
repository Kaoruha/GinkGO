import baostock as bs
import pandas as pd
import datetime


class GinkgoBaoStock(object):
    def __init__(self):
        self._client = None
        self._cache = {}
        self._updated = {}

    @property
    def client(self):
        return self._client

    def login(self):
        self._client = bs.login()

    def logout(self):
        self._client = bs.logout()

    def _update_cache(self, key: str, data: any):
        self._cache[key] = data
        self._updated[key] = datetime.datetime.now()

    def _try_get_cache(self, key: str):
        now = datetime.datetime.now()
        try:
            last_update = self._updated[key]
        except Exception as e:
            last_update = None

        if last_update:
            delta = now - last_update
            if delta < datetime.timedelta(hours=4):
                return self._cache[key]
        else:
            return None

    @property
    def cn_stock_trade_day(self) -> pd.DataFrame:
        """
        Get the TradeDay
        """
        key = "trade_day"
        # Try get Cache
        cache = self._try_get_cache(key)
        if cache is not None:
            return cache

        result = self.fetch_cn_stock_trade_day()
        # Update Cache and updated time
        self._update_cache(key, result)
        return result

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
        if isinstance(date_start, datetime.datetime):
            date_start = date_start.strftime("%Y-%m-%d")
        if isinstance(date_end, datetime.datetime):
            date_en = date_end.strftime("%Y-%m-%d")

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
        data_list = []
        while (rs.error_code == "0") & rs.next():
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)

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
