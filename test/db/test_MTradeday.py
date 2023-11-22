# import unittest
# import base64
# import random
# import time
# import pandas as pd
# import datetime
# from ginkgo.libs.ginkgo_conf import GCONF

# from ginkgo.enums import (
#     SOURCE_TYPES,
#     DIRECTION_TYPES,
#     ORDER_TYPES,
#     ORDERSTATUS_TYPES,
#     FREQUENCY_TYPES,
#     CURRENCY_TYPES,
#     MARKET_TYPES,
# )

# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.data.models import (
#     MOrder,
#     MTradeDay,
#     MStockInfo,
#     MSignal,
#     MTick,
#     MAdjustfactor,
#     MBar,
# )

# from ginkgo.backtest.bar import Bar
# from ginkgo.backtest.tick import Tick
# from ginkgo.backtest.order import Order
# from ginkgo.data.ginkgo_data import GDATA
# from ginkgo.libs.ginkgo_logger import GLOG


# class ModelTradeDayTest(unittest.TestCase):
#     """
#     Unittest for Model TradeDay
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelTradeDayTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "date": datetime.datetime.now(),
#                 "is_open": True,
#                 "market": MARKET_TYPES.CHINA,
#                 "source": SOURCE_TYPES.SIM,
#             },
#             {
#                 "date": datetime.datetime.now(),
#                 "is_open": False,
#                 "market": MARKET_TYPES.NASDAQ,
#                 "source": SOURCE_TYPES.SIM,
#             },
#         ]

#     def test_ModelTradeDay_Init(self) -> None:
#         for i in self.params:
#             o = MTradeDay()

#     def test_ModelTradeDay_SetFromData(self) -> None:
#         for i in self.params:
#             o = MTradeDay()
#             o.set(i["market"], i["is_open"], i["date"])
#             o.set_source(i["source"])
#             self.assertEqual(o.timestamp, i["date"])
#             self.assertEqual(o.is_open, i["is_open"])
#             self.assertEqual(o.market, i["market"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelTradeDay_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             o = MTradeDay()
#             df = pd.DataFrame.from_dict(i, orient="index")
#             o.set(df[0])
#             self.assertEqual(o.timestamp, i["date"])
#             self.assertEqual(o.is_open, i["is_open"])
#             self.assertEqual(o.market, i["market"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelTradeDay_Insert(self) -> None:
#         GDATA.create_table(MTradeDay)
#         for i in self.params:
#             size0 = GDATA.get_table_size(MTradeDay)
#             o = MTradeDay()
#             GDATA.add(o)
#             size1 = GDATA.get_table_size(MTradeDay)
#             self.assertEqual(1, size1 - size0)

#     def test_ModelTradeDay_BatchInsert(self) -> None:
#         GDATA.create_table(MTradeDay)
#         times = random.random() * 500
#         times = int(times)
#         for j in range(times):
#             print(f"ModelTradeDay BatchInsert Test: {j+1}", end="\r")
#             size0 = GDATA.get_table_size(MTradeDay)
#             s = []
#             num = random.random() * 500
#             num = int(num)
#             for i in range(num):
#                 o = MTradeDay()
#                 s.append(o)
#             GDATA.add_all(s)
#             size1 = GDATA.get_table_size(MTradeDay)
#             self.assertEqual(len(s), size1 - size0)

#     def test_ModelTradeDay_Query(self) -> None:
#         GDATA.create_table(MTradeDay)
#         o = MTradeDay()
#         GDATA.add(o)
#         r = GDATA.get_driver(MTradeDay).session.query(MTradeDay).first()
#         self.assertNotEqual(r, None)
