import datetime
import os
import sys
import threading
import time
import baostock as bs
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.thread_manager import thread_manager


class BaoStockData(object):
    _instance_lock = threading.Lock()
    init_date = "1999-07-26"
    data_split = 10000

    def __init__(self):
        self.getdata_count = 0
        self.getlastdate_count = 0
        self.getdata_max = 10
        self.getlastdate_max = 10
        # self.__init_dir()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            with BaoStockData._instance_lock:
                if not hasattr(cls, "_instance"):
                    BaoStockData._instance = super().__new__(cls)

            return BaoStockData._instance

    def login(self) -> None:
        """
        baostock 登录
        :return:
        """
        lg = bs.login(user_id="anonymous", password="123456")
        if lg.error_code == "0":
            gl.logger.warning("Baostock Login Success.")
        else:
            gl.logger.error("Login respond error_code:" + lg.error_code)
            gl.logger.error("Login respond  error_msg:" + lg.error_msg)

    def logout(self) -> None:
        """
        baostock 退出
        :return:
        """
        bs.logout
        gl.logger.warning("BaoStock LogOut.")

    # 从 baostock 获取数据
    def get_data(
        self,
        code: str = "sh.600000",
        data_frequency: str = "d",
        start_date: str = init_date,
        end_date: str = "2006-02-01",
    ) -> pd.DataFrame:
        """
        从baostock获取数据
        :param code: 股票/指数 代码
        :param data_frequency: 数据频率'd' or '5'
        :param start_date: 起始日期
        :param end_date: 截至日期
        :return: 返回一个DataFrame数据
        """
        daily_query = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
        min_query = "date,time,code,open,high,low,close,volume,amount,adjustflag"
        dimension = daily_query
        frequency = "d"
        # now = datetime.datetime.now().strftime("%H:%M:%S")

        # 根据查询数据的频率，修正查询数据的维度与频率
        if data_frequency == "d":
            dimension = daily_query
            frequency = "d"
        elif data_frequency == "5":
            dimension = min_query
            frequency = "5"

        data_list = []

        # 如果需要获取日交易数据，直接发送一个请求
        if data_frequency == "d":
            rs = bs.query_history_k_data_plus(
                code,
                dimension,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag="3",
            )

            if rs.error_code == "0":
                self.getdata_count = 0
                # 打印结果集
                while (rs.error_code == "0") & rs.next():
                    # 获取一条记录，将记录合并在一起
                    data_list.append(rs.get_row_data())
                # gl.logger.info(f"成功获取 {code} 从 {start_date} 至 {end_date} 的数据")
            elif rs.error_code == "10004011":
                return
            else:
                # 10001001
                self.getdata_count += 1
                gl.logger.debug(
                    f"Try Login to Get Data {self.getdata_count}/{self.getdata_max}"
                )
                gl.logger.error(
                    "query_history_k_data_plus respond error_code:" + rs.error_code
                )
                gl.logger.error(
                    "query_history_k_data_plus respond  error_msg:" + rs.error_msg
                )
                if self.getdata_count >= self.getdata_max:
                    self.getdata_count = 0
                else:
                    self.logout()
                    self.login()
                    return self.get_data(
                        code=code,
                        data_frequency=data_frequency,
                        start_date=start_date,
                        end_date=end_date,
                    )

            result = pd.DataFrame(data_list, columns=rs.fields)
            return result

        # 如果需要获取的是5min交易数据，分段获取
        if data_frequency == "5":
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            total_days = (end - start).days
            offset = 365 * 2

            for i in range(int(total_days / offset) + 1):
                start_temp = (start + datetime.timedelta(days=offset * i)).strftime(
                    "%Y-%m-%d"
                )
                if i == int(total_days / offset):
                    end_temp = end_date
                else:
                    end_temp = (
                        start + datetime.timedelta(days=offset * (i + 1))
                    ).strftime("%Y-%m-%d")
                # now = datetime.datetime.now().strftime("%H:%M:%S")

                rs = bs.query_history_k_data_plus(
                    code,
                    dimension,
                    start_date=start_temp,
                    end_date=end_temp,
                    frequency=frequency,
                    adjustflag="3",
                )
                if rs.error_code == "0":
                    # 打印结果集
                    self.getdata_count = 0
                    while (rs.error_code == "0") & rs.next():
                        # 获取一条记录，将记录合并在一起
                        data_list.append(rs.get_row_data())
                else:
                    # 10001001
                    self.getdata_count += 1
                    gl.logger.error(
                        "query_history_k_data_plus respond error_code:" + rs.error_code
                    )
                    gl.logger.error(
                        "query_history_k_data_plus respond  error_msg:" + rs.error_msg
                    )
                    gl.logger.debug(
                        f"Try Login GetDate{self.getdata_count}/{self.getdata_max}"
                    )
                    if self.getdata_count >= self.getdata_max:
                        self.getdata_count = 0
                        return
                    else:
                        self.logout()
                        self.login()
                        return self.get_data(
                            code=code,
                            data_frequency=data_frequency,
                            start_date=start_date,
                            end_date=end_date,
                        )
            result = pd.DataFrame(data_list, columns=rs.fields)
            return result

    # 获取一系列DataFrame的长度
    def count_data(self, data: pd.DataFrame) -> int:
        """
        获取一系列DataFrame的长度
        :param data: 传入DataFrame数据
        :return: 返回这个DataFrame的长度
        """
        count = data.count().date
        return count

    # 通过获取sh.000001的日交易数据来获取数据最新,目前往前推10天
    def get_baostock_last_date(self) -> str:
        """
        通过获取sh.000001的日交易数据来获取数据最新,目前往前推10天
        :return: 返回baostock的最新更新日期
        """
        gl.logger.debug("获取baostock最新更新日期")
        daily_query = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
        start_date = (
            datetime.datetime.now().date() + datetime.timedelta(days=-10)
        ).strftime("%Y-%m-%d")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        rs = bs.query_history_k_data_plus(
            "sh.000001",
            daily_query,
            start_date=start_date,
            end_date=today,
            frequency="d",
            adjustflag="3",
        )
        result = None
        if rs.error_code == "0":
            # 打印结果集
            self.getlastdate_count = 0
            data_list = []
            while (rs.error_code == "0") & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)
        else:
            # 10001001
            self.getlastdate_count += 1
            gl.logger.debug(f"Try Login To Get LastDate {self.getlastdate_count}/{5}")
            if self.getlastdate_count <= self.getlastdate_max:
                self.logout()
                self.login()
                return self.get_baostock_last_date()
            self.getlastdate_count = 0
        last_date = result.iloc[-1].date
        return last_date

    # 生成交易数据CSV文件
    def generate_data_csv(
        self, code: str = "sh.600000", data_frequency: str = "d", *, data_frame
    ):
        """
        abandon
        生成CSV文件
        :param code: 股票代码
        :param data_frequency: 数据频率'd' or '5'
        :param data_frame: 传入一个DataFrame数据
        :return:
        """
        path = self.set_path(data_frequency)
        if data_frame.count().date == 0:
            gl.logger.error("数据不能为空")
            min_ignore = self.read_min_ignore()
            if not self.is_code_in_min_ignore(code=code, min_ignore=min_ignore):
                self.add_to_min_ignore(code=code)
            return
        else:
            result = data_frame
            count = result.count().date
            if count < 10000:
                result.to_csv(path + code + ".csv", mode="w", index=False)
                last_date = self.get_last_date(
                    data_or_code=code, data_frequency=data_frequency
                )
                print(f"{code}.csv 已经生成，最新日期为 {last_date}")
                # self.sleep(3)
            else:
                result[:10000].to_csv(path + code + ".csv", mode="w", index=False)
                self.add_to_csv(
                    code=code, data_frequency=data_frequency, data_frame=result[10000:]
                )

    # # 向CSV中注入交易数据
    def add_to_csv(
        self, code: str = "sh.600000", data_frequency: str = "d", *, data_frame
    ):
        """
        abandon
        """
        path = self.set_path(data_frequency)
        count = data_frame.count().date
        if count == 0:
            print("数据不能为空")
            return
        elif count <= self.data_split:
            data_frame.to_csv(path + code + ".csv", mode="a", header=False, index=False)
            last = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
        else:
            for i in range(int(count / self.data_split) + 1):
                t = data_frame[self.data_split * i : (i + 1) * self.data_split]
                t.to_csv(path + code + ".csv", mode="a", header=False, index=False)
                last = self.get_last_date(
                    data_or_code=code, data_frequency=data_frequency
                )
        print(f"\n{code}.csv 已经更新至 {last}")
        self.sleep(1)

    # 获取所有股票代码
    def get_all_stock_code(self) -> pd.DataFrame:
        """
        获取所有股票代码
        :return:
        """
        # 获取证券信息
        date = bao_instance.get_baostock_last_date()
        rs = bs.query_all_stock(day=date)

        data_list = []
        while (rs.error_code == "0") & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        # 返回结果
        gl.logger.info(f"{date} 指数代码共有{result.shape[0]}条.")
        return result

    # 获取复权因子数据
    def get_adjust_factor(self, code: str) -> pd.DataFrame:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        rs_list = []
        # gl.logger.debug(f"尝试获取 {code} 复权因子数据。。。")
        rs_factor = bs.query_adjust_factor(
            code=code, start_date=self.init_date, end_date=today
        )
        while (rs_factor.error_code == "0") & rs_factor.next():
            rs_list.append(rs_factor.get_row_data())
        result_factor = pd.DataFrame(rs_list, columns=rs_factor.fields)
        # gl.logger.info(f"成功获取 {code} 复权因子数据 {len(rs_list)}条")
        return result_factor


bao_instance = BaoStockData()
