# import unittest
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

#     def __init__(self, *args, **kwargs) -> None:
#         super(OperationTransferRecordTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "portfolio_id": "test001",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "market": MARKET_TYPES.CHINA,
#                 "money": 10000,
#                 "timestamp": "2020-01-01",
#             },
#             {
#                 "portfolio_id": "test002",
#                 "direction": DIRECTION_TYPES.SHORT,
#                 "market": MARKET_TYPES.NASDAQ,
#                 "money": 100000,
#                 "timestamp": "2020-02-01",
#             },
#         ]

#     def test_OperationTransferRecord_create(self) -> None:
#         create_table(MTransferRecord)
#         size0 = get_table_size(MTransferRecord)
#         for i in self.params:
#             add_transfer_record(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             size1 = get_table_size(MTransferRecord)
#             self.assertEqual(1, size1 - size0)
#             size0 = size1

#     def test_OperationTransferRecord_bulkinsert(self) -> None:
#         create_table(MTransferRecord)
#         size0 = get_table_size(MTransferRecord)
#         l = []
#         for i in self.params:
#             item = MTransferRecord()
#             item.set(
#                 i["portfolio_id"],
#                 i["direction"],
#                 i["market"],
#                 i["money"],
#                 datetime_normalize(i["timestamp"]),
#             )
#             l.append(item)
#         add_transfer_records(l)
#         size1 = get_table_size(MTransferRecord)
#         self.assertEqual(len(l), size1 - size0)

#     def test_OperationTransferRecord_update(self) -> None:
#         # no need to update
#         pass

#     def test_OperationTransferRecord_read_by_id(self) -> None:
#         # in format ModelTransfer
#         # in format dataframe
#         create_table(MTransferRecord)
#         for i in self.params:
#             size0 = get_table_size(MTransferRecord)
#             transfer_id = add_transfer_record(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             size1 = get_table_size(MTransferRecord)
#             self.assertEqual(size1 - size0, 1)
#             item = get_transfer_record_by_id(transfer_id)
#             self.assertEqual(i["portfolio_id"], item.portfolio_id)
#             self.assertEqual(i["direction"], item.direction)
#             self.assertEqual(i["market"], item.market)
#             self.assertEqual(i["money"], item.money)

#             df = get_transfer_record_by_id(id=transfer_id, as_dataframe=True)
#             self.assertEqual(df.shape[0], 1)

#     def test_OperationTransferRecord_read_by_portfolio(self) -> None:
#         # By Portfolio
#         portfolio_id = uuid.uuid4().hex[:10]
#         for i in self.params:
#             size0 = get_table_size(MTransferRecord)
#             add_transfer_record(
#                 portfolio_id=portfolio_id,
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             size1 = get_table_size(MTransferRecord)
#             self.assertEqual(size1 - size0, 1)

#         transfers = get_transfer_record_by_portfolio_id(portfolio_id)
#         self.assertEqual(len(transfers), len(self.params))

#         df = get_transfer_record_by_portfolio_id(portfolio_id=portfolio_id, as_dataframe=True)
#         self.assertEqual(df.shape[0], len(self.params))

#     def test_OperationTransferRecord_read_by_portfolio_with_date_range(self) -> None:
#         # Date filter
#         create_table(MTransferRecord)
#         size0 = get_table_size(MTransferRecord)
#         portfolio_id = uuid.uuid4().hex[:10]
#         l = []
#         for i in range(450):
#             item = MTransferRecord()
#             item.set(
#                 portfolio_id,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 datetime_normalize("2022-02-02"),
#             )
#             l.append(item)
#         for i in range(450):
#             item = MTransferRecord()
#             item.set(
#                 portfolio_id,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 datetime_normalize("2022-02-03"),
#             )
#             l.append(item)
#         add_transfer_records(l)
#         size1 = get_table_size(MTransferRecord)
#         self.assertEqual(size1 - size0, len(l))
#         res = get_transfer_record_by_portfolio_id(portfolio_id=portfolio_id)
#         self.assertEqual(900, len(res))
#         df = get_transfer_record_by_portfolio_id(portfolio_id=portfolio_id, as_dataframe=True)
#         self.assertEqual(900, df.shape[0])
#         # DateFilter
#         res = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2022-02-01", end_date="2022-02-02"
#         )
#         self.assertEqual(450, len(res))
#         df = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2022-02-01", end_date="2022-02-02", as_dataframe=True
#         )
#         self.assertEqual(450, df.shape[0])

#         res = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2022-02-03", end_date="2022-02-03"
#         )
#         self.assertEqual(450, len(res))
#         df = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2022-02-03", end_date="2022-02-03", as_dataframe=True
#         )
#         self.assertEqual(450, df.shape[0])

#         res = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2022-02-01", end_date="2022-02-03"
#         )
#         self.assertEqual(900, len(res))
#         df = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2022-02-01", end_date="2022-02-03", as_dataframe=True
#         )
#         self.assertEqual(900, df.shape[0])

#     def test_OperationTransferRecord_read_by_portfolio_with_pagination(self) -> None:
#         create_table(MTransferRecord)
#         portfolio_id = uuid.uuid4().hex[:10]
#         l = []
#         for i in range(50):
#             item = MTransferRecord()
#             item.set(
#                 portfolio_id,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 datetime_normalize("2023-02-02"),
#             )
#             l.append(item)
#         for i in range(50):
#             item = MTransferRecord()
#             item.set(
#                 portfolio_id,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 datetime_normalize("2023-02-03"),
#             )
#             l.append(item)
#         add_transfer_records(l)
#         res = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2023-02-01", end_date="2023-02-02", page=0, page_size=30
#         )
#         self.assertEqual(30, len(res))
#         df = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id,
#             start_date="2023-02-01",
#             end_date="2023-02-02",
#             page=0,
#             page_size=30,
#             as_dataframe=True,
#         )
#         self.assertEqual(30, df.shape[0])

#         res = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id, start_date="2023-02-01", end_date="2023-02-02", page=1, page_size=30
#         )
#         self.assertEqual(20, len(res))
#         df = get_transfer_record_by_portfolio_id(
#             portfolio_id=portfolio_id,
#             start_date="2023-02-01",
#             end_date="2023-02-02",
#             page=1,
#             page_size=30,
#             as_dataframe=True,
#         )
#         self.assertEqual(20, df.shape[0])

#     def test_OperationTransferRecord_delete(self) -> None:
#         create_table(MTransferRecord)
#         # By ID
#         for i in self.params:
#             size0 = get_table_size(MTransferRecord)
#             id = add_transfer_record(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             size1 = get_table_size(MTransferRecord)
#             self.assertEqual(1, size1 - size0)

#             softdelete_transfer_record_by_id(id)
#             time.sleep(0.1)
#             size2 = get_table_size(MTransferRecord)
#             item = get_transfer_record_by_id(id)
#             self.assertEqual(-1, size2 - size1)
#             self.assertEqual(None, item)

#         for i in self.params:
#             size0 = get_table_size(MTransferRecord)
#             id = add_transfer_record(
#                 portfolio_id=i["portfolio_id"],
#                 direction=i["direction"],
#                 market=i["market"],
#                 money=i["money"],
#                 timestamp=datetime_normalize(i["timestamp"]),
#             )
#             size1 = get_table_size(MTransferRecord)
#             self.assertEqual(1, size1 - size0)

#             delete_transfer_record_by_id(id)
#             time.sleep(0.1)
#             size2 = get_table_size(MTransferRecord)
#             item = get_transfer_record_by_id(id)
#             self.assertEqual(-1, size2 - size1)
#             self.assertEqual(None, item)

#         # By PortfolioID
#         portfolio_id = uuid.uuid4().hex[:10]
#         size4 = get_table_size(MTransferRecord)
#         l = []
#         for i in range(100):
#             item = MTransferRecord()
#             item.set(
#                 portfolio_id,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 datetime_normalize("2022-02-03"),
#             )
#             l.append(item)
#         add_all(l)
#         size5 = get_table_size(MTransferRecord)
#         self.assertEqual(100, size5 - size4)

#         softdelete_transfer_record_by_portfolio_id(portfolio_id)
#         time.sleep(0.1)
#         size6 = get_table_size(MTransferRecord)
#         self.assertEqual(-100, size6 - size5)

#         data = get_transfer_record_by_portfolio_id(portfolio_id)
#         self.assertEqual(0, len(data))

#         portfolio_id2 = uuid.uuid4().hex[:10]
#         l = []
#         for i in range(100):
#             item = MTransferRecord()
#             item.set(
#                 portfolio_id2,
#                 DIRECTION_TYPES.LONG,
#                 MARKET_TYPES.CHINA,
#                 10000,
#                 datetime_normalize("2022-02-03"),
#             )
#             l.append(item)
#         add_all(l)
#         size5 = get_table_size(MTransferRecord)
#         self.assertEqual(100, size5 - size4)
#         delete_transfer_record_by_portfolio_id(portfolio_id2)
#         time.sleep(0.1)
#         size7 = get_table_size(MTransferRecord)
#         self.assertEqual(-100, size7 - size5)

#     def test_OperationTransferRecord_exists(self) -> None:
#         pass

#     def test_OperationTransferRecord_exceptions(self) -> None:
#         pass
