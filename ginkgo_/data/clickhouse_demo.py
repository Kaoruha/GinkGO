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

user = "ginkgo"
pwd = "caonima123"
host = "localhost"
db = "quant"
uri = f"clickhouse+native://{user}:{pwd}@{host}/{db}"

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
