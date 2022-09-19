from ginkgo.data.ginkgo_clickhouse import ginkgo_clickhouse as gc
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.data.models.base_model import BaseModel
from ginkgo.data.models.day_bar import DayBar
import pandas as pd

import datetime


# gc.update_all_stockinfo()
# gc.get_stockinfo()
# print(gc.get_stockinfo())


import datetime

# dt = datetime.datetime(2021, 1, 3, 0, 0, 0)
# d = DayBar(date=dt, code="hah")
# l = []
# l.append(d)
# gc.insert_daybars(l)

# gc.update_all_stockinfo()
gc.update_all_daybar()

# gc.get_codes()
