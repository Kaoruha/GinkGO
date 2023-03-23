# from sqlalchemy import create_engine, Column, MetaData, DDL
# from sqlalchemy.orm import sessionmaker
# from clickhouse_sqlalchemy import (
#     Table,
#     make_session,
#     get_declarative_base,
#     types,
#     engines,
# )
# from clickhouse_driver import Client
# from datetime import date, timedelta
# from sqlalchemy import func

# user = "ginkgoadm"
# pwd = "helloclickhouse"
# host = "localhost"
# port = 8123
# db = "ginkgoclick"
# # db = "default"


# uri = f"clickhouse+native://{user}:{pwd}@{host}:{port}/{db}"

# engine = create_engine(f"clickhouse://{user}:{pwd}@{host}:{port}/{db}")


# # engine = create_engine(uri, pool_size=100, pool_recycle=3600, pool_timeout=20)
# session = make_session(engine)
# metadata = MetaData(bind=engine)

# Base = get_declarative_base(metadata=metadata)


# # CreateTable
# class Rate(Base):
#     __tablename__ = "tabletest"
#     day = Column(types.Date, primary_key=True)
#     value = Column(types.Int32)

#     __table_args__ = (engines.Memory(),)


# Rate.__table__.create()


# # INSERT
# today = date.today()
# # rates = [{"day": today - timedelta(i), "value": 200 - i} for i in range(100)]
# r = Rate()
# r.day = date.today()
# r.value = 111
# session.add(r)
# session.commit()

# # or
# session.execute(Rate.__table__.insert(), rates)

# DELETE

# # GET
# count = (
#     session.query(func.count(Rate.day))
#     .filter(Rate.day > today - timedelta(20))
#     .scalar()
# )
# print(count)


import time
import datetime
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.order import Order

# GINKGODATA.drop_all()
GINKGODATA.create_all()
# t0 = datetime.datetime.now()
# for i in range(10000):
#     o = Order()
#     GINKGODATA.session.add(o)
#     GINKGODATA.session.commit()
#     print(f"{i}/10000", end="\r")
# t1 = datetime.datetime.now()

# print(t1 - t0)

# o = Order()
# o.delete()
# GINKGODATA.add(o)
# GINKGODATA.commit()

# o.query()

s = []

t2 = datetime.datetime.now()
for i in range(100):
    s.append(Order())
    print(f"{i}/100", end="\r")

GINKGODATA.add_all(s)
GINKGODATA.commit()
t3 = datetime.datetime.now()
print(t3 - t2)

r = GINKGODATA.session.query(Order).first()
print(r)
print(r.UUID)
print(r.ISDEL)
print(r.DATETIME)
# for i in r:
#     print(i)
