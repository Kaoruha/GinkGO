# import unittest
# import uuid
# import time

# from ginkgo.data.models import MPositionRecord
# from ginkgo.backtest import Position
# from src.ginkgo.data.operations.position_record_crud import *
# from src.ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table


# class OperationPositionrecordTest(unittest.TestCase):
#     """
#     UnitTest for Positionrecord CRUD
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(OperationPositionrecordTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-01",
#                 "code": "test_code001",
#                 "volume": 1000,
#                 "cost": 2.5,
#             },
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-02",
#                 "code": "test_code001",
#                 "volume": 500,
#                 "cost": 2.5,
#             },
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-03",
#                 "code": "test_code001",
#                 "volume": 800,
#                 "cost": 2.5,
#             },
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-01",
#                 "code": "test_code002",
#                 "volume": 1000,
#                 "cost": 3.5,
#             },
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-01",
#                 "code": "test_code003",
#                 "volume": 1000,
#                 "cost": 2.1,
#             },
#         ]

#     def rebuild_table(self) -> None:
#         drop_table(MPositionRecord)
#         time.sleep(0.1)

#         create_table(MPositionRecord)
#         time.sleep(0.1)

#     def test_OperationPositionrecord_insert(self) -> None:
#         create_table(MPositionRecord)
#         for i in self.params:
#             size0 = get_table_size(MPositionRecord)
#             add_position_record(i["portfolio_id"], i["timestamp"], i["code"], i["volume"], i["cost"])
#             time.sleep(0.1)
#             size1 = get_table_size(MPositionRecord)
#             self.assertEqual(1, size1 - size0)

#     def test_OperationPositionrecord_bulkinsert(self) -> None:
#         create_table(MPositionRecord)
#         l = []
#         size0 = get_table_size(MPositionRecord)
#         for i in self.params:
#             item = MPositionRecord()
#             item.set(i["portfolio_id"], i["timestamp"], i["code"], i["volume"], i["cost"])
#             l.append(item)
#         add_position_records(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MPositionRecord)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationPositionrecord_update(self) -> None:
#         pass

#     def test_OperationPositionrecord_get(self) -> None:
#         # in format ModelPositionrecord
#         # in format dataframe
#         pass

#     def test_OperationPositionrecord_delete_by_id(self) -> None:
#         create_table(MPositionRecord)
#         ids = []
#         for i in self.params:
#             size0 = get_table_size(MPositionRecord)
#             id = add_position_record(i["portfolio_id"], i["timestamp"], i["code"], i["volume"], i["cost"])
#             time.sleep(0.1)
#             size1 = get_table_size(MPositionRecord)
#             self.assertEqual(1, size1 - size0)
#             ids.append(id)
#         for i in ids:
#             size2 = get_table_size(MPositionRecord)
#             res = delete_position_record_by_id(i)
#             time.sleep(0.5)
#             size3 = get_table_size(MPositionRecord)
#             self.assertEqual(-1, size3 - size2)

#     def test_OperationPositionrecord_delete_by_portfolio(self) -> None:
#         create_table(MPositionRecord)
#         portfolio_id = uuid.uuid4().hex[:10]
#         l = []
#         size0 = get_table_size(MPositionRecord)
#         for i in self.params:
#             item = MPositionRecord()
#             item.set(portfolio_id, i["timestamp"], i["code"], i["volume"], i["cost"])
#             l.append(item)
#         add_position_records(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MPositionRecord)
#         self.assertEqual(len(self.params), size1 - size0)
#         delete_position_record_by_portfolio_id(portfolio_id)
#         time.sleep(0.1)
#         size2 = get_table_size(MPositionRecord)
#         self.assertEqual(-len(self.params), size2 - size1)

#     def test_OperationPositionrecord_delete_by_portfolio_with_date_range(self) -> None:
#         create_table(MPositionRecord)
#         portfolio_id = uuid.uuid4().hex[:10]
#         l = []
#         size0 = get_table_size(MPositionRecord)
#         for i in self.params:
#             item = MPositionRecord()
#             item.set(portfolio_id, i["timestamp"], i["code"], i["volume"], i["cost"])
#             l.append(item)
#         add_position_records(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MPositionRecord)
#         self.assertEqual(len(self.params), size1 - size0)
#         delete_position_record_by_portfolio_id(portfolio_id, start_date="2020-01-01", end_date="2020-01-02")
#         time.sleep(0.1)
#         size2 = get_table_size(MPositionRecord)
#         self.assertEqual(-4, size2 - size1)

#     def test_OperationPositionrecord_softdelete_by_portfolio(self) -> None:
#         create_table(MPositionRecord)
#         portfolio_id = uuid.uuid4().hex[:10]
#         l = []
#         size0 = get_table_size(MPositionRecord)
#         for i in self.params:
#             item = MPositionRecord()
#             item.set(portfolio_id, i["timestamp"], i["code"], i["volume"], i["cost"])
#             l.append(item)
#         add_position_records(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MPositionRecord)
#         self.assertEqual(len(self.params), size1 - size0)
#         softdelete_position_record_by_portfolio_id(portfolio_id)
#         time.sleep(0.1)
#         size2 = get_table_size(MPositionRecord)
#         self.assertEqual(-len(self.params), size2 - size1)

#     def test_OperationPositionrecord_softdelete_by_portfolio_with_date_range(self) -> None:
#         create_table(MPositionRecord)
#         portfolio_id = uuid.uuid4().hex[:10]
#         l = []
#         size0 = get_table_size(MPositionRecord)
#         for i in self.params:
#             item = MPositionRecord()
#             item.set(portfolio_id, i["timestamp"], i["code"], i["volume"], i["cost"])
#             l.append(item)
#         add_position_records(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MPositionRecord)
#         self.assertEqual(len(self.params), size1 - size0)
#         softdelete_position_record_by_portfolio_id(portfolio_id, start_date="2020-01-01", end_date="2020-01-02")
#         time.sleep(0.1)
#         size2 = get_table_size(MPositionRecord)
#         self.assertEqual(-4, size2 - size1)

#     def test_OperationPositionrecord_exists(self) -> None:
#         pass

#     def test_OperationPositionrecord_exceptions(self) -> None:
#         pass
