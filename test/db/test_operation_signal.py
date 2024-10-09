# import unittest
# import time
# from ginkgo.enums import DIRECTION_TYPES
# from ginkgo.data.models import MSignal

# from src.ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
# from src.ginkgo.data.operations.signal_crud import *


# class OperationSignalTest(unittest.TestCase):
#     """
#     UnitTest for Signal CRUD
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(OperationSignalTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-01",
#                 "code": "testcode001",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "reason": "just for test",
#             },
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-02",
#                 "code": "testcode001",
#                 "direction": DIRECTION_TYPES.SHORT,
#                 "reason": "against  long",
#             },
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-03",
#                 "code": "testcode002",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "reason": "just for test",
#             },
#             {
#                 "portfolio_id": "test_portfolio",
#                 "timestamp": "2020-01-04",
#                 "code": "testcode003",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "reason": "just for test",
#             },
#         ]

#     def rebuild_table(self) -> None:
#         drop_table(MSignal)
#         time.sleep(0.1)
#         create_table(MSignal)
#         time.sleep(0.1)

#     def test_OperationSignal_insert(self) -> None:
#         self.rebuild_table()
#         for i in self.params:
#             size0 = get_table_size(MSignal)
#             add_signal(i["portfolio_id"], i["timestamp"], i["code"], i["direction"], i["reason"])
#             time.sleep(0.1)
#             size1 = get_table_size(MSignal)
#             self.assertEqual(1, size1 - size0)

#     def test_OperationSignal_bulkinsert(self) -> None:
#         self.rebuild_table()
#         l = []
#         for i in self.params:
#             item = Signal()
#             item.set(i["portfolio_id"], i["timestamp"], i["code"], i["direction"], i["reason"])
#             l.append(item)
#         size0 = get_table_size(MSignal)
#         add_signals(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MSignal)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationSignal_update(self) -> None:
#         pass

#     def test_OperationSignal_get_by_portfolio(self) -> None:
#         self.rebuild_table()
#         time.sleep(1)
#         l = []
#         portfolio_id = "test_portfolio"
#         count = 0
#         for i in self.params:
#             if i["portfolio_id"] == portfolio_id:
#                 count += 1
#         for i in self.params:
#             item = Signal()
#             item.set(i["portfolio_id"], i["timestamp"], i["code"], i["direction"], i["reason"])
#             l.append(item)
#         size0 = get_table_size(MSignal)
#         add_signals(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MSignal)
#         self.assertEqual(len(self.params), size1 - size0)

#         res = get_signal_by_portfolio_id_and_date_range(portfolio_id)
#         self.assertEqual(count, len(res))
#         df = get_signal_by_portfolio_id_and_date_range(portfolio_id, as_dataframe=True)
#         self.assertEqual(count, df.shape[0])

#     def test_OperationSignal_get_by_portfolio_and_date(self) -> None:
#         self.rebuild_table()
#         l = []
#         portfolio_id = "test_portfolio"
#         count = 0
#         for i in self.params:
#             if i["portfolio_id"] == portfolio_id:
#                 count += 1
#         for i in self.params:
#             item = Signal()
#             item.set(i["portfolio_id"], i["timestamp"], i["code"], i["direction"], i["reason"])
#             l.append(item)
#         size0 = get_table_size(MSignal)
#         add_signals(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MSignal)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_signal_by_portfolio_id_and_date_range(portfolio_id, start_date="2020-01-02", end_date="2020-01-03")
#         self.assertEqual(2, len(res))
#         df = get_signal_by_portfolio_id_and_date_range(
#             portfolio_id, start_date="2020-01-02", end_date="2020-01-03", as_dataframe=True
#         )
#         self.assertEqual(2, df.shape[0])

#     def test_OperationSignal_delete_by_id(self) -> None:
#         self.rebuild_table()
#         for i in self.params:
#             size0 = get_table_size(MSignal)
#             id = add_signal(i["portfolio_id"], i["timestamp"], i["code"], i["direction"], i["reason"])
#             time.sleep(0.1)
#             size1 = get_table_size(MSignal)
#             self.assertEqual(1, size1 - size0)
#             delete_signal_by_id(id)
#             time.sleep(0.1)
#             size2 = get_table_size(MSignal)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationSignal_delete_by_portfolio(self) -> None:
#         self.rebuild_table()
#         l = []
#         portfolio_id = "test_portfolio"
#         count = 0
#         for i in self.params:
#             if i["portfolio_id"] == portfolio_id:
#                 count += 1
#         for i in self.params:
#             item = Signal()
#             item.set(i["portfolio_id"], i["timestamp"], i["code"], i["direction"], i["reason"])
#             l.append(item)
#         size0 = get_table_size(MSignal)
#         add_signals(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MSignal)
#         self.assertEqual(len(self.params), size1 - size0)
#         delete_signal_by_portfolio_id(portfolio_id)
#         time.sleep(0.1)
#         size2 = get_table_size(MSignal)
#         self.assertEqual(-count, size2 - size1)

#     def test_OperationSignal_delete_by_portfolio_and_date(self) -> None:
#         self.rebuild_table()
#         l = []
#         portfolio_id = "test_portfolio"
#         count = 0
#         for i in self.params:
#             if i["portfolio_id"] == portfolio_id:
#                 count += 1
#         for i in self.params:
#             item = Signal()
#             item.set(i["portfolio_id"], i["timestamp"], i["code"], i["direction"], i["reason"])
#             l.append(item)
#         size0 = get_table_size(MSignal)
#         add_signals(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MSignal)
#         self.assertEqual(len(self.params), size1 - size0)
#         delete_signal_by_portfolio_id(portfolio_id, start_date="2020-01-02", end_date="2020-01-03")
#         time.sleep(0.1)
#         size2 = get_table_size(MSignal)
#         self.assertEqual(-2, size2 - size1)

#     def test_OperationSignal_exists(self) -> None:
#         pass

#     def test_OperationSignal_exceptions(self) -> None:
#         pass
