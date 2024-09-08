# import unittest
# import uuid
# import base64
# import random
# import time
# import pandas as pd
# import datetime
# from ginkgo.libs.ginkgo_conf import GCONF
# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.data.models import MBacktest
# from ginkgo.data.ginkgo_data import GDATA


# class ModelBacktestTest(unittest.TestCase):
#     """
#     Examples for UnitTests of models Backtest
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelBacktestTest, self).__init__(*args, **kwargs)
#         self.test_count = 10
#         self.params = [
#             {
#                 "backtest_id": uuid.uuid4().hex,
#                 "start_at": datetime.datetime.now(),
#                 "content": b"whatareyounongshalei",
#                 "profit": 10002,
#                 "finish_at": datetime.datetime.now(),
#             },
#         ]

#     def test_ModelBacktest_Init(self) -> None:
#         o = MBacktest()

#     def test_ModelBacktest_SetFromData(self) -> None:
#         for i in self.params:
#             o = MBacktest()
#             o.set(
#                 i["backtest_id"],
#                 i["start_at"],
#                 i["content"],
#                 i["finish_at"],
#             )
#             self.assertEqual(o.backtest_id, i["backtest_id"])

#     def test_ModelBacktest_SetFromDataFrame(self) -> None:
#         pass

#     def test_ModelBacktest_Insert(self) -> None:
#         GDATA.create_table(MBacktest)
#         time.sleep(0.2)
#         for i in self.params:
#             size0 = GDATA.get_table_size(MBacktest)
#             o = MBacktest()
#             o.set(
#                 i["backtest_id"],
#                 i["start_at"],
#                 i["content"],
#             )
#             GDATA.add(o)
#             size1 = GDATA.get_table_size(MBacktest)
#             self.assertEqual(1, size1 - size0)

#     def test_ModelBacktest_BatchInsert(self) -> None:
#         GDATA.create_table(MBacktest)
#         times0 = random.random() * self.test_count
#         times0 = int(times0)
#         for j in range(times0):
#             size0 = GDATA.get_table_size(MBacktest)
#             l = []
#             times = random.random() * self.test_count
#             times = int(times)
#             for k in range(times):
#                 for i in self.params:
#                     o = MBacktest()
#                     o.set(
#                         i["backtest_id"],
#                         i["start_at"],
#                         i["content"],
#                     )
#                     l.append(o)
#             GDATA.add_all(l)
#             size1 = GDATA.get_table_size(MBacktest)
#             self.assertEqual(size1 - size0, len(l))

#     def test_ModelBacktest_Query(self) -> None:
#         GDATA.create_table(MBacktest)
#         o = MBacktest()
#         id = o.uuid
#         GDATA.add(o)
#         r = (
#             GDATA.get_driver(MBacktest)
#             .session.query(MBacktest)
#             .filter(MBacktest.uuid == id)
#             .first()
#         )
#         self.assertNotEqual(r, None)

#     def test_ModelBacktest_Update(self) -> None:
#         GDATA.create_table(MBacktest)
#         num = random.random() * self.test_count
#         num = int(num)
#         o = MBacktest()
#         id = o.uuid
#         o.set(id, "2023-11-19 00:43:21", b"123")
#         GDATA.add(o)
#         for i in range(num):
#             item = (
#                 GDATA.get_driver(MBacktest)
#                 .session.query(MBacktest)
#                 .filter(MBacktest.backtest_id == id)
#                 .first()
#             )
#             f = datetime.datetime.now()
#             item.finish_at = f
#             GDATA.get_driver(MBacktest).session.merge(item)
#             GDATA.get_driver(MBacktest).session.commit()
#             item2 = (
#                 GDATA.get_driver(MBacktest)
#                 .session.query(MBacktest)
#                 .filter(MBacktest.backtest_id == id)
#                 .first()
#             )
#             self.assertLessEqual(item2.finish_at - f, datetime.timedelta(seconds=0.5))
