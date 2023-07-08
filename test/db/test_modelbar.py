import unittest
import time
import datetime
from ginkgo.libs import GLOG
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MBar
from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES
from ginkgo.libs.ginkgo_conf import GCONF


# class ModelBarTest(unittest.TestCase):
#     """
#     UnitTest for Bar.
#     """

#     # Init
#     # set data from bar
#     # store in to GDATA
#     # query from GDATA

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelBarTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "code": "testcode",
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "open": 2,
#                 "high": 2.44,
#                 "low": 1,
#                 "close": 1.99,
#                 "volume": 23331,
#                 "timestamp": datetime.datetime.now(),
#                 "frequency": FREQUENCY_TYPES.DAY,
#                 "source": SOURCE_TYPES.SIM,
#             }
#         ]

#     def test_ModelBar_Init(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         for i in self.params:
#             try:
#                 o = MBar()
#             except Exception as e:
#                 result = False
#         self.assertEqual(result, True)

#     def test_ModelBar_SetFromData(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             o = MBar()
#             o.set(
#                 i["code"],
#                 i["open"],
#                 i["high"],
#                 i["low"],
#                 i["close"],
#                 i["volume"],
#                 i["frequency"],
#                 i["timestamp"],
#             )
#             o.set_source(i["source"])
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.open, i["open"])
#             self.assertEqual(o.high, i["high"])
#             self.assertEqual(o.low, i["low"])
#             self.assertEqual(o.close, i["close"])
#             self.assertEqual(o.volume, i["volume"])
#             self.assertEqual(o.timestamp, i["timestamp"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelBar_SetFromDataFrame(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             b = Bar(
#                 i["code"],
#                 i["open"],
#                 i["high"],
#                 i["low"],
#                 i["close"],
#                 i["volume"],
#                 i["frequency"],
#                 i["timestamp"],
#             )
#             o = MBar()
#             o.set(b.to_dataframe)
#             o.set_source(i["source"])
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.open, i["open"])
#             self.assertEqual(o.high, i["high"])
#             self.assertEqual(o.low, i["low"])
#             self.assertEqual(o.close, i["close"])
#             self.assertEqual(o.volume, i["volume"])
#             self.assertEqual(o.timestamp, i["timestamp"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelBar_Insert(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         GDATA.drop_table(MBar)
#         GDATA.create_table(MBar)
#         try:
#             o = MBar()
#             GDATA.add(o)
#             GDATA.commit()
#         except Exception as e:
#             result = False

#         self.assertEqual(result, True)

#     def test_ModelBar_BatchInsert(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         GDATA.drop_table(MBar)
#         GDATA.create_table(MBar)
#         try:
#             s = []
#             for i in range(10):
#                 o = MBar()
#                 s.append(o)
#             GDATA.add_all(s)
#             GDATA.commit()
#         except Exception as e:
#             result = False

#         self.assertEqual(result, True)

#     def test_ModelBar_Query(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         GDATA.drop_table(MBar)
#         GDATA.create_table(MBar)
#         try:
#             o = MBar()
#             GDATA.add(o)
#             GDATA.commit()
#             r = GDATA.session.query(MBar).first()
#         except Exception as e:
#             result = False

#         self.assertNotEqual(r, None)
#         self.assertEqual(result, True)
