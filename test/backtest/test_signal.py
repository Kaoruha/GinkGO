# import unittest
# import time
# import datetime
# import pandas as pd
# from ginkgo.backtest.signal import Signal
# from ginkgo.data.models import MSignal
# from ginkgo import GLOG
# from ginkgo.data.ginkgo_data import GDATA
# from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


# class SignalTest(unittest.TestCase):
#     """
#     UnitTest for Signal.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(SignalTest, self).__init__(*args, **kwargs)
#         self.dev = False
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
#         result = False
#         s = Signal()

#     def test_Signal_SetFromData(self) -> None:
#         for item in self.params:
#             s = Signal()
#             s.set(item["code"], item["direction"], item["timestamp"], item["uuid"])
#             s.set_source(SOURCE_TYPES.TEST)
#             self.assertEqual(s.code, item["code"])
#             self.assertEqual(s.direction, item["direction"])

#     def test_Signal_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             s = Signal()
#             s.set(df)
#             self.assertEqual(s.code, i["code"])
#             self.assertEqual(s.uuid, i["uuid"])
#             self.assertEqual(s.direction, i["direction"])
#             self.assertEqual(s.source, i["source"])
