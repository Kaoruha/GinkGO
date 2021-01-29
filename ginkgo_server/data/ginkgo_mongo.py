"""
数据的存储模块，负责与MongoDB的通信以及本地缓存的处理
"""

import pymongo
import time
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
        # Step1：通过Baostock获取所有指数代码
        bao_instance.login()
        result = bao_instance.get_all_stock_code()
        # result = result[:10000]

        # Step2：如果数据不为空进行持久化操作，反之报错
        if result.shape[0] > 0:
            col = self.db['stock_info']

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
            col.bulk_write(operations)
            pbar.set_description(f"完成 StockInfo 更新")
            # TODO 根据插入结果进行相应处理
            pbar.set_description(f"StockInfo 索引更新")
            col.create_index([("code", 1)], unique=True)
            pbar.set_description(f"StockInfo 更新完成")
        else:
            gl.error("股票指数代码获取为空，请检查代码或日期")

    def get_all_stock_code(self):
        col = self.db['stock_info']
        rs = col.find()
        df = pd.DataFrame(rs)
        if df.shape[0] > 0:
            gl.info(f"查询到 {df.shape[0]} 条指数代码")
        else:
            gl.error(f"指数代码查询为空，请检查代码")
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

    def upsert_day_bar(self, code: str, data_frame: pd.DataFrame):
        """
        批量更新某只股票的日交易数据

        :param code: 股票代码
        :type code: str
        :param data_frame: [description]
        :type data_frame: DataFrame
        """
        col = self.db[code]

        operations = []
        gl.info('开始添加批量操作')
        for i in range(data_frame.shape[0]):
            operations.append(
                pymongo.UpdateOne(
                    {"date": data_frame.iloc[i].date},
                    {
                        "$set": {
                            "code": data_frame.iloc[i].code,
                            "open": data_frame.iloc[i].open,
                            "high": data_frame.iloc[i].high,
                            "low": data_frame.iloc[i].low,
                            "close": data_frame.iloc[i].close,
                            "preclose": data_frame.iloc[i].preclose,
                            "volume": data_frame.iloc[i].volume,
                            "amount": data_frame.iloc[i].amount,
                            "adjust_flag": data_frame.iloc[i].adjustflag,
                            "turn": data_frame.iloc[i].turn,
                            "tradestatus": data_frame.iloc[i].tradestatus,
                            "pct_change": data_frame.iloc[i].pctChg,
                            "is_ST": data_frame.iloc[i].isST,
                        }
                    },
                    upsert=True,
                )
            )
        gl.info('批量操作添加完成')
        gl.info('开始执行批量操作')
        col.bulk_write(operations)
        gl.info('批量操作执行完成')
        # TODO 根据插入结果进行相应处理
        col.create_index([("date", 1)], unique=True)
        gl.info('索引创建完成')

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

    def upsert_min5(self, code: str, data_frame: pd.DataFrame):
        col = self.db[code + "_min5"]
        operations = []
        for i in range(data_frame.shape[0]):
            operations.append(
                pymongo.UpdateOne(
                    {"time": data_frame.iloc[i].time},
                    {
                        "$push": {
                            "date": data_frame.iloc[i].date,
                            "code": data_frame.iloc[i].code,
                            "open": data_frame.iloc[i].open,
                            "high": data_frame.iloc[i].high,
                            "low": data_frame.iloc[i].low,
                            "close": data_frame.iloc[i].close,
                            "volume": data_frame.iloc[i].volume,
                            "amount": data_frame.iloc[i].amount,
                            "adjust_flag": data_frame.iloc[i].adjustflag,
                        }
                    },
                    upsert=True,
                )
            )
        result = col.bulk_write(operations)


    def get_latest_date(self, code: str):
        col = self.db[code]
        s = col.find().sort("date", pymongo.DESCENDING).limit(1)
        last_date = s[0]["date"]
        return last_date

    def get_latest_time(self, code: str):
        col = self.db[code + "_min5"]
        s = col.find().sort("time", pymongo.DESCENDING).limit(1)
        last_time = s[0]["time"]
        return last_time

    def update_day_bar_async(self, data_pool_size=8, thread_num=1):
        # 获取日交易数据队列
        gl.info('初始化.')
        data_queue = queue.Queue()
        thread_dict = dict()
        heartbeat = 1
        stock_queue = queue.Queue()
        gl.info('尝试获取股票代码')
        stock_df = self.get_all_stock_code()
        gl.info('获取股票代码成功')
        bao_instance.login()
        end = bao_instance.get_baostock_last_date()
        gl.info(f'最新更新日期为{end}')

        if stock_df.shape[0] == 0:
            gl.error(f'股票代码为空，请检查代码')
            return
        for i in range(stock_df.shape[0]):
            stock_queue.put(stock_df.iloc[i].code)
        gl.info('待更新队列准备完毕')

        while True:
            # 如果stock_queue、
            if stock_queue.qsize() ==0 and data_queue.qsize()==0 and len(insert_thread_list)==0:
                return
            
            if data_queue.qsize() < data_pool_size:
                # 从stock_queue 中获取一个代码
                stock_code = stock_queue.get()
                gl.info(f'尝试获取{stock_code}数据')
                # 获取数据
                # 获取当前最新的数据日期
                try:
                    # 尝试从MongoDB查询该指数的最新数据
                    # gl.info("获取last_date")
                    last_date = self.get_latest_date(code=stock_code)
                except Exception as e:
                    # 失败则把开始日期设置为初识日期
                    # gl.info("设置last_date")
                    last_date = bao_instance.init_date

                if end is last_date:
                    gl.info(f"{stock_code}数据已是最新，无需更新")
                else:
                    gl.info(f'{stock_code}数据不是最新，尝试拉取最新数据')
                    rs = bao_instance.get_data(
                        code=stock_code,
                        data_frequency="d",
                        start_date=last_date,
                        end_date=end,
                    )
                    gl.info(f'成功获取{stock_code}增量数据')
                    # 插入data_queue中
                    data_queue.put({stock_code:rs})
                    gl.info(f'待插入数据:{data_queue.qsize()}')

            if len(thread_dict) < thread_num and data_queue.qsize()>0:
                # 从 data_queue 中获取一个对象
                data = data_queue.get(block=True, timeout=None)
                # 创建一个数据插入的线程
                code = list(data.keys())[0]
                df = data[code]
                thread = threading.Thread(
                    name=f"Daybar {code} update",
                    target=self.upsert_day_bar,
                    args=(code,df,),
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
            tm.kill_dead_thread()
            # 心跳
            gl.info(f'Stock：{stock_queue.qsize()}，Data：{data_queue.qsize()}，Threads：{len(thread_dict)}')
            time.sleep(heartbeat)



    def is_code_in_min_ignore(self, code: str):
        pass

    def add_to_min_ignore(self, code: str):
        pass

    # db.users.update({'name':'user5'}, {'$set': {'age': 22}, '$setOnInsert': {'index':5}}, upsert=True)

    # dblist = mongo_client.list_database_names()

    # print(dblist)

    # if "quant" in dblist:
    #     print("quant已经存在")
    # else:
    #     print("quant不存在")

    # db = mongo_client.quant
    # factor = db["adjust_factor"]

    # for s in factor.find({}, {"name": "hello2"}):
    #     factor.update_one(s, {"$set": {"name": "hello22_new"}})

    # for x in factor.find():
    #     print(x)
    #     factor.delete_one(x)

    # for x in factor.find():
    #     print(x)


ginkgo_mongo = GinkgoMongo(
    host=HOST, port=PORT, username=USERNAME, pwd=PASSWORD, database=DATABASE
)
