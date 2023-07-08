import unittest
import time
import datetime
from ginkgo.libs import GLOG
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MTradeDay
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
from ginkgo.libs.ginkgo_conf import GCONF


class ModelTradeDayTest(unittest.TestCase):
    """
    UnitTest for Trade_day.
    """

    # Init
    # set data from TradeDay
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTradeDayTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "date": "2020-01-01",
                "is_open": False,
                "source": SOURCE_TYPES.TUSHARE,
                "maket": MARKET_TYPES.CHINA,
            }
        ]

    def test_ModelTradeDay_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        print(1111)
        for i in self.params:
            try:
                o = MTradeDay()
                o.set_source(i["source"])
            except Exception as e:
                print(e)
                result = False
        self.assertEqual(result, True)


#     def test_ModelTradeDay_SetFromData(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             o = MTradeDay()
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

#     def test_ModelTradeDay_SetFromDataFrame(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             b = TradeDay(
#                 i["code"],
#                 i["open"],
#                 i["high"],
#                 i["low"],
#                 i["close"],
#                 i["volume"],
#                 i["frequency"],
#                 i["timestamp"],
#             )
#             o = MTradeDay()
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

#     def test_ModelTradeDay_Insert(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         GDATA.drop_table(MTradeDay)
#         GDATA.create_table(MTradeDay)
#         try:
#             o = MTradeDay()
#             GDATA.add(o)
#             GDATA.commit()
#         except Exception as e:
#             result = False

#         self.assertEqual(result, True)

#     def test_ModelTradeDay_BatchInsert(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         GDATA.drop_table(MTradeDay)
#         GDATA.create_table(MTradeDay)
#         try:
#             s = []
#             for i in range(10):
#                 o = MTradeDay()
#                 s.append(o)
#             GDATA.add_all(s)
#             GDATA.commit()
#         except Exception as e:
#             result = False

#         self.assertEqual(result, True)

#     def test_ModelTradeDay_Query(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = True
#         GDATA.drop_table(MTradeDay)
#         GDATA.create_table(MTradeDay)
#         try:
#             o = MTradeDay()
#             GDATA.add(o)
#             GDATA.commit()
#             r = GDATA.session.query(MTradeDay).first()
#         except Exception as e:
#             result = False

#         self.assertNotEqual(r, None)
#         self.assertEqual(result, True)
