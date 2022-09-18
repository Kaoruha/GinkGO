"""
数据存储模块，负责与Clickhouse通信
"""
import pandas as pd
import tqdm
import datetime
import time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.stock.baostock_data import bao_instance as bi
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD
from ginkgo.data.models.stock_info import StockInfo


class GinkgoClickHouse(object):
    def __init__(self, host, port, username, password, database):
        self.engine = None
        self.session = None
        self.metadata = None
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database

        self.__connect()

        self.code_list_cache = None
        self.code_list_cache_last_update = None

    def __connect(self):
        gl.logger.info("Tring to connect Clickhouse")
        uri = f"clickhouse+native://{self.username}:{self.password}@{self.host}/{self.database}"
        gl.logger.debug(f"CurrentTarget: {uri}")
        self.engine = create_engine(uri)
        self.session = sessionmaker(self.engine)()
        self.metadata = MetaData(bind=self.engine)
        gl.logger.info("Connect to clickhouse succeed.")

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        return self.insp.has_table(name)

    def insert_stockinfo(self) -> None:
        pass

    def del_stockinfo(self) -> None:
        pass

    def update_all_stockinfo(self) -> None:
        t0 = datetime.datetime.now()
        gl.logger.info("StockInfo Updating Start.")
        # Step1：通过Baostock获取所有指数代码
        result = bi.get_all_stock_code()
        # Step2：如果数据不为空进行持久化操作，反之报错
        if result.shape[0] == 0:
            gl.logger.error("股票指数代码获取为空，请检查代码或日期")
            return
        gl.logger.info("Updating StockInfo")
        gl.logger.info("Get Existing StockInfo.")
        old_df = self.get_stockinfo()
        rs_list = []
        pbar = tqdm.tqdm(total=result.shape[0])
        for i, r in result.iterrows():
            item = StockInfo(
                code=r["code"],
                trade_status=int(r["tradeStatus"]),
                code_name=r["code_name"],
            )
            pbar.update(1)
            pbar.set_description(f"Updating StockInfo {item.code}")
            records = old_df[old_df["code"] == item.code].sort_values(
                "create_time", ascending=False
            )
            if records.shape[0] == 0:
                rs_list.append(item)
            else:
                r0 = records.head(1)
                condition1 = r0["name"].values[0] == item.name
                condition2 = r0["trade_status"].values[0] == item.trade_status
                if condition1 & condition2:
                    continue
                else:
                    rs_list.append(item)
        self.session.add_all(rs_list)
        pbar.set_description("Dict Loaded.")
        self.session.commit()
        pbar.set_description("StockInfo Complete:)     ")
        pbar.close()
        t1 = datetime.datetime.now()
        time.sleep(0.2)
        gl.logger.info(
            f"StockInfo Update Complete. Update: {len(rs_list)}, Cost: {t1-t0}"
        )

    def get_stockinfo(self) -> pd.DataFrame:
        old_rs = self.session.query(StockInfo).filter()
        df = pd.read_sql(old_rs.statement, con=self.engine)
        if df.shape[0] > 0:
            df = df.drop(["uuid"], axis=1)
        # df.drop_duplicates(
        #     subset=["code", "name", "trade_status", "has_min5"], inplace=True
        # )
        return df

    def get_codes(self) -> pd.DataFrame:
        pass

    def insert_adjustfactor(self) -> None:
        pass

    def insert_adjustfactor_async(self) -> None:
        pass

    def del_adjustfactor(self) -> None:
        pass

    def update_adjustfactor(self) -> None:
        pass

    def get_adjustfactor(self) -> None:
        pass

    def insert_daybar(self) -> None:
        pass

    def insert_daybar_async(self) -> None:
        pass

    def del_daybar(self) -> None:
        pass

    def update_daybar(self) -> None:
        pass

    def get_daybar(self) -> None:
        pass

    def insert_min5(self) -> None:
        pass

    def insert_min5_async(self) -> None:
        pass

    def del_min5(self) -> None:
        pass

    def update_min5(self) -> None:
        pass

    def get_min5(self) -> None:
        pass

    def get_last_trade_day(self) -> None:
        pass

    def get_last_trade_time(self) -> None:
        pass

    def set_nomin5(self) -> None:
        pass

    def has_min5(self) -> bool:
        pass

    def get_trade_day(self) -> bool:
        pass

    def get_df_norepeat(self) -> pd.DataFrame:
        pass

    def query_stock(self) -> None:
        pass


ginkgo_clickhouse = GinkgoClickHouse(
    host=HOST, port=PORT, username=USERNAME, password=PASSWORD, database=DATABASE
)

# user = "ginkgo"
# pwd = "caonima123"
# host = "localhost"
# db = "quant"
# uri = f"clickhouse+native://{user}:{pwd}@{host}/{db}"

# engine = create_engine(uri)
# session = sessionmaker(engine)()
# metadata = MetaData(bind=engine)

# Base = declarative_base(metadata=metadata)


# class Rate(Base):
#     __tablename__ = "MergeTree"
#     day = Column(Date, primary_key=True)
#     value = Column(Integer)
#     is_delete = Column(Boolean, default=False)

#     __table_args__ = (engines.MergeTree(order_by=["day"]),)


# insp = inspect(engine)
# db_list = insp.get_schema_names()
# print(f"Databases:  {db_list}")
# # if database not in db_list:
# #     engine.execute(DDL(f"CREATE DATABASE IF NOT EXISTS {database}"))

# if not insp.has_table(Rate.__tablename__):
#     Rate.__table__.create()
# else:
#     print(f"{Rate.__tablename__} already exists.")


# # INSERT
# a = Rate()
# a.day = date(2021, 5, 3)
# a.value = 123
# session.add(a)
# session.commit()

# # INSERT BATCH
# t0 = datetime.datetime.now()
# for j in range(10):
#     t1 = datetime.datetime.now()
#     for i in range(20000):
#         item = Rate()
#         item.day = date(2022, 4, 1)
#         item.value = i
#         session.add(item)
#     t2 = datetime.datetime.now()
#     session.commit()
#     t3 = datetime.datetime.now()

#     print(f"Epoch: {j+1}, cost: {t3-t2}, avg: {(t3-t1)/(j+1)}, total: {t3-t0}")


# # GET
# t_get0 = datetime.datetime.now()
# rs = session.query(Rate).filter()
# df = pd.read_sql(rs.statement, con=engine)
# t_get1 = datetime.datetime.now()
# print(df)
# print(t_get1 - t_get0)
