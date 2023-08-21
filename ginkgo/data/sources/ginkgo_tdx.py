from ginkgo.data.sources.source_base import GinkgoSourceBase
import pandas as pd
from ginkgo.libs import datetime_normalize
from pytdx.hq import TdxHq_API
from ginkgo import GLOG
import random


class GinkgoTDX(GinkgoSourceBase):
    def __init__(self):
        self.api = TdxHq_API(heartbeat=True)
        self.ips = [
            "119.147.212.81",
        ]

    @property
    def random_ip(self) -> str:
        return random.choice(self.ips)

    def fetch_history_transaction(self, code: str, date: any) -> pd.DataFrame:
        date = datetime_normalize(date)
        date_num = date.strftime("%Y%m%d")
        date_num = int(date_num)
        max_try = 10
        try_times = 0
        slice_count = 1000
        code_split = code.split(".")
        code = code_split[0]
        market = 1
        if code_split[1] == "SH":
            market = 1
        elif code_split[1] == "SZ":
            market = 0
        else:
            return pd.DataFrame()
        start = 0
        rs = []
        GLOG.INFO(f"Fetching Tick {code} on {date}")
        while try_times < max_try:
            try:
                with self.api.connect(self.random_ip, 7709):
                    while True:
                        data = self.api.get_history_transaction_data(
                            market, code, start, slice_count, date_num
                        )

                        if data is None:
                            break
                        if len(data) == 0:
                            break
                        elif len(data) < slice_count:
                            rs += data
                            break
                        else:
                            rs += data
                            start += slice_count

                    if len(rs) == 0:
                        return pd.DataFrame()
                    else:
                        df = self.api.to_df(rs)
                        df = df.sort_values("time", ascending=True)
                        df = df.reset_index(drop=True)
                        df = df.rename(columns={"time": "timestamp", "vol": "volume"})
                        return df
            except Exception as e:
                print(e)
                try_times += 1
        return pd.DataFrame()
