from ginkgo.data.ginkgo_clickhouse import ginkgo_clickhouse as gc
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.data.models.base_model import BaseModel
from ginkgo.data.models.day_bar import DayBar
import pandas as pd

import datetime


# Update stockinfo
gc.update_all_stockinfo()
gc.get_stockinfo()
print(gc.get_stockinfo())


gc.update_all_daybar()

# gc.get_codes()
