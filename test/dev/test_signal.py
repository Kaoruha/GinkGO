# import unittest
# import time
# import datetime
# import pandas as pd
# from ginkgo.libs import GINKGOLOGGER as gl
# from ginkgo.backtest.signal import Signal
# from ginkgo.data.models import MSignal
# from ginkgo.libs.ginkgo_conf import GINKGOCONF
# from ginkgo.data.ginkgo_data import GINKGODATA
# from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


# class SignalTest(unittest.TestCase):
#     """
#     UnitTest for Signal.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(SignalTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "code": "sh.0000001",
#                 "timestamp": "2020-01-01 02:02:32",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "source": SOURCE_TYPES.SIM,
#             },
#         ]

#     def test_Signal_Init(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         result = False
#         try:
#             s = Signal()
#             result = True
#         except Exception as e:
#             pass

#         self.assertEqual(result, True)

#     def test_Signal_Set(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         for item in self.params:
#             s = Signal()
#             s.set(
#                 item["code"],
#                 item["direction"],
#                 item["timestamp"],
#                 item["source"],
#             )
#             self.assertEqual(s.code, item["code"])
#             self.assertEqual(s.direction, item["direction"])
#             self.assertEqual(s.source, item["source"])

#     def test_Signal_SetFromDataFrame(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         for item in self.params:
#             data = {
#                 "code": item["code"],
#                 "direction": item["direction"],
#                 "timestamp": item["timestamp"],
#                 "source": item["source"],
#                 "uuid": "",
#             }
#             df = pd.Series(data)
#             s = Signal()
#             s.set(df)
#             self.assertEqual(s.code, item["code"])
#             self.assertEqual(s.direction, item["direction"])
#             self.assertEqual(s.source, item["source"])


# def test_Signal_SetFromModel(self) -> None:
#     time.sleep(GINKGOCONF.HEARTBEAT)
#     for item in self.params:
#         data = {
#             "timestamp": item["timestamp"],
#             "code": item["code"],
#             "direction": item["direction"],
#             "type": item["type"],
#             "volume": item["volume"],
#             "status": 1,
#             "limit_price": item["limit_price"],
#         }
#         df = pd.Series(data)
#         mo = MSignal()
#         mo.set(df)
#         GINKGODATA.drop_table(MSignal)
#         GINKGODATA.create_table(MSignal)
#         GINKGODATA.add(mo)
#         GINKGODATA.commit()
#         filter_rs: MSignal = GINKGODATA.get_order(mo.uuid)
#         new_df = filter_rs.to_dataframe
#         o = Signal()
#         o.set(new_df)
#         self.assertEqual(o.code, item["code"])
#         self.assertEqual(o.direction, item["direction"])
#         self.assertEqual(o.type, item["type"])
#         self.assertEqual(o.volume, item["volume"])
#         self.assertEqual(o.limit_price, item["limit_price"])
