import pandas as pd
import datetime
from ginkgo.data.ginkgo_clickhouse import ginkgo_clickhouse as gc
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.data.models.base_model import BaseModel
from ginkgo.data.models.day_bar import DayBar


# Update stockinfo
# gc.update_all_stockinfo()
# gc.get_stockinfo()
# gc.update_all_daybar()

df = gc.get_daybar(code="sz.000610", date_start="2009-12-28", date_end="2009-12-28")


day = DayBar()
day.df_convert(df)
day.date = datetime.datetime.now()
day.date = datetime.datetime(2022, 12, 23, 2, 2, 2)
gc.insert_daybar(day)
gc.insert_daybar(df)
l = []
for i in range(5):
    item = DayBar()
    item.date = datetime.datetime.now()
    l.append(item)
gc.insert_daybar(l)


# print(type(df))
# print(df.loc[:, "date"])
# gc.insert_daybars(daybars=df)

# gc.get_codes()

# a = DayBar()
# print(a)
