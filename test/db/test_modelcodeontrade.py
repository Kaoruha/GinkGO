import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GLOG
from ginkgo.backtest.tick import Tick
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MCodeOnTrade
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
from ginkgo.libs.ginkgo_conf import GCONF


# class ModelCodeOnTradeTest(unittest.TestCase):
#     """
#     UnitTest for ModelCodeOntrade.
#     """

#     # Init
#     # set data from dataframe
#     # store in to GDATA
#     # query from GDATA

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelCodeOnTradeTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "source": SOURCE_TYPES.SIM,
#                 "code": "11166",
#                 "code_name": "testcode111",
#                 "trade_status": True,
#                 "market": MARKET_TYPES.CHINA,
#                 "timestamp": datetime.datetime.now().strftime("%Y-%m-%d"),
#             }
#         ]

#     def test_ModelCodeOntrade_Init(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             item = MCodeOnTrade()
#             item.set(
#                 i["code"],
#                 i["code_name"],
#                 i["trade_status"],
#                 i["market"],
#                 i["timestamp"],
#             )
#             item.set_source(i["source"])
#             self.assertEqual(item.code, i["code"])
#             self.assertEqual(item.code_name, i["code_name"])
#             self.assertEqual(item.trade_status, i["trade_status"])
#             self.assertEqual(item.source, i["source"])

#     def test_ModelCodeOntrade_SetFromDataframe(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             data = {
#                 "code": i["code"],
#                 "code_name": i["code_name"],
#                 "trade_status": i["trade_status"],
#                 "market": i["market"],
#                 "timestamp": i["timestamp"],
#                 "source": i["source"],
#             }
#             c = MCodeOnTrade()
#             c.set(pd.Series(data))

#             self.assertEqual(c.code, i["code"])
#             self.assertEqual(c.code_name, i["code_name"])
#             self.assertEqual(c.trade_status, i["trade_status"])
#             self.assertEqual(c.source, i["source"])

#     def test_ModelCodeOntrade_Insert(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         GDATA.drop_table(MCodeOnTrade)
#         GDATA.create_table(MCodeOnTrade)
#         try:
#             o = MCodeOnTrade()
#             GDATA.add(o)
#             GDATA.commit()
#         except Exception as e:
#             result = False
#         self.assertEqual(result, True)

#     def test_ModelCodeOntrade_BatchInsert(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True

#         GDATA.drop_table(MCodeOnTrade)
#         GDATA.create_table(MCodeOnTrade)
#         try:
#             s = []

#             for i in range(10):
#                 o = MCodeOnTrade()
#                 s.append(o)

#             GDATA.add_all(s)
#             GDATA.commit()
#         except Exception as e:
#             result = False
#         self.assertEqual(result, True)

#     def test_ModelCodeOntrade_Query(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)

#         GDATA.drop_table(MCodeOnTrade)
#         GDATA.create_table(MCodeOnTrade)
#         o = MCodeOnTrade()
#         GDATA.add(o)
#         GDATA.commit()
#         r = GDATA.session.query(MCodeOnTrade).first()
#         self.assertNotEqual(r, None)
#         self.assertNotEqual(r.code, None)
