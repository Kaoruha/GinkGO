# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: GinkgoTDX TDX数据源继承SourceBase提供通达信数据获取支持交易系统功能支持交易系统功能






import pandas as pd
import datetime
from typing import List

from ginkgo.data.sources.source_base import GinkgoSourceBase
from ginkgo.libs import datetime_normalize
from mootdx.quotes import Quotes
from ginkgo.libs import GLOG, retry, time_logger
from rich.console import Console

console = Console()


import random


class GinkgoTDX(GinkgoSourceBase):
    def __init__(self):
        self.client = Quotes.factory(market="std", bestip=False, timeout=15, quiet=True, verbose=0)
        self.bar_type = {
            "0": "5m",
            "1": "15m",
            "2": "30m",
            "3": "1h",
            "4": "days",
            "5": "week",
            "6": "mon",
            "7": "1m",
            "8": "1m",
            "9": "day",
            "10": "3mon",
            "11": "year",
        }

    @time_logger
    def fetch_live(self, codes: List[str], *args, **kwargs) -> pd.DataFrame:
        """
          Index(['market', 'code', 'active1', 'price', 'last_close', 'open', 'high',
         'low', 'servertime', 'reversed_bytes0', 'reversed_bytes1', 'vol',
         'cur_vol', 'amount', 's_vol', 'b_vol', 'reversed_bytes2',
         'reversed_bytes3', 'bid1', 'ask1', 'bid_vol1', 'ask_vol1', 'bid2',
         'ask2', 'bid_vol2', 'ask_vol2', 'bid3', 'ask3', 'bid_vol3', 'ask_vol3',
         'bid4', 'ask4', 'bid_vol4', 'ask_vol4', 'bid5', 'ask5', 'bid_vol5',
         'ask_vol5', 'reversed_bytes4', 'reversed_bytes5', 'reversed_bytes6',
         'reversed_bytes7', 'reversed_bytes8', 'reversed_bytes9', 'active2',
         'volume'],
        dtype='object')
        """
        df = self.client.quotes(symbol=codes)
        console.print(f":crab: Got {df.shape[0]} records about live from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_latest_bar(self, code: str, frequency: int = 7, count: int = 20, *args, **kwargs) -> pd.DataFrame:
        """
        frequency -> K线种类
        self.assertGreater(len(df), 0)
        0 => 5分钟K线 => 5m
        1 => 15分钟K线 => 15m
        2 => 30分钟K线 => 30m
        3 => 小时K线 => 1h
        4 => 日K线 (小数点x100) => days
        5 => 周K线 => week
        6 => 月K线 => mon
        7 => 1分钟K线(好像一样) => 1m
        8 => 1分钟K线(好像一样) => 1m
        9 => 日K线 => day
        10 => 季K线 => 3mon
        11 => 年K线 => year
        """
        code_num = code.split(".")[0]
        df = self.client.bars(symbol=code_num, frequency=frequency, offset=count)
        console.print(
            f":crab: Got {df.shape[0]} records about {code_num} {self.bar_type[str(frequency)]} bar from [bold #E4C1C0]TDX[/]."
        )
        return df

    @time_logger
    @retry
    def fetch_stock_list(self, *args, **kwargs) -> pd.DataFrame:
        from mootdx import consts

        df_sh = self.client.stocks(market=consts.MARKET_SH)
        df_sh["code"] = df_sh["code"].apply(lambda x: str(x) + ".SH")
        df_sz = self.client.stocks(market=consts.MARKET_SZ)
        df_sz["code"] = df_sz["code"].apply(lambda x: str(x) + ".SZ")
        df = pd.concat([df_sh, df_sz])
        console.print(f":crab: Got {df.shape[0]} records about stocklist from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_history_transaction_summary(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:
        code_num = code.split(".")[0]
        date = datetime_normalize(date)
        date_num = date.strftime("%Y%m%d")
        date_num = int(date_num)
        df = self.client.minutes(symbol=code_num, date=date_num)
        console.print(f":crab: Got {df.shape[0]} records about {code} Tick Summary from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_history_transaction_detail(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:

        def time_combine(time):
            new_date = datetime_normalize(date)
            time = datetime.datetime.strptime(time, "%H:%M").time()
            return datetime.datetime.combine(new_date, time)

        code_num = code.split(".")[0]
        code_market = code.split(".")[1]
        if code_market.upper() not in ["SH", "SZ"]:
            console.print("TDX api just support SH and SZ now.")
            return
        date = datetime_normalize(date)
        date_num = date.strftime("%Y%m%d")
        date_num = int(date_num)
        start = 0
        page = 1000
        df = pd.DataFrame()
        with console.status(f":dango: Fetching {code} tick records from [bold #E4C1C0]TDX[/].") as status:
            while True:
                temp = self.client.transactions(symbol=code_num, start=start, offset=page, date=date_num)
                start += page
                df = pd.concat([df, temp])
                if temp.shape[0] < page:
                    break
        console.print(f":crab: Got {df.shape[0]} tick records about {code} from [bold #E4C1C0]TDX[/].")
        if df.shape[0] == 0:
            return pd.DataFrame()
        else:
            df["timestamp"] = df["time"].apply(lambda x: time_combine(x))
            df = df.sort_values(by="timestamp")
            df = df.reset_index(drop=True)
            return df

    @time_logger
    @retry
    def fetch_adjustfactor(self, code: str, *args, **kwargs) -> pd.DataFrame:
        code_num = code.split(".")[0]
        df = self.client.xdxr(symbol=code_num)
        console.print(f":crab: Got {df.shape[0]} records about {code} adjustfactor from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_history_daybar(self, code: str, start_date: any, end_date: any, *args, **kwargs) -> pd.DataFrame:
        code_num = code.split(".")[0]
        start_date = datetime_normalize(start_date).strftime("%Y-%m-%d")
        end_date = datetime_normalize(end_date).strftime("%Y-%m-%d")
        df = self.client.k(symbol=code_num, begin=start_date, end=end_date)
        console.print(f":crab: Got {df.shape[0]} records about {code} OHLC from [bold #E4C1C0]TDX[/].")
        return df
