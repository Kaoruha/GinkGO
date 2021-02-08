"""
数据的存储模块，负责与MongoDB的通信以及本地缓存的处理
"""

import pymongo
import time
import datetime
import queue
import pandas as pd
import tqdm
import math
import threading
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD
from ginkgo_server.data.storage import ginkgo_storage as gs
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.libs.thread_manager import thread_manager as tm
from ginkgo_server.data.models.stock_info import StockInfo
from ginkgo_server.data.models.adjust_factor import AdjustFactor
from ginkgo_server.data.models.day_bar import DayBar
from ginkgo_server.data.models.min5_bar import Min5Bar


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
        # 建立客户端连接
        self.client = pymongo.MongoClient(host=self.host, port=self.port)
        # 切换数据库
        self.db = self.client[self.database]
        # 授权
        self.db.authenticate(self.username, self.pwd, mechanism="SCRAM-SHA-1")

    # 更新所有股票指数基本信息
    def update_stock_info(self):
        """
        更新所有指数代码基本信息,包括指数指数代码、指数名称、交易状态
        """
        slice_count = 1000
        # Step1：通过Baostock获取所有指数代码
        bao_instance.login()
        result = bao_instance.get_all_stock_code()
        # result = result[:10000]

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

    # 从Mongo中获取所有股票代码
    def get_all_stock_code(self):
        col = self.db["stock_info"]
        rs = col.find()
        df = pd.DataFrame(rs)
        return df

    # 更新所有复权因子
    def update_adjust_factor(self):
        df_stock_list = self.get_all_stock_code()
        # df_stock_list = df_stock_list[:400]
        if df_stock_list.shape[0] == 0:
            gl.error("StockInfo为空")
            return

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
            rs = bao_instance.get_adjust_factor(code=df_stock_list.iloc[i].code)
            if rs.shape[0] > 0:
                insert_list = pd.concat([insert_list, rs], join="inner")
            pbar.update(1)
        if insert_list.shape[0] > 0:
            # 执行批量插入操作
            self.upsert_adjust_factor_async(data_frame=insert_list, thread_num=4)
        else:
            gl.error("共获取AdjustFactor 0 条, 请检查代码")

    # 插入日交易数据
    def insert_day_bar(self, code: str, data_frame: pd.DataFrame):
        """
        批量更新某只股票的日交易数据

        :param code: 股票代码
        :type code: str
        :param data_frame: [description]
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
        col = self.db[code]
        data = df.to_dict("record")
        col.insert_many(data)
        col.create_index([("date", 1)], unique=True)

    # 更新日交易数据
    def update_day_bar(self, code: str, df_new):
        df_old = self.get_day_bar(code=code)
        df_insert = self.get_df_norepeat(index_col="date", df_old=df_old, df_new=df_new)
        self.insert_day_bar(code=code, data_frame=df_insert)

    # 异步更新日交易数据
    def update_day_bar_async(self, data_pool_size=12, thread_num=4):
        # 获取日交易数据队列
        gl.info("初始化.")
        data_queue = queue.Queue()
        thread_dict = dict()
        heartbeat = 0.1
        stock_queue = queue.Queue()
        stock_df = self.get_all_stock_code()

        bao_instance.login()
        end = bao_instance.get_baostock_last_date()
        gl.info(f"目标更新日期为{end}")

        if stock_df.shape[0] == 0:
            gl.error("股票代码为空，请检查代码")
            return
        for i in range(stock_df.shape[0]):
            stock_queue.put(stock_df.iloc[i].code)
        gl.info("更新队列准备完毕")
        pbar_get = tqdm.tqdm(range(stock_queue.qsize()))
        pbar_get.set_description("数据更新")
        pbar_set = tqdm.tqdm(range(stock_queue.qsize()))
        pbar_set.set_description("数据存储")

        while True:
            # 如果stock_queue
            if (
                stock_queue.qsize() == 0
                and data_queue.qsize() == 0
                and len(thread_dict) == 0
            ):
                gl.info("日交易数据更新完毕")
                return

            # 当数据队列尺寸小于设置的数据池尺寸时，尝试进行数据获取的操作
            if data_queue.qsize() < data_pool_size and stock_queue.qsize() > 0:
                # 从stock_queue 中获取一个代码
                stock_code = stock_queue.get()
                pbar_get.set_description(f"尝试获取{stock_code}数据")
                # 获取数据
                # 获取当前最新的数据日期
                try:
                    # 尝试从MongoDB查询该指数的最新数据
                    # gl.info("获取last_date")
                    last_date = self.get_latest_date(code=stock_code)
                except Exception as e:
                    # 失败则把开始日期设置为初识日期
                    last_date = bao_instance.init_date

                if end == last_date:
                    pbar_get.set_description(f"{stock_code}数据已是最新")
                    pbar_set.set_description(f"{stock_code}目前无需更新")
                    pbar_get.update(1)
                    pbar_set.update(1)
                else:
                    pbar_get.set_description(
                        f"{data_queue.qsize()}/{data_pool_size} Get {stock_code}"
                    )
                    rs = bao_instance.get_data(
                        code=stock_code,
                        data_frequency="d",
                        start_date=last_date,
                        end_date=end,
                    )
                    # 插入data_queue中
                    if rs.shape[0] > 0:
                        data_queue.put({stock_code: rs})
                    else:
                        pbar_set.update(1)
                    pbar_get.update(1)

            # 当线程队列小于设置的线程限制数时，切数据队列中有值时，尝试进行数据存储操作
            if len(thread_dict) < thread_num and data_queue.qsize() > 0:
                # 从 data_queue 中获取一个对象
                data = data_queue.get(block=True, timeout=None)
                # 创建一个数据插入的线程
                code = list(data.keys())[0]
                df = data[code]
                pbar_set.set_description(
                    f"{len(thread_dict)}/{thread_num} Store {code}"
                )
                thread = threading.Thread(
                    name=f"Min5 {code} update",
                    target=self.update_day_bar,
                    args=(code, df,),
                )
                # 线程注册
                thread_dict[thread.name] = thread
                # 线程添加至insert_thread_list
                tm.thread_register(thread=thread)
            # 清理僵尸线程
            dead_list = []
            for p in thread_dict:
                if not thread_dict[p].is_alive():
                    dead_list.append(p)
            for d in dead_list:
                thread_dict.pop(d)
                pbar_set.update(1)
            tm.kill_dead_thread()
            # 心跳
            time.sleep(heartbeat)

    # 异步获取日交易数据
    def get_day_bar_async(self, code, start_date, end_date, data_queue):
        rs = bao_instance.get_data(
            code=code, data_frequency="d", start_date=start_date, end_date=end_date,
        )
        # 插入data_queue中
        if rs.shape[0] > 0:
            data_queue.put({code: rs})

    # 异步更新日交易数据
    def update_day_bar_async_new(self, data_pool_size=10, thread_num=4):
        # 获取日交易数据队列
        gl.info("初始化.")
        data_queue = queue.Queue()
        get_thread_dict = dict()
        set_thread_dict = dict()
        heartbeat = 0.1
        stock_queue = queue.Queue()
        stock_df = self.get_all_stock_code()

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
                    # 尝试从MongoDB查询该指数的最新数据
                    last_date = self.get_latest_date(code=code)
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
                        target=self.get_day_bar_async,
                        args=(code, last_date, end, data_queue,),
                    )
                    # 线程注册
                    get_thread_dict[thread.name] = thread
                    # 线程添加至insert_thread_list
                    tm.thread_register(thread=thread)
                    pbar_set.set_description(
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
                    target=self.update_day_bar,
                    args=(code, df,),
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

    # 更新所有复权因子
    def update_adjust_factor(self):
        df_stock_list = self.get_all_stock_code()
        # df_stock_list = df_stock_list[:400]
        if df_stock_list.shape[0] == 0:
            gl.error("StockInfo为空")
            return

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
            rs = bao_instance.get_adjust_factor(code=df_stock_list.iloc[i].code)
            if rs.shape[0] > 0:
                insert_list = pd.concat([insert_list, rs], join="inner")
            pbar.update(1)
        if insert_list.shape[0] > 0:
            # 执行批量插入操作
            self.upsert_adjust_factor_async(data_frame=insert_list, thread_num=4)
        else:
            gl.error("共获取AdjustFactor 0 条, 请检查代码")

    def upsert_adjust_factor(self, data_frame: pd.DataFrame):
        """
        批量更新复权信息

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
        print(rs)
        # self.collection.ensure_index([("code",1),("divid_operate_date",1)])
        col.create_index([("code", 1), ("divid_operate_date", 1)])

    def upsert_adjust_factor_async(self, data_frame, thread_num=2):
        slice_count = 20000
        pieces_count = math.ceil(data_frame.shape[0] / slice_count)
        threads = []
        for i in range(pieces_count):
            gl.info(f"创建UpsertAF {i}")
            sliced_stock_list = data_frame[slice_count * i : slice_count * (i + 1)]
            thread = threading.Thread(
                name=f"AdjustFactor {slice_count*i}-{slice_count*(i+1)}",
                target=self.upsert_adjust_factor,
                args=(sliced_stock_list,),
            )
            threads.append(thread)
        tm.limit_thread_register(threads=threads, thread_num=thread_num)

    # 插入5min档位的分钟交易数据
    def insert_min5(self, code: str, data_frame: pd.DataFrame):
        # 存储5min档交易数据
        # 如果传入的DF为空，直接返回
        if data_frame.shape[0] == 0:
            return
        df = data_frame.drop_duplicates(subset=["time"], keep="first")
        df.rename(
            columns={"adjustflag": "adjust_flag"}, inplace=True,
        )
        col = self.db[code + min5_postfix]
        data = df.to_dict("record")
        col.insert_many(data)
        col.create_index([("time", 1)], unique=True)

    # 异步插入5min档位的分钟交易数据
    def get_min5_async(self, code, start_date, end_date, data_queue):
        time1 = datetime.datetime.now()
        rs = bao_instance.get_data(
            code=code, data_frequency="5", start_date=start_date, end_date=end_date,
        )
        # pbar_get.set_description(
        #     f"{data_queue.qsize()}/{data_pool_size}  {stock_code}"
        # )
        # 插入data_queue中
        if rs.shape[0] > 0:
            data_queue.put({code: rs})
            # pbar_get.set_description(
            #     f"数据队列: {data_queue.qsize()}/{data_pool_size}"
            # )
        else:
            self.set_nomin5(code=code)

    # 更新某只Code的5min挡位分钟交易数据
    def update_min5(self, code: str, df_new):
        df_old = self.get_min5(code=code)
        df_insert = self.get_df_norepeat(index_col="time", df_old=df_old, df_new=df_new)
        self.insert_min5(code=code, data_frame=df_insert)

    # 异步更新Min5交易数据
    def update_min5_async(self, data_pool_size=4, thread_num=2):
        # 获取日交易数据队列
        gl.info("初始化.")
        data_queue = queue.Queue()
        thread_dict = dict()
        heartbeat = 0.01
        stock_queue = queue.Queue()
        stock_df = self.get_all_stock_code()
        bao_instance.login()
        end = bao_instance.get_baostock_last_date()
        gl.info(f"目标更新日期为{end}")

        if stock_df.shape[0] == 0:
            gl.error("股票代码为空，请检查代码")
            return
        for i in range(stock_df.shape[0]):
            # 需要查询是否有Min5交易数据
            if self.check_stock_min5(code=stock_df.iloc[i].code):
                stock_queue.put(stock_df.iloc[i].code)
        gl.info(f"更新队列准备完毕:{stock_queue.qsize()}")
        # pbar_get = tqdm.tqdm(range(stock_queue.qsize()))
        # pbar_get.set_description("数据更新")
        # pbar_set = tqdm.tqdm(range(stock_queue.qsize()))
        # pbar_set.set_description("数据存储")

        while True:
            # 如果stock_queue
            if (
                stock_queue.qsize() == 0
                and data_queue.qsize() == 0
                and len(thread_dict) == 0
            ):
                gl.info("日交易数据更新完毕")
                return
            if data_queue.qsize() < data_pool_size and stock_queue.qsize() > 0:
                # 从stock_queue 中获取一个代码
                stock_code = stock_queue.get()
                pbar_get.set_description(
                    f"{stock_queue.qsize()}/{data_pool_size} {stock_code}"
                )
                # 获取数据
                # 获取当前最新的数据日期
                try:
                    # 尝试从MongoDB查询该指数的最新数据
                    last_date = self.get_min5_latest_time(code=stock_code)
                except Exception as e:
                    # 失败则把开始日期设置为初识日期
                    last_date = bao_instance.init_date

                if end == last_date:
                    print(f"{stock_code}数据已是最新")
                    pass
                    # pbar_get.set_description(f"{stock_code}数据已是最新")
                    # pbar_set.set_description(f"{stock_code}目前无需更新")
                    # pbar_get.update(1)
                    # pbar_set.update(1)
                else:
                    pbar_get.set_description(
                        f"{stock_queue.qsize()}/{data_pool_size} {stock_code}"
                    )
                    rs = bao_instance.get_data(
                        code=stock_code,
                        data_frequency="5",
                        start_date=last_date,
                        end_date=end,
                    )
                    pbar_get.set_description(
                        f"{stock_queue.qsize()}/{data_pool_size} {stock_code}"
                    )
                    # 插入data_queue中
                    if rs.shape[0] > 0:
                        data_queue.put({stock_code: rs})
                        pbar_get.set_description(
                            f"数据队列: {data_queue.qsize()}/{data_pool_size}"
                        )
                    else:
                        print(f"{stock_code} has no min5")
                        self.set_nomin5(code=stock_code)
                        # pbar_get.set_description(f"{stock_code}没有min5")
                        # pbar_set.update(1)
                    # pbar_get.update(1)
            else:
                pass
                # pbar_get.set_description("等待存储")

            if len(thread_dict) < thread_num and data_queue.qsize() > 0:
                # 从 data_queue 中获取一个对象
                data = data_queue.get(block=True, timeout=None)
                # 创建一个数据插入的线程
                code = list(data.keys())[0]
                df = data[code]
                # pbar_set.set_description(f"尝试存储{code}数据")
                thread = threading.Thread(
                    name=f"Daybar {code} update",
                    target=self.update_min5,
                    args=(code, df,),
                )
                # 线程注册
                thread_dict[thread.name] = thread
                # 线程添加至insert_thread_list
                tm.thread_register(thread=thread)
            # 清理僵尸线程
            dead_list = []
            for p in thread_dict:
                if not thread_dict[p].is_alive():
                    dead_list.append(p)
            for d in dead_list:
                thread_dict.pop(d)
                # pbar_set.update(1)
            tm.kill_dead_thread()
            print(f"{len(thread_dict)}/{thread_num}")
            # 心跳
            time.sleep(heartbeat)

    # 异步更新Min5交易数据
    def update_min5_async_new(self, data_pool_size=4, thread_num=2):
        gl.info("初始化.")
        data_queue = queue.Queue()
        get_thread_dict = dict()
        set_thread_dict = dict()
        heartbeat = 0.1
        stock_queue = queue.Queue()
        stock_df = self.get_all_stock_code()

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
                    # 尝试从MongoDB查询该指数的最新数据
                    last_date = self.get_min5_latest_time(code=code)
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
                        target=self.get_min5_async,
                        args=(code, last_date, end, data_queue,),
                    )

                    # 线程注册
                    get_thread_dict[thread.name] = thread
                    # 线程添加至insert_thread_list
                    tm.thread_register(thread=thread)
                    pbar_set.set_description(
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
                    args=(code, df,),
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
    def get_day_bar(self, code):
        # TODO 添加日期范围
        col = self.db[code]
        rs = col.find()
        df = pd.DataFrame(list(rs))
        return df

    # 获取分钟交易数据
    def get_min5(self, code):
        # TODO 添加日期范围
        col = self.db[code + min5_postfix]
        rs = col.find()
        df = pd.DataFrame(list(rs))
        return df

    # 获取某只股票日交易数据的最新日期
    def get_latest_date(self, code: str):
        col = self.db[code]
        s = col.find().sort("date", pymongo.DESCENDING).limit(1)
        last_date = s[0]["date"]
        return last_date

    # 获取某股票min5数据的最新时间戳
    def get_min5_latest_time(self, code: str):
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
        rs2 = self.get_all_stock_code()
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


ginkgo_mongo = GinkgoMongo(
    host=HOST, port=PORT, username=USERNAME, pwd=PASSWORD, database=DATABASE
)
