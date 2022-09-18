from sqlalchemy import inspect
from ginkgo.data.ginkgo_clickhouse import ginkgo_clickhouse as gc
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.config.secure import DATABASE
from ginkgo.data.models.base_model import BaseModel
from ginkgo.data.models.stock_info import StockInfo

insp = gc.insp
db_list = insp.get_schema_names()
gl.logger.debug(f"Databases:  {db_list}")

# Create Database
gc.engine.connect().execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")


# Create Tables

# [print(cls) for cls in BaseModel.__subclasses__()]
for i in BaseModel.__subclasses__():
    if i.__abstract__ == True:
        gl.logger.info(f"IGNORE {i.__tablename__}")
        continue
    if not gc.is_table_exsists(i.__tablename__):
        # i.__table__.create()
        i.create_table()
        gl.logger.info(f"CREATE TABLE {i.__tablename__}")
    else:
        gl.logger.info(f"TABLE {i.__tablename__} ALREADY EXISTS.")
    print(i)
