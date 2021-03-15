"""
数据的存储模块，负责与mongoDB的通信以及本地缓存的处理
"""
import time
import pymongo
import datetime
import queue
import pandas as pd
import numpy as np
import tqdm
import math
import threading
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.data.bitcoin.coin_cap import coin_cap_instance
from ginkgo_server.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.libs.thread_manager import thread_manager as tm


# 5分钟交易数据后缀
min5_postfix = ".min5"


class GinkgoMongo(object):
    def __init__(self, host, port, username, pwd, database):
        self.client = None
        self.db = None
        self.host = host
        self.port = port
        self.username = username
        self.pwd = pwd
        self.database = database

        self.__connect()

    def __connect(self):
        """
        建立mongo连接
        TODO 连接失败的操作：提示安装mongo，配置端口，自动安装mongo？
        """
        # 建立客户端连接
        self.client = pymongo.MongoClient(host=self.host, port=self.port)
        # 切换数据库
        self.db = self.client[self.database]
        # 授权
        self.db.authenticate(self.username, self.pwd, mechanism="SCRAM-SHA-1")

    def __adjust_cal(self, raw, adjust_factor, adjust_flag=1, frequency="d"):
        """
        复权计算

        :param raw: 原始交易数据
        :type raw: DataFrame
        :param adjust_factor: 复权因子
        :type adjust_factor: DataFrame
        :param adjust_flag: 复权方式, defaults to 1
        :type adjust_flag: int, optional
        :param frequency: 频率, defaults to 'd'
        :type frequency: str, optional
        :return: 复权后的交易数据
        :rtype: DataFrame
        """
        # 没有复权因子
        if adjust_factor.shape[0] == 0:
            return raw

        # 有复权因子
        # TODO 按照截至日期复权
        adjust_columns = []
        if frequency == "d":
            adjust_columns = ["open", "high", "low", "close", "pre_close"]
        elif frequency == "5":
            adjust_columns = ["open", "high", "low", "close"]

        for i in adjust_columns:
            raw[i] = raw[i].astype(np.float)
        for i in ["adjust_factor", "back_adjust_factor", "fore_adjust_factor"]:
            adjust_factor[i] = adjust_factor[i].astype(np.float)
        fore = raw.copy(deep=True)
        back = raw.copy(deep=True)
        for i in range(adjust_factor.shape[0] + 1):
            if i == 0:
                condition = raw["date"] < adjust_factor.iloc[0].divid_operate_date
                condition2 = raw["date"] <= adjust_factor.iloc[0].divid_operate_date

                fore.loc[condition, adjust_columns] *= adjust_factor.iloc[
                    0
                ].fore_adjust_factor
                back.loc[condition2, adjust_columns] *= adjust_factor.iloc[
                    0
                ].back_adjust_factor

            elif i == len(adjust_factor):
                condition = (
                    raw["date"] >= adjust_factor.iloc[i - 1]["divid_operate_date"]
                )
                condition2 = (
                    raw["date"] > adjust_factor.iloc[i - 1]["divid_operate_date"]
                )
                fore.loc[condition, adjust_columns] *= adjust_factor.iloc[i - 1][
                    "fore_adjust_factor"
                ]
                back.loc[condition2, adjust_columns] *= adjust_factor.iloc[i - 1][
                    "back_adjust_factor"
                ]
            else:
                condition = (
                    raw["date"] < adjust_factor.iloc[i]["divid_operate_date"]
                ) & (raw["date"] >= adjust_factor.iloc[i - 1]["divid_operate_date"])
                condition2 = (
                    raw["date"] <= adjust_factor.iloc[i]["divid_operate_date"]
                ) & (raw["date"] > adjust_factor.iloc[i - 1]["divid_operate_date"])
                fore.loc[condition, adjust_columns] *= adjust_factor.iloc[i][
                    "fore_adjust_factor"
                ]
                back.loc[condition2, adjust_columns] *= adjust_factor.iloc[i][
                    "back_adjust_factor"
                ]

        if adjust_flag == 1:
            return fore
        elif adjust_flag == 2:
            return back
        else:
            return raw

    # 更新所有股票指数基本信息
    def update_stockinfo(self):
        """
        更新所有指数代码基本信息,包括指数指数代码、指数名称、交易状态
        """
        gl.info("StockInfo更新初始化.")
        slice_count = 1000
        gl.info(f"存储切片设置为 {slice_count}")
        # Step1：通过Baostock获取所有指数代码
        bao_instance.login()
        result = bao_instance.get_all_stock_code()

        # Step2：如果数据不为空进行持久化操作，反之报错
        if result.shape[0] > 0:
            col = self.db["stock_info"]

            operations = []
            pbar = tqdm.tqdm(total=result.shape[0])
            for i in range(result.shape[0]):
                operations.append(
                    pymongo.UpdateOne(
                        {"code": result.iloc[i].code},
                        {
                            "$set": {
                                "code_name": result.iloc[i].code_name,
                                "trade_status": result.iloc[i].tradeStatus,
                            }
                        },
                        upsert=True,
                    )
                )
                pbar.update(1)
                pbar.set_description(f"添加 {result.iloc[i].code} 操作")
                if len(operations) == slice_count:
                    col.bulk_write(operations, ordered=False)
                    operations = []
            if len(operations) > 0:
                col.bulk_write(operations, ordered=False)
            pbar.set_description("完成 StockInfo 更新")
            # TODO 根据插入结果进行相应处理
            pbar.set_description("StockInfo 索引更新")
            col.create_index([("code", 1)], unique=True)
            pbar.set_description("StockInfo 更新完成")
        else:
            gl.error("股票指数代码获取为空，请检查代码或日期")

        gl.info("StockInfo更新完成.")

    # 从mongo中获取所有股票代码
    def get_all_stockcode_by_mongo(self):
        """
        从本地mongo中获得所有股票代码

        :return: [所有StockCode组成的df]
        :rtype: [DataFrame]
        """
        col = self.db["stock_info"]
        rs = col.find()
        df = pd.DataFrame(rs)
        return df

    # 更新插入复权数据
    def upsert_adjustfactor(self, data_frame: pd.DataFrame):
        """
        与mongo交互，更新插入复权信息

        :param data_frame: [description]
        :type data_frame: DataFrame
        """
        col = self.db["adjust_factor"]

        operations = []
        pbar = tqdm.tqdm(total=data_frame.shape[0])
        for i in range(data_frame.shape[0]):
            operations.append(
                pymongo.UpdateOne(
                    {
                        "code": data_frame.iloc[i].code,
                        "divid_operate_date": data_frame.iloc[i].dividOperateDate,
                    },
                    {
                        "$set": {
                            "fore_adjust_factor": data_frame.iloc[i].foreAdjustFactor,
                            "back_adjust_factor": data_frame.iloc[i].backAdjustFactor,
                            "adjust_factor": data_frame.iloc[i].adjustFactor,
                        }
                    },
                    upsert=True,
                )
            )
            pbar.set_description(
                f"{data_frame.iloc[i].code} {data_frame.iloc[i].dividOperateDate}"
            )
            pbar.update(1)
        rs = col.bulk_write(operations)
        # TODO 根据批量差距结果执行后续操作
        # 建立索引
        col.create_index([("code", 1), ("divid_operate_date", 1)])

    # 异步更新插入复权数据
    def upsert_adjustfactor_async(self, data_frame: pd.DataFrame, thread_num=2):
        """
        异步更新插入复权信息

        :param data_frame: 需要更新插入的复权信息数据
        :type data_frame: pd.DataFrame
        :param thread_num: 最大线程数, defaults to 2
        :type thread_num: int, optional
        """
        slice_count = 20000
        pieces_count = math.ceil(data_frame.shape[0] / slice_count)
        threads = []
        for i in range(pieces_count):
            gl.info(f"创建UpsertAF {i}")
            sliced_stock_list = data_frame[slice_count * i : slice_count * (i + 1)]
            thread = threading.Thread(
                name=f"AdjustFactor {slice_count*i}-{slice_count*(i+1)}",
                target=self.upsert_adjustfactor,
                args=(sliced_stock_list,),
            )
            threads.append(thread)
        tm.limit_thread_register(threads=threads, thread_num=thread_num)

    # 更新所有复权因子
    def update_adjustfactor(self):
        """
        全量更新复权因子
        """
        gl.info("AdjustFactor更新初始化.")
        # 获取所有代码
        df_stock_list = self.get_all_stockcode_by_mongo()

        if df_stock_list.shape[0] == 0:
            gl.error("StockInfo为空")
            return

        # 生成待插入df
        insert_list = pd.DataFrame(
            columns=[
                "code",
                "dividOperateDate",
                "foreAdjustFactor",
                "backAdjustFactor",
                "adjustFactor",
            ]
        )
        stock_count = df_stock_list.shape[0]
        bao_instance.login()
        pbar = tqdm.tqdm(total=stock_count)

        for i in range(stock_count):
            pbar.set_description(f"获取{df_stock_list.iloc[i].code}复权数据")
            result = bao_instance.get_adjust_factor(code=df_stock_list.iloc[i].code)
            if result.shape[0] > 0:
                insert_list = pd.concat([insert_list, result], join="inner")
            pbar.update(1)
        if insert_list.shape[0] > 0:
            # 执行批量插入操作
            self.upsert_adjustfactor_async(data_frame=insert_list, thread_num=4)
        else:
            gl.error("共获取AdjustFactor 0 条, 请检查代码")

    # 插入日交易数据
    def insert_daybar(self, code: str, data_frame: pd.DataFrame):
        """
        插入日交易数据

        :param code: 股票代码
        :type code: str
        :param data_frame: 日交易数据
        :type data_frame: DataFrame
        """
        # 如果传入的DF为空，直接返回
        if data_frame.shape[0] == 0:
            return
        # 去重
        df = data_frame.drop_duplicates(subset=["date"], keep="first")
        # 修改列名
        df.rename(
            columns={
                "adjustflag": "adjust_flag",
                "preclose": "pre_close",
                "pctChg": "pct_change",
                "tradestatus": "trade_status",
                "isST": "is_st",
            },
            inplace=True,
        )
        # 切换collection
        col = self.db[code]
        # dataframe转换为dict，可供pymongo批量插入
        data = df.to_dict("record")
        # 批量插入
        col.insert_many(data)
        # 建立索引
        col.create_index([("date", 1)], unique=True)

    # 更新日交易数据
    def update_daybar(self, code: str, df_new: pd.DataFrame):
        """
        更新某只股票的日交易数据

        从mongo中获取某只Code的历史日交易数据，待插入数据进行比对后，插入不重复的数据

        :param code: 股票代码
        :type code: str
        :param df_new: 待插入的日交易数据
        :type df_new: DataFrame
        """
        df_old = self.get_dayBar_by_mongo(code=code)
        df_insert = self.get_df_norepeat(index_col="date", df_old=df_old, df_new=df_new)
        self.insert_daybar(code=code, data_frame=df_insert)

    # 获取日交易数据，并存入队列
    def get_daybar_by_baostock(
        self, code: str, start_date: str, end_date: str, data_queue: queue.Queue
    ):
        """
        获取日交易数据，并存入data_queue的队列里

        :param code: 股票代码
        :type code: str
        :param start_date: 起始日期
        :type start_date: str
        :param end_date: 终止日期
        :type end_date: str
        :param data_queue: 存放日交易数据的队列，由更新函数传递
        :type data_queue: queue.Queue
        """
        rs = bao_instance.get_data(
            code=code,
            data_frequency="d",
            start_date=start_date,
            end_date=end_date,
        )
        # 推入data_queue中
        if rs.shape[0] > 0:
            data_queue.put({code: rs})

    # 异步更新日交易数据
    def update_daybar_async(self, data_pool_size=10, thread_num=4):
        """
        异步更新日交易数据

        :param data_pool_size: [description], defaults to 10
        :type data_pool_size: int, optional
        :param thread_num: [description], defaults to 4
        :type thread_num: int, optional
        """
        # 获取日交易数据队列
        gl.info("日交易数据更新初始化.")
        data_queue = queue.Queue()
        get_thread_dict = dict()
        set_thread_dict = dict()
        heartbeat = 0.01
        stock_queue = queue.Queue()
        stock_df = self.get_all_stockcode_by_mongo()

        # stock_df = stock_df[4700:]

        bao_instance.login()
        end = bao_instance.get_baostock_last_date()
        gl.info(f"目标更新日期为{end}")

        if stock_df.shape[0] == 0:
            gl.error("股票代码为空，请检查代码")
            return
        for i in range(stock_df.shape[0]):
            stock_queue.put(stock_df.iloc[i].code)
        gl.info("更新队列准备完毕")

        pbar_get = tqdm.tqdm(total=stock_queue.qsize())
        pbar_set = tqdm.tqdm(total=stock_queue.qsize())

        while True:
            # 如果stock_queue
            if (
                stock_queue.qsize() == 0
                and data_queue.qsize() == 0
                and len(get_thread_dict) == 0
                and len(set_thread_dict) == 0
            ):
                gl.info("日交易数据更新完毕")
                return

            if (
                data_queue.qsize() < data_pool_size
                and len(get_thread_dict) == 0
                and stock_queue.qsize() > 0
            ):
                # 从stock_queue 中获取一个代码
                code = stock_queue.get()
                # 获取数据
                # 获取当前最新的数据日期
                try:
                    # 尝试从mongoDB查询该指数的最新数据
                    last_date = self.get_daybar_latestDate_by_mongo(code=code)
                except Exception as e:
                    # 失败则把开始日期设置为初识日期
                    last_date = bao_instance.init_date

                if end == last_date:
                    pbar_get.set_description(
                        f"{code}无新数据,{len(get_thread_dict)}/{data_pool_size}"
                    )
                    pbar_set.set_description(
                        f"{code}无新数据,{len(set_thread_dict)}/{thread_num}"
                    )
                    pbar_get.update(1)
                    pbar_set.update(1)
                else:
                    thread = threading.Thread(
                        name=f"Day {code} Get",
                        target=self.get_daybar_by_baostock,
                        args=(
                            code,
                            last_date,
                            end,
                            data_queue,
                        ),
                    )
                    # 线程注册
                    get_thread_dict[thread.name] = thread
                    # 线程添加至insert_thread_list
                    tm.thread_register(thread=thread)
                    pbar_get.set_description(
                        f"获取 {code} {len(get_thread_dict)}/{data_pool_size}"
                    )

            if len(set_thread_dict) < thread_num and data_queue.qsize() > 0:
                # 从 data_queue 中获取一个对象
                data = data_queue.get(block=True, timeout=None)
                # 创建一个数据插入的线程
                code = list(data.keys())[0]
                df = data[code]
                thread = threading.Thread(
                    name=f"Day {code} update",
                    target=self.update_daybar,
                    args=(
                        code,
                        df,
                    ),
                )
                # 线程注册
                set_thread_dict[thread.name] = thread
                # 线程添加至insert_thread_list
                tm.thread_register(thread=thread)
                pbar_set.set_description(
                    f"存储 {code} {len(set_thread_dict)}/{thread_num}"
                )
            # 清理僵尸线程
            dead_list1 = []
            for p in set_thread_dict:
                if not set_thread_dict[p].is_alive():
                    dead_list1.append(p)
            for d in dead_list1:
                set_thread_dict.pop(d)
                pbar_set.update(1)

            dead_list2 = []
            for p in get_thread_dict:
                if not get_thread_dict[p].is_alive():
                    dead_list2.append(p)
            for d in dead_list2:
                get_thread_dict.pop(d)
                pbar_get.update(1)
            tm.kill_dead_thread()
            # 心跳
            time.sleep(heartbeat)

    # 批量插入5Min交易数据
    def insert_min5(self, code: str, data_frame: pd.DataFrame):
        """
        批量插入5Min交易数据

        :param code: 股票代码
        :type code: str
        :param data_frame: Min5交易数据
        :type data_frame: pd.DataFrame
        """
        # 存储5min档交易数据
        # 如果传入的DF为空，直接返回
        if data_frame.shape[0] == 0:
            return
        df = data_frame.drop_duplicates(subset=["time"], keep="first")
        df.rename(
            columns={"adjustflag": "adjust_flag"},
            inplace=True,
        )
        col = self.db[code + min5_postfix]
        data = df.to_dict("record")
        col.insert_many(data)
        col.create_index([("time", 1)], unique=True)

    # 从Baostock获取Min5数据，存入dataQueue中
    def get_min5_async_by_baostock(
        self, code: str, start_date: str, end_date: str, data_queue: queue.Queue
    ):
        """
        从Baostock获取Min5数据，存入dataQueue中

        :param code: 股票代码
        :type code: str
        :param start_date: 开始日期
        :type start_date: str
        :param end_date: 结束日期
        :type end_date: str
        :param data_queue: 待存入的数据队列
        :type data_queue: queue.Queue
        """
        rs = bao_instance.get_data(
            code=code,
            data_frequency="5",
            start_date=start_date,
            end_date=end_date,
        )
        # 插入data_queue中
        if rs.shape[0] > 0:
            data_queue.put({code: rs})
        else:
            self.set_nomin5(code=code)

    # 更新某只Code的5min挡位分钟交易数据
    def update_min5(self, code: str, df_new: pd.DataFrame):
        """
        更新某只Code的5min挡位分钟交易数据

        :param code: 股票代码
        :type code: str
        :param df_new: 待插入的Min5数据
        :type df_new: pd.DataFrame
        """
        df_old = self.get_min5_by_mongo(code=code)
        df_insert = self.get_df_norepeat(index_col="time", df_old=df_old, df_new=df_new)
        self.insert_min5(code=code, data_frame=df_insert)

    # 异步更新Min5交易数据
    def update_min5_async(self, data_pool_size=4, thread_num=2):
        """
        异步全量更新Min5交易数据

        :param data_pool_size: 数据缓存池上限, defaults to 4
        :type data_pool_size: int, optional
        :param thread_num: 存储线程上限, defaults to 2
        :type thread_num: int, optional
        """
        gl.info("Min5数据更新初始化.")
        data_queue = queue.Queue()
        get_thread_dict = dict()
        set_thread_dict = dict()
        heartbeat = 0.1
        stock_queue = queue.Queue()
        stock_df = self.get_all_stockcode_by_mongo()

        bao_instance.login()
        end = bao_instance.get_baostock_last_date()
        gl.info(f"目标更新日期为{end}")

        if stock_df.shape[0] == 0:
            gl.error("股票代码为空，请检查代码")
            return
        for i in range(stock_df.shape[0]):
            if self.check_stock_min5(code=stock_df.iloc[i].code):
                stock_queue.put(stock_df.iloc[i].code)
        gl.info("更新队列准备完毕")
        pbar_get = tqdm.tqdm(total=stock_queue.qsize())
        pbar_set = tqdm.tqdm(total=stock_queue.qsize())

        while True:
            # 如果stock_queue
            if (
                stock_queue.qsize() == 0
                and data_queue.qsize() == 0
                and len(get_thread_dict) == 0
                and len(set_thread_dict) == 0
            ):
                gl.info("Min5 交易数据更新完毕")
                return

            if (
                data_queue.qsize() < data_pool_size
                and len(get_thread_dict) == 0
                and stock_queue.qsize() > 0
            ):
                # 从stock_queue 中获取一个代码
                code = stock_queue.get()
                # 获取数据
                # 获取当前最新的数据日期
                try:
                    # 尝试从mongoDB查询该指数的最新数据
                    last_date = self.get_min5_latestDate_by_mongo(code=code)
                except Exception as e:
                    # 失败则把开始日期设置为初识日期
                    last_date = bao_instance.init_date

                if end == last_date:
                    pbar_get.set_description(
                        f"{code}无新数据,{len(get_thread_dict)}/{data_pool_size}"
                    )
                    pbar_set.set_description(
                        f"{code}无新数据,{len(set_thread_dict)}/{thread_num}"
                    )
                    pbar_get.update(1)
                    pbar_set.update(1)
                else:
                    thread = threading.Thread(
                        name=f"Min5 {code} Get",
                        target=self.get_min5_async_by_baostock,
                        args=(
                            code,
                            last_date,
                            end,
                            data_queue,
                        ),
                    )

                    # 线程注册
                    get_thread_dict[thread.name] = thread
                    # 线程添加至insert_thread_list
                    tm.thread_register(thread=thread)
                    pbar_get.set_description(
                        f"获取 {code} {len(get_thread_dict)}/{data_pool_size}"
                    )

            if len(set_thread_dict) < thread_num and data_queue.qsize() > 0:
                # 从 data_queue 中获取一个对象
                data = data_queue.get(block=True, timeout=None)
                # 创建一个数据插入的线程
                code = list(data.keys())[0]
                df = data[code]
                thread = threading.Thread(
                    name=f"Min5 {code} update",
                    target=self.update_min5,
                    args=(
                        code,
                        df,
                    ),
                )

                # 线程注册
                set_thread_dict[thread.name] = thread
                # 线程添加至insert_thread_list
                tm.thread_register(thread=thread)
                pbar_set.set_description(
                    f"存储 {code} {len(set_thread_dict)}/{thread_num}"
                )
            # 清理僵尸线程
            dead_list1 = []
            for p in set_thread_dict:
                if not set_thread_dict[p].is_alive():
                    dead_list1.append(p)
            for d in dead_list1:
                set_thread_dict.pop(d)
                pbar_set.update(1)

            dead_list2 = []
            for p in get_thread_dict:
                if not get_thread_dict[p].is_alive():
                    dead_list2.append(p)
            for d in dead_list2:
                get_thread_dict.pop(d)
                pbar_get.update(1)
            tm.kill_dead_thread()
            # 心跳
            time.sleep(heartbeat)

    # 获取日交易数据
    def get_dayBar_by_mongo(self, code: str, start_date="", end_date=""):
        """
        获取日交易数据，不传入日期范围则返回全量数据

        :param code: 股票代码
        :type code: str
        :param start_date: 起始日期
        :type start_date: str
        :param end_date: 结束日期
        :type end_date: str
        :return: code股票start_date至end_date的日交易数据
        :rtype: DataFrame
        """
        if start_date == "":
            start_date = bao_instance.init_date
        if end_date == "":
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        col = self.db[code]
        rs = col.find()
        df = pd.DataFrame(list(rs))
        if df.shape[0] > 0:
            condition1 = df["date"] >= start_date
            condition2 = df["date"] <= end_date
            df = df[condition1 & condition2]
            df = df.sort_values(by=["date"], ascending=[True])
        return df

    # 获取分钟交易数据
    def get_min5_by_mongo(self, code: str, start_date="", end_date=""):
        """
        获取分钟交易数据，不传入日期范围则返回全量数据

        :param code: 股票代码
        :type code: str
        :param start_date: 起始日期, defaults to ''
        :type start_date: str, optional
        :param end_date: 终止日期, defaults to ''
        :type end_date: str, optional
        :return: Min5交易数据
        :rtype: DataFrame
        """
        if start_date == "":
            start_date = bao_instance.init_date
        if end_date == "":
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        col = self.db[code + min5_postfix]
        result = col.find()
        df = pd.DataFrame(list(result))
        if df.shape[0] > 0:
            condition1 = df["date"] >= start_date
            condition2 = df["date"] <= end_date
            df = df[condition1 & condition2]
            df = df.sort_values(by=["date"], ascending=[True])
        return df

    # 获取复权数据
    def get_adjustfactor_by_mongo(self, code: str, start_date="", end_date=""):
        """
        获取复权数据，不传入日期范围则返回全量数据

        :param code: 股票代码
        :type code: str
        :param start_date: 起始日期, defaults to ""
        :type start_date: str, optional
        :param end_date: 截至日期, defaults to ""
        :type end_date: str, optional
        :return: 复权数据
        :rtype: DataFrame
        """
        if start_date == "":
            start_date = bao_instance.init_date
        if end_date == "":
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        col = self.db["adjust_factor"]
        result = col.find(
            {"code": code},
            {
                "_id": 0,
                "code": 1,
                "divid_operate_date": 1,
                "adjust_factor": 1,
                "back_adjust_factor": 1,
                "fore_adjust_factor": 1,
            },
        )
        df = pd.DataFrame(list(result))
        # 按日期排序
        try:
            condition1 = df["divid_operate_date"] >= start_date
            condition2 = df["divid_operate_date"] <= end_date
            df = df[condition1 & condition2]
            df = df.sort_values(by=["divid_operate_date"], ascending=[True])
        except Exception as e:
            print(e)
            pass

        return df

    # 获取某只股票日交易数据的最新日期
    def get_daybar_latestDate_by_mongo(self, code: str):
        col = self.db[code]
        result = col.find().sort("date", pymongo.DESCENDING).limit(1)
        last_date = result[0]["date"]
        return last_date

    # 获取某股票min5数据的最新时间戳
    def get_min5_latestDate_by_mongo(self, code: str):
        col = self.db[code + min5_postfix]
        s = col.find().sort("date", pymongo.DESCENDING).limit(1)
        last_time = s[0]["date"]
        return last_time

    def is_code_in_min_ignore(self, code: str):
        pass

    def add_to_min_ignore(self, code: str):
        pass

    def print_dead_stock(self):
        bao_instance.login()
        rs1 = bao_instance.get_all_stock_code()
        code_list1 = []
        code_list2 = []
        for i in range(rs1.shape[0]):
            t = rs1.iloc[i].code
            code_list1.append(t)
        rs2 = self.get_all_stockcode_by_mongo()
        for i in range(rs2.shape[0]):
            t = rs2.iloc[i].code
            code_list2.append(t)

        print(len(code_list1))
        print(len(code_list2))
        for i in code_list2:
            if i not in code_list1:
                print(i)

    def set_nomin5(self, code: str):
        col = self.db["stock_info"]
        col.update_one({"code": code}, {"$set": {"has_min5": False}})

    def check_stock_min5(self, code: str):
        col = self.db["stock_info"]
        stock_info = col.find({"code": code})
        if stock_info.count() != 1:
            gl.error(f"{code}不存在")
            return False
        else:
            try:
                result = stock_info[0]["has_min5"]
                return result
            except Exception as e:
                return True

    def get_df_norepeat(self, index_col, df_old, df_new):
        if df_old.shape[0] == 0:
            return df_new
        df_duplicate = df_new[df_new[index_col].isin(df_old[index_col])]
        df_return = df_new.append(df_duplicate).drop_duplicates(
            subset=[index_col], keep=False
        )
        try:
            df_return = df_return.drop(["_id"], axis=1)
        except Exception as e:
            pass
        return df_return

    def check_code_exist(self, code):
        # 查询all_stock.csv中是否存在与code匹配
        try:
            code_df = self.get_all_stockcode_by_mongo()
            count = code_df.count().code
            if count == 0:
                print("指数代码为空，请检查代码")
                return False
            else:
                is_code_in_list = code in code_df["code"].values
                return is_code_in_list
        except Exception as e:
            raise e

    def query_stock(self, code, start_date, end_date, frequency, adjust_flag=3):
        # 如果code不存在列表内，直接返回
        if not self.check_code_exist(code=code):
            print("股票代码不存在股票列表内")
            return
        else:
            # 获取股票原始数据
            if frequency == "d":
                raw = self.get_dayBar_by_mongo(code=code)
            elif frequency == "5":
                raw = self.get_min5_by_mongo(code=code)

            # 获取复权因子数据
            adjust_factor = self.get_adjustfactor_by_mongo(code=code)
            # 复权计算
            adjust = self.__adjust_cal(
                raw=raw,
                adjust_factor=adjust_factor,
                adjust_flag=adjust_flag,
                frequency=frequency,
            )
            # 根据start_date与end_date返回数据
            if start_date > end_date:
                print("start should before end")
                return
            condition = adjust["date"] >= start_date
            condition2 = adjust["date"] <= end_date
            result = adjust[condition & condition2].replace("", 0)
            return result

    def update_coin_info(self):
        rs = coin_cap_instance.get_coin_list()
        # 存储到MongoDB

    def update_all(self):
        self.update_stockinfo()
        self.update_adjustfactor()
        self.update_daybar_async(thread_num=4)
        self.update_min5_async(thread_num=2)
        # TODO 加入虚拟货币的更新


ginkgo_mongo = GinkgoMongo(
    host=HOST, port=PORT, username=USERNAME, pwd=PASSWORD, database=DATABASE
)
