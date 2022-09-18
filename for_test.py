from ginkgo.data.ginkgo_clickhouse import ginkgo_clickhouse as gc
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.data.models.base_model import BaseModel

import datetime


gc.update_all_stockinfo()
# gc.get_stockinfo()
