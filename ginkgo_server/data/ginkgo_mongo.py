"""
数据的存储模块，负责与MongoDB的通信以及本地缓存的处理
"""

import pymongo
import time
import queue
import pandas as pd
import tqdm
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD
from ginkgo_server.data.storage import ginkgo_storage as gs
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.data.models.stock_info import StockInfo
from ginkgo_server.data.models.adjust_factor import AdjustFactor
from ginkgo_server.data.models.day_bar import DayBar
from ginkgo_server.data.models.min5_bar import Min5Bar


class GinkgoMongo(object):
    def __init__(self, host, port, username, pwd, database):
        self.client = None
        self.db = None
        self.collection = None
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

    def __change_collection(self, collection_name: str):
        """
        切换数据集

        :param collection_name: 数据集名称
        :type collection_name: str
        """
        self.collection = self.db[collection_name]

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
            self.__change_collection(collection_name="stock_info")

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
            self.collection.bulk_write(operations)
            pbar.set_description(f"完成 StockInfo 更新")
            # TODO 根据插入结果进行相应处理
            pbar.set_description(f"StockInfo 索引更新")
            self.collection.create_index([("code", 1)], unique=True)
            pbar.set_description(f"StockInfo 更新完成")
        else:
            gl.error("股票指数代码获取为空，请检查代码或日期")

    def get_all_stock_code(self):
        self.__change_collection(collection_name="stock_info")
        rs = self.collection.find()
        df = pd.DataFrame(rs)
        return df

    # 更新所有复权因子
    def update_adjust_factor(self):
        df_stock_list = self.get_all_stock_code()
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
            rs = bao_instance.get_adjust_factor(code=df_stock_list.iloc[i].code)
            print(rs.shape[0])
            if rs.shape[0] > 0:
                temp_list = pd.merge(insert_list, rs)
                insert_list = temp_list
            print(insert_list.shape[0])

    def upsert_day_bar(self, code: str, data_frame: pd.DataFrame):
        """
        批量更新某只股票的日交易数据

        :param code: 股票代码
        :type code: str
        :param data_frame: [description]
        :type data_frame: DataFrame
        """
        self.__change_collection(collection_name=code)

        operations = []
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
        self.collection.bulk_write(operations)
        # TODO 根据插入结果进行相应处理
        self.collection.create_index([("date", 1)], unique=True)

    def upsert_min5(self, code: str, data_frame: pd.DataFrame):
        self.__change_collection(collection_name=code + "_min5")
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
        result = self.collection.bulk_write(operations)

    def upsert_min5_old(self, code: str, data_list):
        self.__change_collection(collection_name=code)
        # self.collection.ensure_index("time", unique=True)
        operations = []
        for i in data_list:
            operations.append(
                pymongo.UpdateOne(
                    {"time": i.time},
                    {
                        "$push": {
                            "date": i.date,
                            "code": i.code,
                            "open": i.open,
                            "high": i.high,
                            "low": i.low,
                            "close": i.close,
                            "volume": i.volume,
                            "amount": i.amount,
                            "adjust_flag": i.adjust_flag,
                        }
                    },
                    upsert=True,
                )
            )
        result = self.collection.bulk_write(operations)
        # operations = [
        #     UpdateOne({"field1": 1}, {"$push": {"vals": 1}}, upsert=True),
        #     UpdateOne({"field1": 1}, {"$push": {"vals": 2}}, upsert=True),
        #     UpdateOne({"field1": 1}, {"$push": {"vals": 3}}, upsert=True),
        # ]

        # result = collection.bulk_write(operations)

    def get_latest_date(self, code: str):
        self.__change_collection(collection_name=code)
        s = self.collection.find().sort("date", pymongo.DESCENDING).limit(1)
        last_date = s[0]["date"]
        return last_date

    def get_latest_time(self, code: str):
        self.__change_collection(collection_name=code + "_min5")
        s = self.collection.find().sort("time", pymongo.DESCENDING).limit(1)
        last_time = s[0]["time"]
        return last_time

    def update_day_bar_async(self, data_pool_size=8, thread_num=1):
        # 获取日交易数据队列
        data_queue = queue.Queue()
        insert_thread_queue = queue.Queue()
        heartbeat = 1
        while data_queue.qsize() <= data_pool_size:
            # TODO 获取数据
            # TODO data_queue 放入数据对象
            pass
            # 当队列内有待插入数据且当前存储线程小于等于thread_num时，新建一个存储线程，进行数据库upsert操作
            while insert_thread_queue.qsize() <= thread_num and data_queue.qsize() > 0:
                # TODO 从data_queue中提取一列数据，新建一个线程进行存储
                # TODO 检查insert_thread_queue内所有线程的运行状态，如果运行结束，从队列中剔除
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
