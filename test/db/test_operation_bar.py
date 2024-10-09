# import unittest
# import datetime
# import time
# import uuid
# import random

# from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
# from ginkgo.data.drivers import create_table, drop_table, get_table_size
# from ginkgo.data.models import MBar
# from ginkgo.backtest import Bar
# from ginkgo.data.operations.bar_crud import *

# class OperationBarTest(unittest.TestCase):
#     """
#     UnitTest for Bar CRUD
#     """

#     @classmethod
#     def setUpClass(cls):
#         cls.model = MBar
#         drop_table(cls.model)
#         time.sleep(0.1)
#         create_table(cls.model)
#         cls.count = 10
#         cls.params = [
#             {
#                 "code": uuid.uuid4().hex,
#                 "open": round(random.uniform(1.5, 5.5), 2),
#                 "high": round(random.uniform(1.5, 5.5), 2),
#                 "low": round(random.uniform(1.5, 5.5), 2),
#                 "close": round(random.uniform(1.5, 5.5), 2),
#                 "volume": random.randint(100, 1000),
#                 "frequency": FREQUENCY_TYPES.DAY,
#                 "timestamp": datetime.datetime.now(),
#                 "source": SOURCE_TYPES.OTHER,
#             }
#             for i in range(cls.count)
#         ]

#     def test_OperationBar_insert(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             add_bar(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(size0 + 1, size1)

#     def test_OperationBar_bulkinsert(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(**i)
#             l.append(item)
#         add_bars(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(self.count, size1 - size0)

#     def test_OperationBar_update(self) -> None:
#         # No update
#         pass

#     def test_OperationBar_delete_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             df = add_bar(**i)
#             uuid = df.uuid
#             size1 = get_table_size(self.model)
#             self.assertEqual(size0 + 1, size1)
#             delete_bar_by_id(uuid)
#             time.sleep(0.1)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationBar_softdelete_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             df = add_bar(**i)
#             uuid = df.uuid
#             size1 = get_table_size(self.model)
#             self.assertEqual(size0 + 1, size1)
#             softdelete_bar_by_id(uuid)
#             time.sleep(0.1)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationBar_delete_by_code(self) -> None:
#         code = uuid.uuid4().hex
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(
#                 code=code,
#                 open=i["open"],
#                 high=i["high"],
#                 low=i["low"],
#                 close=i["close"],
#                 volume=i["volume"],
#                 frequency=i["frequency"],
#                 timestamp=i["timestamp"],
#                 source=i["source"],
#             )
#             l.append(item)
#         add_bars(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(self.count, size1 - size0)
#         delete_bar_by_code_and_date_range(code=code)
#         size2 = get_table_size(self.model)
#         self.assertEqual(size2, size0)

#     def test_OperationBar_delete_by_code_and_date_range(self) -> None:
#         code = uuid.uuid4().hex
#         l = []
#         size0 = get_table_size(self.model)
#         now = datetime.datetime.now()
#         for i in self.params:
#             item = self.model(
#                 code=code,
#                 open=i["open"],
#                 high=i["high"],
#                 low=i["low"],
#                 close=i["close"],
#                 volume=i["volume"],
#                 frequency=i["frequency"],
#                 timestamp=now,
#                 source=i["source"],
#             )
#             l.append(item)
#         add_bars(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(self.count, size1 - size0)
#         delete_bar_by_code_and_date_range(code=code, start_date=now, end_date=now)
#         size2 = get_table_size(self.model)
#         self.assertEqual(size2, size0)

#     def test_OperationBar_exists(self) -> None:
#         pass

#     def test_OperationBar_get(self) -> None:
#         code = uuid.uuid4().hex
#         l = []
#         size0 = get_table_size(self.model)
#         item1 = self.model()
#         item1.update(
#             code,
#             open=round(random.uniform(1.5, 5.5), 2),
#             high=round(random.uniform(1.5, 5.5), 2),
#             low=round(random.uniform(1.5, 5.5), 2),
#             close=round(random.uniform(1.5, 5.5), 2),
#             volume=random.randint(100, 1000),
#             frequency=FREQUENCY_TYPES.DAY,
#             timestamp="2020-01-01",
#             source=SOURCE_TYPES.OTHER,
#         )
#         l.append(item1)
#         item2 = self.model()
#         item2.update(
#             code,
#             open=round(random.uniform(1.5, 5.5), 2),
#             high=round(random.uniform(1.5, 5.5), 2),
#             low=round(random.uniform(1.5, 5.5), 2),
#             close=round(random.uniform(1.5, 5.5), 2),
#             volume=random.randint(100, 1000),
#             frequency=FREQUENCY_TYPES.DAY,
#             timestamp="2020-01-02",
#             source=SOURCE_TYPES.OTHER,
#         )
#         l.append(item2)
#         item3 = self.model()
#         item3.update(
#             code,
#             open=round(random.uniform(1.5, 5.5), 2),
#             high=round(random.uniform(1.5, 5.5), 2),
#             low=round(random.uniform(1.5, 5.5), 2),
#             close=round(random.uniform(1.5, 5.5), 2),
#             volume=random.randint(100, 1000),
#             frequency=FREQUENCY_TYPES.DAY,
#             timestamp="2020-01-03",
#             source=SOURCE_TYPES.OTHER,
#         )
#         l.append(item3)
#         add_bars(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(3, size1 - size0)

#         res = get_bar(code=code)
#         self.assertEqual(3, len(res))

#         res = get_bar(code=code, start_date="2020-01-02")
#         self.assertEqual(2, len(res))

#         res = get_bar(code=code, start_date="2020-01-02", end_date="2020-01-02")
#         self.assertEqual(1, len(res))

#         res = get_bar(code=code, page=0, page_size=2)
#         self.assertEqual(2, len(res))

#         res = get_bar(code=code, page=1, page_size=2)
#         self.assertEqual(1, len(res))

#     def test_OperationBar_get_in_dataframe(self) -> None:
#         code = uuid.uuid4().hex
#         l = []
#         size0 = get_table_size(self.model)
#         item1 = self.model()
#         item1.update(
#             code,
#             open=round(random.uniform(1.5, 5.5), 2),
#             high=round(random.uniform(1.5, 5.5), 2),
#             low=round(random.uniform(1.5, 5.5), 2),
#             close=round(random.uniform(1.5, 5.5), 2),
#             volume=random.randint(100, 1000),
#             frequency=FREQUENCY_TYPES.DAY,
#             timestamp="2020-01-01",
#             source=SOURCE_TYPES.OTHER,
#         )
#         l.append(item1)
#         item2 = self.model()
#         item2.update(
#             code,
#             open=round(random.uniform(1.5, 5.5), 2),
#             high=round(random.uniform(1.5, 5.5), 2),
#             low=round(random.uniform(1.5, 5.5), 2),
#             close=round(random.uniform(1.5, 5.5), 2),
#             volume=random.randint(100, 1000),
#             frequency=FREQUENCY_TYPES.DAY,
#             timestamp="2020-01-02",
#             source=SOURCE_TYPES.OTHER,
#         )
#         l.append(item2)
#         item3 = self.model()
#         item3.update(
#             code,
#             open=round(random.uniform(1.5, 5.5), 2),
#             high=round(random.uniform(1.5, 5.5), 2),
#             low=round(random.uniform(1.5, 5.5), 2),
#             close=round(random.uniform(1.5, 5.5), 2),
#             volume=random.randint(100, 1000),
#             frequency=FREQUENCY_TYPES.DAY,
#             timestamp="2020-01-03",
#             source=SOURCE_TYPES.OTHER,
#         )
#         l.append(item3)
#         add_bars(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(3, size1 - size0)

#         res = get_bar(code=code, as_dataframe=True)
#         self.assertEqual(3, res.shape[0])

#         res = get_bar(code=code, start_date="2020-01-02", as_dataframe=True)
#         self.assertEqual(2, res.shape[0])

#         res = get_bar(code=code, start_date="2020-01-02", end_date="2020-01-02", as_dataframe=True)
#         self.assertEqual(1, res.shape[0])

#         res = get_bar(code=code, page=0, page_size=2, as_dataframe=True)
#         self.assertEqual(2, res.shape[0])

#         res = get_bar(code=code, page=1, page_size=2, as_dataframe=True)
#         self.assertEqual(1, res.shape[0])

#     def test_OperationBar_exceptions(self) -> None:
#         pass
