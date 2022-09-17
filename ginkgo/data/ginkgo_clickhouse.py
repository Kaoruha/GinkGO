"""
数据存储模块，负责与Clickhouse通信
"""
import pandas as pd
import datetime
from sqlalchemy import (
    create_engine,
    Column,
    MetaData,
    Integer,
    String,
    Boolean,
    Date,
    inspect,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from clickhouse_sqlalchemy import engines
from datetime import date
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD

user = "ginkgo"
pwd = "caonima123"
host = "localhost"
db = "quant"
uri = f"clickhouse+native://{user}:{pwd}@{host}/{db}"


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
        gl.logger.debug("Tring to connect Clickhouse")
        uri = f"clickhouse+native://{self.username}:{self.password}@{self.host}/{self.database}"
        gl.logger.debug(f"CurrentTarget: {uri}")
        self.engine = create_engine(uri)
        self.session = sessionmaker(engine)()
        self.metadata = MetaData(bind=engine)
        gl.logger.debug("Connect to clickhouse succeed.")

    def update_stockinfo(self) -> None:
        pass

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

engine = create_engine(uri)
session = sessionmaker(engine)()
metadata = MetaData(bind=engine)

Base = declarative_base(metadata=metadata)


class Rate(Base):
    __tablename__ = "MergeTree"
    day = Column(Date, primary_key=True)
    value = Column(Integer)
    is_delete = Column(Boolean, default=False)

    __table_args__ = (engines.MergeTree(order_by=["day"]),)


insp = inspect(engine)
db_list = insp.get_schema_names()
print(f"Databases:  {db_list}")
# if database not in db_list:
#     engine.execute(DDL(f"CREATE DATABASE IF NOT EXISTS {database}"))

if not insp.has_table(Rate.__tablename__):
    Rate.__table__.create()
else:
    print(f"{Rate.__tablename__} already exists.")


# INSERT
a = Rate()
a.day = date(2021, 5, 3)
a.value = 123
session.add(a)
session.commit()

# INSERT BATCH
t0 = datetime.datetime.now()
for j in range(10):
    t1 = datetime.datetime.now()
    for i in range(20000):
        item = Rate()
        item.day = date(2022, 4, 1)
        item.value = i
        session.add(item)
    t2 = datetime.datetime.now()
    session.commit()
    t3 = datetime.datetime.now()

    print(f"Epoch: {j+1}, cost: {t3-t2}, avg: {(t3-t1)/(j+1)}, total: {t3-t0}")


# GET
t_get0 = datetime.datetime.now()
rs = session.query(Rate).filter()
df = pd.read_sql(rs.statement, con=engine)
t_get1 = datetime.datetime.now()
print(df)
print(t_get1 - t_get0)
