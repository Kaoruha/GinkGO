# import unittest
# import time
# import uuid
# import random
# import datetime

# from ginkgo.enums import SOURCE_TYPES
# from ginkgo.data.drivers import get_table_size, create_table, drop_table
# from ginkgo.data.models import MAnalyzerRecord
# from ginkgo.data.operations.analyzer_record_crud import *


# class OperationAnalyzerRecordTest(unittest.TestCase):
#     """
#     UnitTest for Analyzer CRUD
#     """

#     @classmethod
#     def setUpClass(cls):
#         cls.model = MAnalyzerRecord
#         drop_table(cls.model)
#         time.sleep(0.1)
#         create_table(cls.model)
#         cls.count = 10
#         cls.params = [
#             {
#                 "portfolio_id": uuid.uuid4().hex,
#                 "timestamp": datetime.datetime.now(),
#                 "value": round(random.uniform(1.5, 5.5), 2),
#                 "name": uuid.uuid4().hex,
#                 "analyzer_id": uuid.uuid4().hex,
#             }
#             for i in range(cls.count)
#         ]

#     def test_OperationAnalyzerRecord_insert(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             add_analyzer_record(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#     def test_OperationAnalyzerRecord_bulkinsert(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(**i)
#             l.append(item)
#         add_analyzer_records(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationAnalyzerRecord_delete_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_analyzer_record(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             delete_analyzer_record_by_id(res.uuid)
#             time.sleep(0.1)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationAnalyzerRecord_softdelete_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_analyzer_record(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             delete_analyzer_record_by_id(res.uuid)
#             time.sleep(0.2)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationAnalyzerRecord_delete_by_portfolio(self) -> None:
#         portfolio_id = uuid.uuid4().hex
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(
#                 portfolio_id=portfolio_id,
#                 timestamp=i["timestamp"],
#                 value=i["value"],
#                 name=i["name"],
#                 analyzer_id=i["analyzer_id"],
#             )
#             l.append(item)
#         add_analyzer_records(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(len(self.params), size1 - size0)
#         size2 = get_table_size(self.model)
#         delete_analyzer_record_by_portfolio_analyzer_and_date_range(portfolio_id)
#         time.sleep(0.1)
#         size3 = get_table_size(self.model)
#         self.assertEqual(-(self.count), size3 - size2)

#     def test_OperationAnalyzerRecord_delete_by_portfolio_and_analyzer(self) -> None:
#         count = random.randint(1, 5)
#         portfolio_id = uuid.uuid4().hex
#         for i in range(count):
#             analyzer_id = uuid.uuid4().hex
#             l = []
#             size4 = get_table_size(self.model)
#             for i in self.params:
#                 item = self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp=i["timestamp"],
#                     value=i["value"],
#                     name=i["name"],
#                     analyzer_id=analyzer_id,
#                 )
#                 l.append(item)
#             add_analyzer_records(l)
#             size5 = get_table_size(self.model)
#             self.assertEqual(len(self.params), size5 - size4)
#             delete_analyzer_record_by_portfolio_analyzer_and_date_range(portfolio_id, analyzer_id)
#             time.sleep(0.1)
#             size6 = get_table_size(self.model)
#             self.assertEqual(size6, size4)

#     def test_OperationAnalyzerRecord_softdelete_by_portfolio(self) -> None:
#         portfolio_id = uuid.uuid4().hex
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(
#                 portfolio_id=portfolio_id,
#                 timestamp=i["timestamp"],
#                 value=i["value"],
#                 name=i["name"],
#                 analyzer_id=i["analyzer_id"],
#             )
#             l.append(item)
#         add_analyzer_records(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(len(self.params), size1 - size0)
#         size2 = get_table_size(self.model)
#         softdelete_analyzer_record_by_portfolio_analyzer_and_date_range(portfolio_id)
#         time.sleep(0.1)
#         size3 = get_table_size(self.model)
#         self.assertEqual(-(self.count), size3 - size2)

#     def test_OperationAnalyzerRecord_softdelete_by_portfolio_and_analyzer(self) -> None:
#         count = random.randint(1, 5)
#         portfolio_id = uuid.uuid4().hex
#         for i in range(count):
#             analyzer_id = uuid.uuid4().hex
#             l = []
#             size0 = get_table_size(self.model)
#             for i in self.params:
#                 item = self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp=i["timestamp"],
#                     value=i["value"],
#                     name=i["name"],
#                     analyzer_id=analyzer_id,
#                 )
#                 l.append(item)
#             add_analyzer_records(l)
#             size1 = get_table_size(self.model)
#             self.assertEqual(len(self.params), size1 - size0)
#             softdelete_analyzer_record_by_portfolio_analyzer_and_date_range(portfolio_id, analyzer_id)
#             time.sleep(0.1)
#             size2 = get_table_size(self.model)
#             self.assertEqual(size2, size0)

#     def test_OperationAnalyzerRecord_softdelete_by_portfolio_analyzer_date_range(self) -> None:
#         count = random.randint(1, 5)
#         portfolio_id = uuid.uuid4().hex
#         for i in range(count):
#             size0 = get_table_size(self.model)
#             analyzer_id = uuid.uuid4().hex
#             l = []
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-01",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-01",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-02",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-02",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-03",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id,
#                 )
#             )
#             add_analyzer_records(l)
#             size1 = get_table_size(self.model)
#             self.assertEqual(len(l), size1 - size0)
#             delete_analyzer_record_by_portfolio_analyzer_and_date_range(
#                 portfolio_id, analyzer_id=analyzer_id, start_date="2021-01-01", end_date="2021-01-02"
#             )
#             size2 = get_table_size(self.model)
#             self.assertEqual(-4, size2 - size1)
#             delete_analyzer_record_by_portfolio_analyzer_and_date_range(
#                 portfolio_id, analyzer_id=analyzer_id, start_date="2021-01-01", end_date="2021-01-03"
#             )
#             size3 = get_table_size(self.model)
#             self.assertEqual(size3, size0)

#     def test_OperationAnalyzerRecord_exists(self) -> None:
#         pass

#     def test_OperationAnalyzerRecord_get(self) -> None:
#         count = random.randint(1, 5)
#         for i in range(count):
#             portfolio_id = uuid.uuid4().hex
#             size0 = get_table_size(self.model)
#             analyzer_id1 = uuid.uuid4().hex
#             analyzer_id2 = uuid.uuid4().hex
#             l = []
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-01",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id1,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-01",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id2,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-02",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id1,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-02",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id2,
#                 )
#             )
#             l.append(
#                 self.model(
#                     portfolio_id=portfolio_id,
#                     timestamp="2021-01-03",
#                     value=12,
#                     name="test001",
#                     analyzer_id=analyzer_id1,
#                 )
#             )
#             add_analyzer_records(l)
#             size1 = get_table_size(self.model)
#             self.assertEqual(len(l), size1 - size0)
#             df = get_analyzer_record(
#                 portfolio_id, analyzer_id=analyzer_id1, start_date="2021-01-01", end_date="2021-01-02"
#             )
#             self.assertEqual(2, df.shape[0])

#             df = get_analyzer_record(
#                 portfolio_id, analyzer_id=analyzer_id1, start_date="2021-01-01", end_date="2021-01-03"
#             )
#             self.assertEqual(3, df.shape[0])

#             df = get_analyzer_record(
#                 portfolio_id, analyzer_id=analyzer_id2, start_date="2021-01-01", end_date="2021-01-03"
#             )
#             self.assertEqual(2, df.shape[0])

#             df = get_analyzer_record(portfolio_id, start_date="2021-01-01", end_date="2021-01-02")
#             self.assertEqual(4, df.shape[0])

#             df = get_analyzer_record(portfolio_id)
#             self.assertEqual(5, df.shape[0])

#             df = get_analyzer_record(portfolio_id, page=0, page_size=2)
#             self.assertEqual(2, df.shape[0])
#             df = get_analyzer_record(portfolio_id, page=1, page_size=3)
#             self.assertEqual(2, df.shape[0])

#     def test_OperationAnalyzerRecord_exceptions(self) -> None:
#         # TODO
#         pass
