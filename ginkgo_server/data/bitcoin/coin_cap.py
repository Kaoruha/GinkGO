"""
调用CoinCapAPI
获取数据
"""
import threading
import requests
import logging
import datetime
import time
import json
import pandas as pd


class CoinCapAPI(object):
    _instance_lock = threading.Lock()
    interval_list = ["m1", "m5", "m15", "m30", "h1", "h2", "h6", "h12", "d1"]
    init_date = "2010-07-17"
    one_day_sec = 1000 * (60 * 60 * 24)

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            with CoinCapAPI._instance_lock:
                if not hasattr(cls, "_instance"):
                    CoinCapAPI._instance = super().__new__(cls)

            return CoinCapAPI._instance

    def get_url(self, coin_id, interval, start, end):
        """
        API拼接
        """
        if interval not in self.interval_list:
            print(f"{interval} is not supported.")
            return
        url = f"http://api.coincap.io/v2/assets/{coin_id}/history?interval={interval}&start={start}&end={end}"
        return url

    def convert_date2stamp(self, date: str):
        """
        将日期字符串转化为毫秒级别的时间戳
        """
        s = date + " 00:00:00"
        t = time.strptime(s, "%Y-%m-%d %H:%M:%S")
        stamp = int(time.mktime(t)) * 1000
        return stamp

    def get_delta_day(self, date: str, delta: int):
        """
        输入一个日期，返回第二天的日期字符串
        """
        start = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        next_day = start + datetime.timedelta(days=delta)
        return next_day.strftime("%Y-%m-%d")

    def get_min_data_by_date(self, coin_id, interval, date):
        """
        获取某个虚拟货币某天的分钟数据
        """
        t1 = time.time()
        start_stamp = self.convert_date2stamp(date=date)
        end_day = self.get_delta_day(date=date, delta=1)
        end_stamp = self.convert_date2stamp(date=end_day)
        request_link = self.get_url(
            coin_id=coin_id, interval=interval, start=start_stamp, end=end_stamp
        )
        t2 = time.time()
        # print(request_link)
        r = requests.get(url=request_link)
        t3 = time.time()
        content = json.loads(r.content)
        df = pd.DataFrame(content["data"])
        t4 = time.time()
        print(f"耗时:{round(t4-t1,3)}s API响应:{round(t3-t2,3)}s ")
        return df

    def get_min_data_by_time(self, coin_id, interval, time_start):
        """
        获取某个虚拟货币某天的分钟数据
        """
        t1 = time.time()
        start_stamp = time_start
        end_stamp = time_start + self.one_day_sec
        request_link = self.get_url(
            coin_id=coin_id, interval=interval, start=start_stamp, end=end_stamp
        )
        t2 = time.time()
        # print(request_link)
        r = requests.get(url=request_link)
        t3 = time.time()
        content = json.loads(r.content)
        # print(content)
        df = pd.DataFrame(content["data"])
        t4 = time.time()
        print(f"{coin_id} 获取耗时:{round(t4-t1,3)}s API响应:{round(t3-t2,3)}s ")
        return df

    def get_coin_list(self):
        t1 = time.time()
        request_link = "https://api.coincap.io/v2/assets"
        t2 = time.time()
        # print(request_link)
        r = requests.get(url=request_link)
        t3 = time.time()
        content = json.loads(r.content)

        df = pd.DataFrame(content["data"])

        df = df.drop(["explorer"], axis=1)
        t4 = time.time()

        # print(df)
        print(f"耗时:{round(t4-t1,3)}s API响应:{round(t3-t2,3)}s ")
        return df


logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
coin_cap_instance = CoinCapAPI()
