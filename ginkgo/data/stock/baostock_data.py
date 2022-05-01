# pylint: disable=no-member
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
        pass
        # self.__init_dir()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            with BaoStockData._instance_lock:
                if not hasattr(cls, "_instance"):
                    BaoStockData._instance = super().__new__(cls)

            return BaoStockData._instance

    # baostock 登录
    def login(self):
        """
        baostock 登录
        :return:
        """
        lg = bs.login(user_id="anonymous", password="123456")
        if not lg.error_code == "0":
            gl.logger.error("\rlogin respond error_code:" + lg.error_code)
            gl.logger.error("\rlogin respond  error_msg:" + lg.error_msg)
        else:
            pass
            # gl.logger.info("Baostock Login Success")

    # baostock 退出
    def logout(self):
        """
        baostock 退出
        :return:
        """
        bs.logout

    # 线程等待
    def sleep(self, sleep_second=2):
        """
        线程等待
        :param sleep_second: 等待的时间（秒）
        :return:
        """
        for i in range(sleep_second * 10):
            t = sleep_second * 10 - (i + 1)
            rate = (i + 1) / (sleep_second * 10)
            process_max = 30
            elapse = int(rate * process_max)
            time.sleep(0.1)

    # 从 baostock 获取数据
    def get_data(
        self,
        code="sh.600000",
        data_frequency="d",
        start_date=init_date,
        end_date="2006-02-01",
    ):
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
                # 打印结果集
                while (rs.error_code == "0") & rs.next():
                    # 获取一条记录，将记录合并在一起
                    data_list.append(rs.get_row_data())
                # gl.logger.info(f"成功获取 {code} 从 {start_date} 至 {end_date} 的数据")
            else:
                gl.logger.error(
                    "query_history_k_data_plus respond error_code:" + rs.error_code
                )
                gl.logger.error(
                    "query_history_k_data_plus respond  error_msg:" + rs.error_msg
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
                    while (rs.error_code == "0") & rs.next():
                        # 获取一条记录，将记录合并在一起
                        data_list.append(rs.get_row_data())
                else:
                    gl.logger.error(
                        "query_history_k_data_plus respond error_code:" + rs.error_code
                    )
                    gl.logger.error(
                        "query_history_k_data_plus respond  error_msg:" + rs.error_msg
                    )
            result = pd.DataFrame(data_list, columns=rs.fields)
            return result

    # 获取一系列DataFrame的长度
    def count_data(self, data):
        """
        获取一系列DataFrame的长度
        :param data: 传入DataFrame数据
        :return: 返回这个DataFrame的长度
        """
        count = data.count().date
        return count

    # # 获取DataFrame或者某只股票的最近更新日期，!!ABANDON!!
    # def get_last_date(self, data_or_code, data_frequency="d"):
    #     """
    #     获取DataFrame或者某只股票的最近更新日期
    #     :param data_or_code: 传入DataFrame数据 或者具体股票Code
    #     :param data_frequency: 数据频率'd' or '5'
    #     :return: 如果传入DataFrame数据则返回这个DataFrame的最新更新日期，如果传入具体股票Code则取查找本地存取的csv读取最近更新日期
    #     """
    #     if data_frequency == "d":
    #         path = "day/"
    #     elif data_frequency == "5":
    #         path = "min/"
    #     else:
    #         print("Frequency should be d or 5.")
    #         return
    #     if type(data_or_code) == pd.core.frame.DataFrame:
    #         last_date = data_or_code.iloc[-1].date
    #     elif type(data_or_code) == str:
    #         # 数据库查询
    #         date_data = pd.read_csv(
    #             STOCK_URL + path + data_or_code + ".csv", usecols=["date"]
    #         )
    #     if date_data.count().date == 0:
    #         print(f"{data_or_code}.csv 无数据")
    #         return 0
    #     else:
    #         last_date = date_data.iloc[-1].date
    #     return last_date

    # 通过获取sh.000001的日交易数据来获取数据最新,目前往前推10天
    def get_baostock_last_date(self):
        """
        通过获取sh.000001的日交易数据来获取数据最新,目前往前推10天
        :return: 返回baostock的最新更新日期
        """
        gl.logger.info("获取baostock最新更新日期")
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
            data_list = []
            while (rs.error_code == "0") & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)
        last_date = result.iloc[-1].date
        return last_date

    # 根据数据频率设定文件目录
    # def set_path(self, data_frequency):
    #     """
    #     根据数据频率设定文件目录
    #     :param data_frequency: 数据频率'd' or '5'
    #     :return: 返回路径
    #     """
    #     if data_frequency == "d":
    #         path = STOCK_URL + "day/"
    #     elif data_frequency == "5":
    #         path = STOCK_URL + "min/"
    #     else:
    #         print("Frequency should be d or 5.")
    #     return path

    # 生成交易数据CSV文件
    def generate_data_csv(self, code="sh.600000", data_frequency="d", *, data_frame):
        """
        生成CSV文件
        :param code: 股票代码
        :param data_frequency: 数据频率'd' or '5'
        :param data_frame: 传入一个DataFrame数据
        :return:
        """
        path = self.set_path(data_frequency)
        if data_frame.count().date == 0:
            print("数据不能为空")
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
    def add_to_csv(self, code="sh.600000", data_frequency="d", *, data_frame):
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

    # 生成分钟数据黑名单，把没有分钟数据的指数存入
    # def generate_min_ignore(self):
    #     """
    #     生成分钟数据黑名单，把没有分钟数据的指数存入
    #     :return:
    #     """
    #     t = {"code": []}
    #     df = pd.DataFrame(data=t, index=None)
    #     df.to_csv(STOCK_URL + "min_ignore.csv", mode="w", index=False, encoding="GBK")
    #     print(f"成功创建 min_ignore.csv")

    # 判断股票代码是否在分钟时间黑名单中
    def is_code_in_min_ignore(self, code, min_ignore):
        """
        判断股票代码是否在分钟时间黑名单中
        :param code: 股票代码
        :param min_ignore: 分钟数据黑名单DataFrame
        :return:
        """
        if min_ignore is None:
            return False
        ignore_list = min_ignore["code"].values.tolist()
        if code in ignore_list:
            return True
        else:
            return False

    # 将股票代码添加至分钟数据黑名单
    # def add_to_min_ignore(self, code):
    #     """
    #     将股票代码添加至分钟数据黑名单
    #     :param code: 股票指数代码
    #     :return:
    #     """
    #     try:
    #         t = {"code": [code]}
    #         df = pd.DataFrame(data=t, index=None)
    #         df.to_csv(
    #             STOCK_URL + "min_ignore.csv",
    #             mode="a",
    #             header=False,
    #             index=False,
    #             encoding="GBK",
    #         )
    #         print(f"已经添加 {code} 至 min_ignore.csv.")
    #     except Exception as e:
    #         print(e)
    #         self.generate_min_ignore()
    #         self.add_to_min_ignore(code=code)

    # 读取分钟数据黑名单
    # def read_min_ignore(self):
    #     """
    #     读取分钟数据黑名单
    #     :return:
    #     """
    #     try:
    #         ignore_df = pd.read_csv(STOCK_URL + "min_ignore.csv", usecols=["code"])
    #         return ignore_df
    #     except Exception as e:
    #         print(e)
    #         self.generate_min_ignore()
    #         self.read_min_ignore()

    # 更新一只股票数据
    def update_one_stock(self, code="sh.600000", data_frequency="d", end=""):
        """
        更新一只股票数据
        :param code: 股票代码
        :param data_frequency: 数据频率'd' or '5'
        :param end: 更新到的截至日期
        :return:
        """
        try:
            last_date = self.get_last_date(
                data_or_code=code, data_frequency=data_frequency
            )
            if end == "":
                end = self.get_baostock_last_date()
            if last_date == end:
                print(f"{code} 无需更新，最新日期为 {end}")
                return
            start = (
                datetime.datetime.strptime(last_date, "%Y-%m-%d").date()
                + datetime.timedelta(days=1)
            ).strftime("%Y-%m-%d")
            add_data = self.get_data(
                code=code, data_frequency=data_frequency, start_date=start, end_date=end
            )
            self.add_to_csv(
                code=code, data_frequency=data_frequency, data_frame=add_data
            )
        except Exception as e:
            print(e)
            print(f"没有找到 {code}.csv")
            start = self.init_date
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            add_data = self.get_data(
                code=code,
                data_frequency=data_frequency,
                start_date=start,
                end_date=today,
            )
            self.generate_data_csv(
                code=code, data_frequency=data_frequency, data_frame=add_data
            )

    # 获取所有股票代码
    def get_all_stock_code(self):
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
        self.logout()
        # 返回结果
        gl.logger.info(f"{date} 指数代码共有{result.shape[0]}条.")
        return result

    # 更新所有股票指数交易数据
    # def update_all_stock(self):
    #     """
    #     更新所有股票
    #     :return:
    #     """
    #     try:
    #         min_ignore = self.read_min_ignore()
    #         # self.login()
    #         code = pd.read_csv(STOCK_URL + "all_stock.csv", usecols=["code"])
    #         count = code.count().code
    #         end = self.get_baostock_last_date()
    #         if count == 0:
    #             print("指数代码为空，请检查代码")
    #             return
    #         else:
    #             begin = datetime.datetime.now()
    #             for row in code.iterrows():
    #                 self.up_to_date(code=row[1].code, data_frequency="d", end=end)
    #             print("日交易数据更新完毕")

    #             for row in code.iterrows():
    #                 if self.is_code_in_min_ignore(
    #                     code=row[1].code, min_ignore=min_ignore
    #                 ):
    #                     print(f"{row[1].code} 已被忽略")
    #                     continue
    #                 self.up_to_date(code=row[1].code, data_frequency="5", end=end)
    #             print("5 Min 交易数据更新完毕")
    #         self.logout()
    #         end = datetime.datetime.now()
    #         min_elapse = int((end - begin).seconds / 60)
    #         second_elapse = (end - begin).seconds - 60 * min_elapse
    #         print(f"更新完毕,共耗时 {min_elapse} 分 {second_elapse} 秒")
    #     except Exception as e:
    #         raise e

    # 获取复权因子数据
    def get_adjust_factor(self, code):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        rs_list = []
        # gl.logger.info(f'尝试获取 {code} 复权因子数据。。。')
        rs_factor = bs.query_adjust_factor(
            code=code, start_date=self.init_date, end_date=today
        )
        while (rs_factor.error_code == "0") & rs_factor.next():
            rs_list.append(rs_factor.get_row_data())
        result_factor = pd.DataFrame(rs_list, columns=rs_factor.fields)
        # gl.logger.info(f'成功获取 {code} 复权因子数据 {len(rs_list)}条')
        return result_factor

    # 生成复权因子数据CSV
    # def generate_adjust_factor(self, data_frame):
    #     data_frame.to_csv(
    #         STOCK_URL + "adjust_factor_data.csv", encoding="GBK", index=False, mode="w"
    #     )
    #     print("成功生成 adjust_factor.csv")

    # 更新复权因子数据
    # def add_to_adjust_factor(self, data_frame, code, adjust_factor):
    #     if not os.path.exists(".//" + STOCK_URL + "adjust_factor_data.csv"):
    #         print("文件不存在")
    #         self.generate_adjust_factor(data_frame)
    #     else:
    #         temp = data_frame.copy(deep=True)
    #         temp_list = []
    #         for i in range(temp.count().code):
    #             if self.is_adjust_in_csv(temp.iloc[i], adjust_factor=adjust_factor):
    #                 temp_list.append(i)
    #         result = temp.drop(index=temp_list)
    #         if result.count().code == 0:
    #             _output.write(f"\r{code} 复权因子数据已经存在")
    #         else:
    #             result.to_csv(
    #                 STOCK_URL + "adjust_factor_data.csv",
    #                 mode="a",
    #                 header=False,
    #                 index=False,
    #             )
    #             _output.write(f"\r{code} 复权因子数据已经更新")

    # 判断某一行DataFrame是否在adjust_factor_data.csv中
    def is_adjust_in_csv(self, data_frame, adjust_factor):
        filter = adjust_factor.loc[
            (adjust_factor.code == data_frame.code)
            & (adjust_factor.dividOperateDate == data_frame.dividOperateDate)
        ]
        count = filter.count().dividOperateDate
        if count == 1:
            return True
        elif count == 0:
            return False
        else:
            print("复权因子数据重复，请复核")  # TODO 复权因子重复的话去重
            return True

    # 更新某一个股票的复权因子数据
    def adjust_factor_up_to_date(self, code, adjust_factor):
        result = self.get_adjust_factor(code)
        if result.count().code == 0:
            _output.write(f"\r{code} 无复权因子数据")
            return
        else:
            self.add_to_adjust_factor(
                data_frame=result, code=code, adjust_factor=adjust_factor
            )

    # 更新所有股票指数复权因子
    # def all_adjust_factor_up_to_date(self):
    #     code = pd.read_csv(STOCK_URL + "all_stock.csv", usecols=["code"])
    #     count = code.count().code
    #     if count == 0:
    #         print("指数代码为空，请检查代码")
    #         return
    #     else:
    #         print("开始更新复权因子数据。。。")
    #         self.login()
    #         rs_list = []
    #         rs_factor = bs.query_adjust_factor(
    #             code="sh.600000", start_date=self.init_date, end_date="2017-12-31"
    #         )
    #         while (rs_factor.error_code == "0") & rs_factor.next():
    #             rs_list.append(rs_factor.get_row_data())
    #         result_factor = pd.DataFrame(rs_list, columns=rs_factor.fields)
    #         if not os.path.exists(".//" + STOCK_URL + "adjust_factor_data.csv"):
    #             print("没有找到 adjust_factor_data.csv")
    #             self.generate_adjust_factor(result_factor)
    #         adjust = pd.read_csv(STOCK_URL + "adjust_factor_data.csv")
    #         begin = datetime.datetime.now()

    #         for row in code.iterrows():
    #             self.adjust_factor_up_to_date(code=row[1].code, adjust_factor=adjust)
    #         end = datetime.datetime.now()
    #         min_elapse = int((end - begin).seconds / 60)
    #         second_elapse = (end - begin).seconds - 60 * min_elapse
    #         print(f"复权因子数据数据更新完毕,共耗时 {min_elapse} 分 {second_elapse} 秒")
    #         self.logout()


bao_instance = BaoStockData()
