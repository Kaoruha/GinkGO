import time
import os
import multiprocessing
import pymongo
import datetime
import queue
import pandas as pd
import tqdm
import math
import threading
from ginkgo.data.stock.baostock_data import bao_instance as bi
from ginkgo.data.bitcoin.coin_cap import coin_cap_instance
from ginkgo.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.thread_manager import thread_manager as tm
from ginkgo.util.adjust_calculation import adjust_cal
from ginkgo.libs import GINKGOLOGGER as gl

# 5分钟交易数据后缀
min5_postfix = ".min5"


class GinkgoMongo(object):
    """
    数据的存储模块，负责与mongoDB的通信
    """

    def __init__(self, host, port, username, password, database):
        self.client = None
        self.db = None
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database

        self.__connect()

        self.code_list_cache = None
        self.code_list_cache_last_update = None

    def __connect(self):
        """
        建立mongo连接
        TODO 连接失败的操作：提示安装mongo，配置端口，自动安装mongo？
        """
        # 建立客户端连接
        gl.logger.debug("正在尝试连接Mongo")
        uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.client = pymongo.MongoClient(uri)
        gl.logger.debug(f"CurrentTarget: {uri}")
        gl.logger.debug(self.client)
        gl.logger.debug("成功连接至Mongo")
        # 切换数据库
        self.db = self.client[self.database]
        gl.logger.debug(f"切换数据库 {self.database}")

    # 更新所有股票指数基本信息
    def update_stockinfo(self) -> None:
        """
        更新所有指数代码基本信息,包括指数指数代码、指数名称、交易状态
        """
        gl.logger.info("StockInfo更新初始化.")
        slice_count = 3000
        gl.logger.info(f"存储切片设置为 {slice_count}")
        # Step1：通过Baostock获取所有指数代码
        result = bi.get_all_stock_code()

        # Step2：如果数据不为空进行持久化操作，反之报错
        if result.shape[0] == 0:
            gl.logger.error("股票指数代码获取为空，请检查代码或日期")
            return

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

        gl.logger.info("StockInfo更新完成.")

    # 从mongo中获取所有股票代码
    def get_all_stockcode_by_mongo(self) -> pd.DataFrame:
        """
        从本地mongo中获得所有股票代码

        :return: [所有StockCode组成的df]
        :rtype: [DataFrame]
        """
        if self.code_list_cache_last_update is None:
            self.code_list_cache_last_update = datetime.datetime.now()
            is_overdue = False
        else:
            time_delta = datetime.datetime.now() - self.code_list_cache_last_update
            is_overdue = time_delta >= datetime.timedelta(days=1)
        if (self.code_list_cache is not None) and (not is_overdue):
            gl.logger.debug("Get CodeList by Cache")
            return self.code_list_cache.drop(["_id"], axis=1)

        col = self.db["stock_info"]
        rs = col.find()
        df = pd.DataFrame(rs)
        self.code_list_cache = df
        self.code_list_cache_last_update = datetime.datetime.now()
        gl.logger.debug("Get CodeList with no Cache")
        return df.drop(["_id"], axis=1)

    # 更新插入复权数据
    def upsert_adjustfactor(self, data_frame: pd.DataFrame) -> None:
        """
        与mongo交互，更新插入复权信息

        :param data_frame: [description]
        :type data_frame: DataFrame
        """
        col = self.db["adjust_factor"]

        operations = []
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
        col.bulk_write(operations)
        # TODO 根据批量差距结果执行后续操作
        # 建立索引
        col.create_index([("code", 1), ("divid_operate_date", 1)])

    # 异步更新插入复权数据
    def upsert_adjustfactor_async(self, data_frame: pd.DataFrame, thread_num=2) -> None:
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
            gl.logger.info(f"创建UpsertAF {i}")
            sliced_stock_list = data_frame[slice_count * i : slice_count * (i + 1)]
            thread = threading.Thread(
                name=f"AdjustFactor {slice_count * i}-{slice_count * (i + 1)}",
                target=self.upsert_adjustfactor,
                args=(sliced_stock_list,),
            )
            threads.append(thread)
        tm.limit_thread_register(threads=threads, thread_num=thread_num)

    # 更新所有复权因子
    def update_adjustfactor(self) -> None:
        """
        全量更新复权因子
        """
        gl.logger.info("AdjustFactor更新初始化.")
        # 获取所有代码
        df_stock_list = self.get_all_stockcode_by_mongo()

        if df_stock_list.shape[0] == 0:
            gl.logger.error("StockInfo为空")
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
        pbar = tqdm.tqdm(total=stock_count)

        for i in range(stock_count):
            pbar.set_description(f"获取{df_stock_list.iloc[i].code}复权数据")
            result = bi.get_adjust_factor(code=df_stock_list.iloc[i].code)
            if result.shape[0] > 0:
                insert_list = pd.concat([insert_list, result], join="inner")
            pbar.update(1)
        if insert_list.shape[0] > 0:
            # 执行批量插入操作
            self.upsert_adjustfactor_async(data_frame=insert_list, thread_num=4)
        else:
            gl.logger.error("共获取AdjustFactor 0 条, 请检查代码")

    # 插入日交易数据
    def insert_daybar(self, code: str, data_frame: pd.DataFrame) -> None:
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
        data = df.to_dict(orient="records")
        # 批量插入
        col.insert_many(data)
        # 建立索引
        col.create_index([("date", 1)], unique=True)

    # 更新日交易数据
    def update_daybar(self, code: str, df_new: pd.DataFrame) -> None:
        """
        更新某只股票的日交易数据

        从mongo中获取某只Code的历史日交易数据，待插入数据进行比对后，插入不重复的数据

        :param code: 股票代码
        :type code: str
        :param df_new: 待插入的日交易数据
        :type df_new: DataFrame
        """
        if df_new.shape[0] == 0:
            return
        df_old = self.get_dayBar_by_mongo(code=code)
        df_insert = self.get_df_norepeat(index_col="date", df_old=df_old, df_new=df_new)
        self.insert_daybar(code=code, data_frame=df_insert)

    def insert_min5(self, code: str, data_frame: pd.DataFrame) -> None:
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
        df = data_frame.drop_duplicates(subset=["time"], keep="first").copy()
        df.rename(
            columns={"adjustflag": "adjust_flag"},
            inplace=True,
        )
        col = self.db[code + min5_postfix]
        data = df.to_dict(orient="records")
        col.insert_many(data)
        col.create_index([("time", 1)], unique=True)

    # 更新某只Code的5min挡位分钟交易数据
    def update_min5(self, code: str, df_new: pd.DataFrame) -> None:
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

    def update_stock_min5(self, queue, code, end_date, pbar):
        # print(f"Run task pid:{os.getpid()}...")
        try:
            # 尝试从mongoDB查询该指数的最新数据
            last_date = self.get_min5_latestDate_by_mongo(code=code)
        except Exception:
            # 失败则把开始日期设置为初识日期
            last_date = bi.init_date

        if last_date != end_date:
            rs = bi.get_data(
                code=code,
                data_frequency="5",
                start_date=last_date,
                end_date=end_date,
            )
            if rs.shape[0] > 0:
                self.update_min5(code, rs)
            else:
                self.set_nomin5(code=code)
        queue.get(code)
        pbar.update()

    # 获取日交易数据
    def get_dayBar_by_mongo(
        self, code: str, start_date="", end_date=""
    ) -> pd.DataFrame:
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
            start_date = bi.init_date
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
            df = df.reset_index(drop=True)
        return df

    # 获取分钟交易数据
    def get_min5_by_mongo(self, code: str, start_date="", end_date="") -> pd.DataFrame:
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
            start_date = bi.init_date
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
        return df.reset_index()

    # 获取复权数据
    def get_adjustfactor_by_mongo(
        self, code: str, start_date="", end_date=""
    ) -> pd.DataFrame:
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
            start_date = bi.init_date
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
            pass
            gl.logger.error(e)

        return df

    # 获取某只股票日交易数据的最新日期
    def get_daybar_latestDate_by_mongo(self, code: str) -> str:
        col = self.db[code]
        result = col.find().sort("date", pymongo.DESCENDING).limit(1)
        last_date = result[0]["date"]
        return last_date

    # 获取某股票min5数据的最新时间戳
    def get_min5_latestDate_by_mongo(self, code: str) -> str:
        col = self.db[code + min5_postfix]
        s = col.find().sort("date", pymongo.DESCENDING).limit(1)
        last_time = s[0]["date"]
        return last_time

    def print_dead_stock(self):
        rs1 = bi.get_all_stock_code()
        code_list1 = []
        code_list2 = []
        for i in range(rs1.shape[0]):
            t = rs1.iloc[i].code
            code_list1.append(t)
        rs2 = self.get_all_stockcode_by_mongo()
        for i in range(rs2.shape[0]):
            t = rs2.iloc[i].code
            code_list2.append(t)
        for i in code_list2:
            if i not in code_list1:
                print(i)

    def set_nomin5(self, code: str) -> None:
        col = self.db["stock_info"]
        col.update_one({"code": code}, {"$set": {"has_min5": False}})

    def check_stock_min5(self, code: str) -> bool:
        col = self.db["stock_info"]
        stock_count = col.count_documents({"code": code})
        if stock_count != 1:
            gl.logger.error(f"{code}不存在")
            return False
        else:
            try:
                result = col.find({"code": code})[0]["has_min5"]
                return result
            except Exception as e:
                return True

    def get_df_norepeat(self, index_col, df_old, df_new) -> pd.DataFrame:
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

    def check_code_exist(self, code: str) -> bool:
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

    def query_stock(
        self, code: str, start_date: str, end_date: str, frequency: str, adjust_flag=3
    ) -> pd.DataFrame:
        """
        股价查询
        """
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
            adjust = adjust_cal(
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

    def update_all(self):
        self.update_stockinfo()
        self.update_adjustfactor()
        self.update_daybar_async(thread_num=4)
        self.update_min5_async(thread_num=2)
        # TODO 加入虚拟货币的更新
        self.upsert_coin_info()
        self.update_all_coin()

    def get_trade_day(self):
        """
        获取所有交易日
        """
        df = self.get_dayBar_by_mongo(code="sh.000001")
        return df["date"]


ginkgo_mongo = GinkgoMongo(
    host=HOST, port=PORT, username=USERNAME, password=PASSWORD, database=DATABASE
)


def update_stock_daybar(queue, code, end_date, pbar):
    print(f"Run task pid:{os.getpid()}...")

    try:
        # 尝试从mongoDB查询该指数的最新数据
        last_date = ginkgo_mongo.get_daybar_latestDate_by_mongo(code=code)
    except Exception:
        # 失败则把开始日期设置为初识日期
        last_date = bi.init_date

    if last_date != end_date:
        rs = bi.get_data(
            code=code,
            data_frequency="d",
            start_date=last_date,
            end_date=end_date,
        )
        if rs.shape[0] > 0:
            ginkgo_mongo.update_daybar(code, rs)
    queue.get(code)
    pbar.update()
