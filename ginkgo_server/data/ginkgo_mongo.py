import pymongo
import pandas as pd
from ginkgo_server.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD


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

        self.connect()

    def connect(self):
        # self.client = pymongo.MongoClient(
        #     host=self.host, port=self.port, username=self.username, password=self.pwd
        # )
        self.client = pymongo.MongoClient(host=self.host, port=self.port)

        # db = self.client.admin
        # # 认证
        # db.authenticate(self.username, self.pwd)
        # # 需要用的的表需要在认证后用client单独去关联
        # mongo_db = self.client[self.database]

        # # 获取所有collections并打印，验证是否登录成功
        # coll_names = mongo_db.list_collection_names(session=None)
        # print(coll_names)
        dblist = self.client.list_database_names()
        print(dblist)
        self.db = self.client[self.database]

    def change_collection(self, collection_name: str):
        self.collection = self.db[collection_name]

    def upsert_day_bar(self, code: str, data_frame):
        self.change_collection(collection_name=code)
        self.collection.ensure_index("date", unique=True)
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
        result = self.collection.bulk_write(operations)

    def upsert_min5(self, code: str, data_frame):
        self.change_collection(collection_name=code + "_min5")
        self.collection.ensure_index("time", unique=True)
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
        self.change_collection(collection_name=code)
        self.collection.ensure_index("time", unique=True)
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
        self.change_collection(collection_name=code)
        s = self.collection.find().sort("date", pymongo.DESCENDING).limit(1)
        last_date = s[0]["date"]
        return last_date

    def get_latest_time(self, code: str):
        self.change_collection(collection_name=code + "_min5")
        s = self.collection.find().sort("time", pymongo.DESCENDING).limit(1)
        last_time = s[0]["time"]
        return last_time

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
