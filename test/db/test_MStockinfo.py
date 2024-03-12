import unittest
import base64
import random
import time
import pandas as pd
import datetime
from ginkgo.libs.ginkgo_conf import GCONF

from ginkgo.enums import (
    SOURCE_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
)

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import (
    MOrder,
    MTradeDay,
    MStockInfo,
    MSignal,
    MTick,
    MAdjustfactor,
    MBar,
)

from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_logger import GLOG


class ModelStockInfoTest(unittest.TestCase):
    """
    UnitTest for StockInfo.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelStockInfoTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testcode",
                "code_name": "testname",
                "industry": "test industry",
                "currency": CURRENCY_TYPES.CNY,
                "list_date": datetime.datetime.now(),
                "delist_date": datetime.datetime.now(),
                "timestamp": datetime.datetime.now(),
                "source": SOURCE_TYPES.SIM,
            },
            {
                "code": "testcode2",
                "code_name": "testname222",
                "industry": "test industry222",
                "currency": CURRENCY_TYPES.USD,
                "list_date": datetime.datetime.now(),
                "delist_date": datetime.datetime.now(),
                "timestamp": datetime.datetime.now(),
                "source": SOURCE_TYPES.SIM,
            },
        ]

    def test_ModelStockInfo_Init(self) -> None:
        for i in self.params:
            o = MStockInfo()


#     def test_ModelStockInfo_SetFromData(self) -> None:
#         for i in self.params:
#             o = MStockInfo()
#             o.set(
#                 i["code"],
#                 i["code_name"],
#                 i["industry"],
#                 i["currency"],
#                 i["list_date"],
#                 i["delist_date"],
#             )
#             o.set_source(i["source"])
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.code_name, i["code_name"])
#             self.assertEqual(o.industry, i["industry"])
#             self.assertEqual(o.currency, i["currency"])
#             self.assertEqual(o.list_date, i["list_date"])
#             self.assertEqual(o.delist_date, i["delist_date"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelStockInfo_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             o = MStockInfo()
#             df = pd.DataFrame.from_dict(i, orient="index")
#             o.set(df[0])
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.code_name, i["code_name"])
#             self.assertEqual(o.industry, i["industry"])
#             self.assertEqual(o.currency, i["currency"])
#             self.assertEqual(o.list_date, i["list_date"])
#             self.assertEqual(o.delist_date, i["delist_date"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelStockInfo_Insert(self) -> None:
#         GDATA.create_table(MStockInfo)
#         times = random.random() * 500
#         times = int(times)
#         for j in range(times):
#             print(f"ModelStockInfo Insert Test : {j+1}", end="\r")
#             for i in self.params:
#                 size0 = GDATA.get_table_size(MStockInfo)
#                 o = MStockInfo()
#                 GDATA.add(o)
#                 size1 = GDATA.get_table_size(MStockInfo)
#                 self.assertEqual(1, size1 - size0)

#     def test_ModelStockInfo_BatchInsert(self) -> None:
#         GDATA.create_table(MStockInfo)
#         times = random.random() * 500
#         times = int(times)
#         for j in range(times):
#             size0 = GDATA.get_table_size(MStockInfo)
#             print(f"ModelStockInfo Insert Test : {j+1}", end="\r")
#             s = []
#             for i in self.params:
#                 o = MStockInfo()
#                 s.append(o)
#             GDATA.add_all(s)
#             size1 = GDATA.get_table_size(MStockInfo)
#             self.assertEqual(len(s), size1 - size0)

#     def test_ModelStockInfo_Query(self) -> None:
#         GDATA.create_table(MStockInfo)
#         o = MStockInfo()
#         GDATA.add(o)
#         r = GDATA.get_driver(MStockInfo).session.query(MStockInfo).first()
#         self.assertNotEqual(r, None)
