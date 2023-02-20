from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from ginkgo.data.ginkgo_clickhouse import ginkgo_clickhouse as gc
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.config.secure import DATABASE
from ginkgo.data.models.base_model import BaseModel
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.data.models.day_bar import DayBar
from ginkgo.config.secure import HOST, PORT, USERNAME, PASSWORD, DATABASE


uri = f"clickhouse+native://{USERNAME}:{PASSWORD}@{HOST}/default"
engine = create_engine(uri)
session = sessionmaker(engine)()
insp = inspect(engine)
db_list = insp.get_schema_names()

gl.logger.debug(f"Databases:  {db_list}")

# Create Database
engine.connect().execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")


uri = f"clickhouse+native://{USERNAME}:{PASSWORD}@{HOST}/{DATABASE}"
engine = create_engine(uri)
session = sessionmaker(engine)()
insp = inspect(engine)

# Create Tables

print("++++++++++++++++++++++")
[print(cls) for cls in BaseModel.__subclasses__()]
print("++++++++++++++++++++++")
for i in BaseModel.__subclasses__():
    if i.__abstract__ == True:
        gl.logger.info(f"IGNORE {i.__tablename__}")
        continue
    if not insp.has_table(i.__tablename__):
        # i.__table__.create()
        i.create_table()
        gl.logger.info(f"CREATE TABLE {i.__tablename__}")
    else:
        gl.logger.info(f"TABLE {i.__tablename__} ALREADY EXISTS.")
    print(i)
