# import unittest
# import time
# import datetime
# import pandas as pd
# from ginkgo.backtest.signal import Signal
# from ginkgo.data.models import MSignal
# from ginkgo.data.ginkgo_data import GDATA
# from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
# from ginkgo.libs import datetime_normalize, GLOG


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
#                 "uuid": "test_uuid",
#             },
#         ]

#     def test_Signal_Init(self) -> None:
#         for i in self.params:
#             s = Signal()

#     def test_Signal_SetFromData(self) -> None:
#         for item in self.params:
#             s = Signal()
#             s.set(item["code"], item["direction"], item["timestamp"], item["uuid"])
#             s.set_source(item["source"])
#             self.assertEqual(s.code, item["code"])
#             self.assertEqual(s.timestamp, datetime_normalize(item["timestamp"]))
#             self.assertEqual(s.direction, item["direction"])
#             self.assertEqual(s.source, item["source"])
#             self.assertEqual(s.uuid, item["uuid"])

#     def test_Signal_SetFromDataFrame(self) -> None:
#         for item in self.params:
#             df = pd.DataFrame.from_dict(item, orient="index")[0]
#             s = Signal()
#             s.set(df)
#             s.set_source(item["source"])
#             self.assertEqual(s.code, item["code"])
#             self.assertEqual(s.timestamp, datetime_normalize(item["timestamp"]))
#             self.assertEqual(s.direction, item["direction"])
#             self.assertEqual(s.source, item["source"])
#             self.assertEqual(s.uuid, item["uuid"])
