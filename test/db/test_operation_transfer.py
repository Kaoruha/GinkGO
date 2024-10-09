# import unittest
# import random
# import time
# import uuid
# from src.ginkgo.data.operations.transfer_crud import *
# from src.ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
# from src.ginkgo.data.models import MTransfer
# from src.ginkgo.libs import datetime_normalize
# from ginkgo.enums import TICKDIRECTION_TYPES, TRANSFERSTATUS_TYPES, MARKET_TYPES


# class OperationTransferTest(unittest.TestCase):
#     """
#     UnitTest for Transfer CRUD
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(OperationTransferTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "portfolio_id": "11test001",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "market": MARKET_TYPES.CHINA,
#                 "money": 10000,
#                 "status": TRANSFERSTATUS_TYPES.NEW,
#                 "timestamp": "2020-01-01",
#             },
#             {
#                 "portfolio_id": "test002",
#                 "direction": DIRECTION_TYPES.SHORT,
#                 "market": MARKET_TYPES.NASDAQ,
#                 "money": 100000,
#                 "status": TRANSFERSTATUS_TYPES.NEW,
#                 "timestamp": "2020-02-01",
#             },
#         ]

#     def test_OperationTransfer_insert(self) -> None:
#         create_table(MTransfer)
#         size0 = get_table_size(MTransfer)
#         for i in self.params:
#             count = add_transfer(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 status=i["status"],
#                 timestamp=i["timestamp"],
#             )
#             size1 = get_table_size(MTransfer)
#             self.assertEqual(1, size1 - size0)
#             size0 = size1

#     def test_OperationTransfer_bulkinsert(self) -> None:
#         create_table(MTransfer)
#         size0 = get_table_size(MTransfer)
#         l = []
#         for i in self.params:
#             item = MTransfer()
#             item.set(
#                 i["portfolio_id"],
#                 i["direction"],
#                 i["market"],
#                 i["money"],
#                 i["status"],
#                 i["timestamp"],
#             )
#             l.append(item)
#         add_transfers(l)
#         size1 = get_table_size(MTransfer)
#         self.assertEqual(len(l), size1 - size0)

#     def test_OperationTransfer_update(self) -> None:
#         pass

#     def test_OperationTransfer_get_byid(self) -> None:
#         # in format ModelTransfer
#         # in format dataframe
#         create_table(MTransfer)
#         for i in self.params:
#             size0 = get_table_size(MTransfer)
#             transfer_id = add_transfer(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 status=i["status"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             size1 = get_table_size(MTransfer)
#             self.assertEqual(size1 - size0, 1)
#             item = get_transfer_by_id(transfer_id)
#             self.assertEqual(i["portfolio_id"], item.portfolio_id)
#             self.assertEqual(i["direction"], item.direction)
#             self.assertEqual(i["market"], item.market)
#             self.assertEqual(i["money"], item.money)
#             self.assertEqual(i["status"], item.status)

#             df = get_transfer_by_id(id=transfer_id, as_dataframe=True)
#             self.assertEqual(df.shape[0], 1)

#     def test_OperationTransfer_get_by_portfolio(self) -> None:
#         # By Portfolio
#         create_table(MTransfer)
#         portfolio_id = uuid.uuid4().hex[:10]
#         for i in self.params:
#             size0 = get_table_size(MTransfer)
#             add_transfer(
#                 portfolio_id=portfolio_id,
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 status=i["status"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             size1 = get_table_size(MTransfer)
#             self.assertEqual(size1 - size0, 1)

#         transfers = get_transfer_by_portfolio_id(portfolio_id)
#         self.assertEqual(len(transfers), len(self.params))

#         df = get_transfer_by_portfolio_id(portfolio_id=portfolio_id, as_dataframe=True)
#         self.assertEqual(df.shape[0], len(self.params))

#     def test_OperationTransfer_read_byportfolio_bunk(self) -> None:
#         # Date filter
#         create_table(MTransfer)
#         size0 = get_table_size(MTransfer)
#         portfolio_id2 = uuid.uuid4().hex[:10]
#         l = []
#         for i in range(50):
#             item = MTransfer()
#             item.set(
#                 portfolio_id2,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 TRANSFERSTATUS_TYPES.NEW,
#                 datetime_normalize("2022-02-01"),
#             )
#             l.append(item)
#         for i in range(50):
#             item = MTransfer()
#             item.set(
#                 portfolio_id2,
#                 DIRECTION_TYPES.SHORT,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 TRANSFERSTATUS_TYPES.NEW,
#                 datetime_normalize("2022-02-02"),
#             )
#             l.append(item)
#         for i in range(50):
#             item = MTransfer()
#             item.set(
#                 portfolio_id2,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 TRANSFERSTATUS_TYPES.NEW,
#                 datetime_normalize("2022-02-03"),
#             )
#             l.append(item)
#         add_transfers(l)
#         size1 = get_table_size(MTransfer)
#         self.assertEqual(size1 - size0, len(l))
#         res = get_transfer_by_portfolio_id(portfolio_id=portfolio_id2)
#         self.assertEqual(150, len(res))
#         df = get_transfer_by_portfolio_id(portfolio_id=portfolio_id2, as_dataframe=True)
#         self.assertEqual(150, df.shape[0])

#         # DateFilter
#         res = get_transfer_by_portfolio_id(portfolio_id=portfolio_id2, start_date="2022-02-01", end_date="2022-02-02")
#         self.assertEqual(100, len(res))
#         df = get_transfer_by_portfolio_id(
#             portfolio_id=portfolio_id2, start_date="2022-02-01", end_date="2022-02-02", as_dataframe=True
#         )
#         self.assertEqual(100, df.shape[0])

#         res = get_transfer_by_portfolio_id(portfolio_id=portfolio_id2, start_date="2022-02-03", end_date="2022-02-03")
#         self.assertEqual(50, len(res))
#         df = get_transfer_by_portfolio_id(
#             portfolio_id=portfolio_id2, start_date="2022-02-03", end_date="2022-02-03", as_dataframe=True
#         )
#         self.assertEqual(50, df.shape[0])

#         res = get_transfer_by_portfolio_id(portfolio_id=portfolio_id2, start_date="2022-02-01", end_date="2022-02-03")
#         self.assertEqual(150, len(res))
#         df = get_transfer_by_portfolio_id(
#             portfolio_id=portfolio_id2, start_date="2022-02-01", end_date="2022-02-03", as_dataframe=True
#         )
#         self.assertEqual(150, df.shape[0])

#         # Pagination
#         res = get_transfer_by_portfolio_id(
#             portfolio_id=portfolio_id2, start_date="2022-02-01", end_date="2022-02-02", page=0, page_size=30
#         )
#         self.assertEqual(30, len(res))
#         df = get_transfer_by_portfolio_id(
#             portfolio_id=portfolio_id2,
#             start_date="2022-02-01",
#             end_date="2022-02-02",
#             page=0,
#             page_size=30,
#             as_dataframe=True,
#         )
#         self.assertEqual(30, df.shape[0])

#         res = get_transfer_by_portfolio_id(
#             portfolio_id=portfolio_id2, start_date="2022-02-01", end_date="2022-02-02", page=3, page_size=30
#         )
#         self.assertEqual(10, len(res))
#         df = get_transfer_by_portfolio_id(
#             portfolio_id=portfolio_id2,
#             start_date="2022-02-01",
#             end_date="2022-02-02",
#             page=3,
#             page_size=30,
#             as_dataframe=True,
#         )
#         self.assertEqual(10, df.shape[0])

#     def test_OperationTransfer_softdelete_by_id(self) -> None:
#         create_table(MTransfer)
#         ids = []
#         for i in self.params:
#             size0 = get_table_size(MTransfer)
#             id = add_transfer(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 status=i["status"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             ids.append(id)
#             size1 = get_table_size(MTransfer)
#             self.assertEqual(1, size1 - size0)

#         for i in ids:
#             size2 = get_table_size(MTransfer)
#             softdelete_transfer_by_id(i)
#             size3 = get_table_size(MTransfer)
#             item = get_transfer_by_id(i)
#             self.assertEqual(None, item)
#             self.assertEqual(0, size3 - size2)

#     def test_OperationTransfer_delete_by_id(self) -> None:
#         create_table(MTransfer)
#         ids = []
#         for i in self.params:
#             size0 = get_table_size(MTransfer)
#             id = add_transfer(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 status=i["status"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             ids.append(id)
#             size1 = get_table_size(MTransfer)
#             self.assertEqual(1, size1 - size0)

#         for i in ids:
#             size2 = get_table_size(MTransfer)
#             delete_transfer_by_id(i)
#             size3 = get_table_size(MTransfer)
#             item = get_transfer_by_id(i)
#             self.assertEqual(-1, size3 - size2)
#             self.assertEqual(None, item)

#     def test_OperationTransfer_softdelete_by_portfolio(self) -> None:
#         create_table(MTransfer)
#         portfolio_id = uuid.uuid4().hex[:10]
#         count = random.randint(50, 100)
#         size0 = get_table_size(MTransfer)
#         l = []
#         for i in range(count):
#             item = MTransfer()
#             item.set(
#                 portfolio_id,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 TRANSFERSTATUS_TYPES.NEW,
#                 datetime_normalize("2022-02-03"),
#             )
#             l.append(item)
#         add_transfers(l)
#         size1 = get_table_size(MTransfer)
#         self.assertEqual(count, size1 - size0)

#         softdelete_transfer_by_portfolio_id(portfolio_id)
#         size2 = get_table_size(MTransfer)
#         self.assertEqual(0, size2 - size1)

#         data = get_transfer_by_portfolio_id(portfolio_id)
#         self.assertEqual(0, len(data))
#         df = get_transfer_by_portfolio_id(portfolio_id, as_dataframe=True)
#         self.assertEqual(0, df.shape[0])

#     def test_OperationTransfer_delete_by_portfolio(self) -> None:
#         # By PortfolioID
#         portfolio_id = uuid.uuid4().hex[:10]
#         count = random.randint(50, 100)
#         size0 = get_table_size(MTransfer)
#         l = []
#         for i in range(count):
#             item = MTransfer()
#             item.set(
#                 portfolio_id,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 TRANSFERSTATUS_TYPES.NEW,
#                 datetime_normalize("2022-02-03"),
#             )
#             l.append(item)
#         add_transfers(l)
#         size1 = get_table_size(MTransfer)
#         self.assertEqual(count, size1 - size0)

#         delete_transfer_by_portfolio_id(portfolio_id)
#         size2 = get_table_size(MTransfer)
#         self.assertEqual(-count, size2 - size1)

#         data = get_transfer_by_portfolio_id(portfolio_id)
#         self.assertEqual(0, len(data))
#         df = get_transfer_by_portfolio_id(portfolio_id, as_dataframe=True)
#         self.assertEqual(0, df.shape[0])

#     def test_OperationTransfer_exists(self) -> None:
#         pass

#     def test_OperationTransfer_exceptions(self) -> None:
#         pass
