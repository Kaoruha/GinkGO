# import unittest
# import pandas as pd
# import datetime
# from time import sleep
# from ginkgo.backtest.bar import Bar
# from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
# from ginkgo import GLOG
# from ginkgo.libs import datetime_normalize


# class BarTest(unittest.TestCase):
#     """
#     UnitTest for Bar.
#     """

#     # Init
#     # Change
#     # Amplitude

#     def __init__(self, *args, **kwargs) -> None:
#         super(BarTest, self).__init__(*args, **kwargs)
#         self.dev = False
#         self.params = [
#             {
#                 "code": "unittest_simcode",
#                 "open": 10.1,
#                 "high": 11,
#                 "low": 9,
#                 "close": 9.51,
#                 "volume": 1991231,
#                 "frequency": FREQUENCY_TYPES.DAY,
#                 "timestamp": "2020-01-01 02:02:32",
#                 "source": SOURCE_TYPES.TEST,
#             },
#             {
#                 "code": "sh.0000001",
#                 "open": 10,
#                 "high": 11.1,
#                 "low": 9.6,
#                 "close": 9.4,
#                 "volume": 10022,
#                 "frequency": FREQUENCY_TYPES.DAY,
#                 "timestamp": datetime.datetime.now(),
#                 "source": SOURCE_TYPES.SINA,
#             },
#         ]

#     def test_Bar_Init(self) -> None:
#         for i in self.params:
#             b = Bar()

#     def test_Bar_Set(self) -> None:
#         for i in self.params:
#             b = Bar()
#             b.set(
#                 i["code"],
#                 i["open"],
#                 i["high"],
#                 i["low"],
#                 i["close"],
#                 i["volume"],
#                 i["frequency"],
#                 i["timestamp"],
#             )
#             b.set_source(i["source"])
#             self.assertEqual(b.code, i["code"])
#             self.assertEqual(b.open, i["open"])
#             self.assertEqual(b.high, i["high"])
#             self.assertEqual(b.low, i["low"])
#             self.assertEqual(b.close, i["close"])
#             self.assertEqual(b.volume, i["volume"])
#             self.assertEqual(b.source, i["source"])
#             self.assertEqual(b.timestamp, datetime_normalize(i["timestamp"]))
#             self.assertEqual(b.frequency, i["frequency"])

#     def test_Bar_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")
#             b = Bar()
#             df = df[0]
#             b.set(df)
#             b.set_source(i["source"])
#             self.assertEqual(b.code, df["code"])
#             self.assertEqual(b.open, df["open"])
#             self.assertEqual(b.high, df["high"])
#             self.assertEqual(b.low, df["low"])
#             self.assertEqual(b.close, df["close"])
#             self.assertEqual(b.volume, df["volume"])
#             self.assertEqual(b.source, df["source"])
#             self.assertEqual(b.timestamp, datetime_normalize(df["timestamp"]))
#             self.assertEqual(b.frequency, df["frequency"])

#     def test_Bar_Change(self) -> None:
#         for i in self.params:
#             b = Bar()
#             b.set(
#                 i["code"],
#                 i["open"],
#                 i["high"],
#                 i["low"],
#                 i["close"],
#                 i["volume"],
#                 i["frequency"],
#                 i["timestamp"],
#             )
#             b.set_source(i["source"])
#             r_expect = round(i["close"] - i["open"], 2)
#             self.assertEqual(b.chg, r_expect)

#     def test_Bar_Amplitude(self) -> None:
#         for i in self.params:
#             b = Bar()
#             b.set(
#                 i["code"],
#                 i["open"],
#                 i["high"],
#                 i["low"],
#                 i["close"],
#                 i["volume"],
#                 i["frequency"],
#                 i["timestamp"],
#             )
#             b.set_source(i["source"])
#             self.assertEqual(b.amplitude, i["high"] - i["low"])
