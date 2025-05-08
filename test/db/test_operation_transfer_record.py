# import unittest
# import random
# import time
# import uuid

# from src.ginkgo.data.operations.transferrecord_crud import *
# from src.ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
# from src.ginkgo.data.models import MTransferRecord
# from src.ginkgo.libs import datetime_normalize
# from ginkgo.enums import TICKDIRECTION_TYPES


# class OperationTransferRecordTest(unittest.TestCase):
#     """
#     UnitTest for Transfer CRUD
#     """

#     @classmethod
#     def setUpClass(cls):
#         cls.model = MTransferRecord
#         drop_table(cls.model)
#         create_table(cls.model)
#         cls.count = random.randint(2, 5)
#         cls.params = [
#             {
#                 "portfolio_id": uuid.uuid4().hex,
#                 "direction": random.choice([i for i in TRANSFERDIRECTION_TYPES]),
#                 "market": random.choice([i for i in MARKET_TYPES]),
#                 "money": random.randint(10000, 1000000),
#                 "status": random.choice([i for i in TRANSFERSTATUS_TYPES]),
#                 "timestamp": datetime.datetime.now(),
#             }
#             for i in range(cls.count)
#         ]

#     def test_OperationTransferRecord_insert(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             add_transfer_record(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             size0 = size1

#     def test_OperationTransferRecord_bulkinsert(self) -> None:
#         l = []
#         for i in self.params:
#             item = self.model(**i)
#             l.append(item)
#         size0 = get_table_size(self.model)
#         add_transfer_records(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(self.count, size1 - size0)

#     def test_OperationTransferRecord_update(self) -> None:
#         # no need to update
#         pass

#     def test_OperationTransferRecord_delete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_transfer_record(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#             delete_transfer_record(res["uuid"])
#             time.sleep(0.01)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationTransferRecord_softdelete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_transfer_record(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#             softdelete_transfer_record(res["uuid"])
#             time.sleep(0.01)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationTransferRecord_delete_by_portfolio(self) -> None:
#         new_portfolio_id = uuid.uuid4().hex
#         for i in self.params:
#             params_copy = i.copy()
#             params_copy["portfolio_id"] = new_portfolio_id
#             size0 = get_table_size(self.model)
#             res = add_transfer_record(**params_copy)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#         size2 = get_table_size(self.model)
#         delete_transfer_records_by_portfolio(new_portfolio_id)
#         time.sleep(0.01)
#         size3 = get_table_size(self.model)
#         self.assertEqual(-self.count, size3 - size2)

#     def test_OperationTransferRecord_softdelete_by_portfolio(self) -> None:
#         new_portfolio_id = uuid.uuid4().hex
#         for i in self.params:
#             params_copy = i.copy()
#             params_copy["portfolio_id"] = new_portfolio_id
#             size0 = get_table_size(self.model)
#             res = add_transfer_record(**params_copy)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#         size2 = get_table_size(self.model)
#         softdelete_transfer_records_by_portfolio(new_portfolio_id)
#         time.sleep(0.01)
#         size3 = get_table_size(self.model)
#         self.assertEqual(-self.count, size3 - size2)

#     def test_OperationTransferRecord_get_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_transfer_record(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#             item = get_transfer_record(res["uuid"])

#             self.assertEqual(item.direction, i["direction"])
#             self.assertEqual(item.market, i["market"])
#             self.assertEqual(item.money, i["money"])
#             self.assertEqual(item.status, i["status"])

#             df = get_transfer_record(res["uuid"], as_dataframe=True).iloc[0]
#             self.assertEqual(df["direction"], i["direction"])
#             self.assertEqual(df["market"], i["market"])
#             self.assertEqual(df["money"], i["money"])
#             self.assertEqual(df["status"], i["status"])

#     def test_OperationTransferRecord_get_by_portfolio(self) -> None:
#         new_portfolio_id = uuid.uuid4().hex
#         for i in self.params:
#             params_copy = i.copy()
#             params_copy["portfolio_id"] = new_portfolio_id
#             size0 = get_table_size(self.model)
#             res = add_transfer_record(**params_copy)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#         res = get_transfer_records(portfolio_id=new_portfolio_id)
#         self.assertEqual(len(res), self.count)

#         df = get_transfer_records(portfolio_id=new_portfolio_id, as_dataframe=True)
#         self.assertEqual(self.count, df.shape[0])

#     def test_OperationTransferRecord_exists(self) -> None:
#         pass

#     def test_OperationTransferRecord_exceptions(self) -> None:
#         pass
