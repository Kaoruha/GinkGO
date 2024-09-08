# import unittest
# import uuid
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
#     MPosition,
# )

# from ginkgo.data.ginkgo_data import GDATA
# from ginkgo.libs.ginkgo_logger import GLOG


# class ModelPositionTest(unittest.TestCase):
#     """
#     UnitTest for ModelPosition.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelPositionTest, self).__init__(*args, **kwargs)
#         self.test_count = 10
#         self.params = [
#             {
#                 "backtest_id": "testbacktestid1123",
#                 "timestamp": datetime.datetime.now(),
#                 "code": "testordercode",
#                 "volume": 1000,
#                 "cost": 10.92,
#             }
#         ]

#     def test_ModelPosition_Init(self) -> None:
#         o = MPosition()

#     def test_ModelPosition_SetFromData(self) -> None:
#         for i in self.params:
#             o = MPosition()
#             o.set(
#                 i["backtest_id"],
#                 i["timestamp"],
#                 i["code"],
#                 i["volume"],
#                 i["cost"],
#             )
#             self.assertEqual(o.backtest_id, i["backtest_id"])
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.volume, i["volume"])
#             self.assertEqual(o.cost, i["cost"])

#     def test_ModelPosition_SetFromDataFrame(self) -> None:
#         pass

#     def test_ModelPosition_Insert(self) -> None:
#         GDATA.create_table(MPosition)
#         time.sleep(0.2)
#         for i in self.params:
#             size0 = GDATA.get_table_size(MPosition)
#             o = MPosition()
#             o.set(
#                 i["backtest_id"],
#                 i["timestamp"],
#                 i["code"],
#                 i["volume"],
#                 i["cost"],
#             )
#             GDATA.add(o)
#             size1 = GDATA.get_table_size(MPosition)
#             self.assertEqual(1, size1 - size0)

#     def test_ModelPosition_BatchInsert(self) -> None:
#         GDATA.create_table(MPosition)
#         times0 = random.random() * self.test_count
#         times0 = int(times0)
#         for j in range(times0):
#             size0 = GDATA.get_table_size(MPosition)
#             l = []
#             times = random.random() * self.test_count
#             times = int(times)
#             for k in range(times):
#                 for i in self.params:
#                     o = MPosition()
#                     o.set(
#                         i["backtest_id"],
#                         i["timestamp"],
#                         i["code"],
#                         i["volume"],
#                         i["cost"],
#                     )
#                     l.append(o)
#             GDATA.add_all(l)
#             size1 = GDATA.get_table_size(MPosition)
#             self.assertEqual(size1 - size0, len(l))

#     def test_ModelPosition_Query(self) -> None:
#         GDATA.create_table(MPosition)
#         o = MPosition()
#         id = o.uuid
#         GDATA.add(o)
#         r = (
#             GDATA.get_driver(MPosition)
#             .session.query(MPosition)
#             .filter(MPosition.uuid == id)
#             .first()
#         )
#         self.assertNotEqual(r, None)
