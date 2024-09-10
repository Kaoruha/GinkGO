# import unittest
# import time
# from src.ginkgo.data.models import MStockInfo
# from src.ginkgo.backtest.stockinfo import StockInfo
# from src.ginkgo.data.operations.stockinfo_crud import *
# from src.ginkgo.data.drivers import create_table, drop_table, get_table_size
# from ginkgo.enums import CURRENCY_TYPES

# from src.ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse


# class OperationStockinfoTest(unittest.TestCase):
#     """
#     UnitTest for Stockinfo CRUD
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(OperationStockinfoTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "code": "test_code1",
#                 "code_name": "test_codename",
#                 "industry": "矿产",
#                 "currency": CURRENCY_TYPES.CNY,
#                 "list_date": "2020-01-01",
#                 "delist_date": "2020-05-01",
#             },
#             {
#                 "code": "test_code2",
#                 "code_name": "test_codename",
#                 "industry": "矿产",
#                 "currency": CURRENCY_TYPES.USD,
#                 "list_date": "2020-01-01",
#                 "delist_date": "2020-04-01",
#             },
#             {
#                 "code": "test_code3",
#                 "code_name": "test_codename",
#                 "industry": "体育",
#                 "currency": CURRENCY_TYPES.USD,
#                 "list_date": "2020-02-01",
#                 "delist_date": "2020-03-01",
#             },
#             {
#                 "code": "test_code4",
#                 "code_name": "test_codename",
#                 "industry": "体育",
#                 "currency": CURRENCY_TYPES.CNY,
#                 "list_date": "2020-03-01",
#                 "delist_date": "2020-05-01",
#             },
#         ]

#     def rebuild_table(self) -> None:
#         drop_table(MStockInfo)
#         time.sleep(0.1)
#         create_table(MStockInfo)
#         time.sleep(0.1)
#         size = get_table_size(MStockInfo)
#         self.assertEqual(0, size)

#     def test_OperationStockinfo_create(self) -> None:
#         self.rebuild_table()
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             add_stockinfo(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationStockinfo_bulkinsert(self) -> None:
#         self.rebuild_table()
#         size0 = get_table_size(MStockInfo)
#         l = []
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationStockinfo_update(self) -> None:
#         pass

#     def test_OperationStockinfo_read_by_code(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_stockinfo(code="test_code1")
#         self.assertEqual(1, len(res))
#         df = get_stockinfo(code="test_code1", as_dataframe=True)
#         self.assertEqual(1, df.shape[0])

#     def test_OperationStockinfo_read_by_code_fuzzy(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_stockinfo(code="test", fuzzy=True)
#         self.assertEqual(len(self.params), len(res))
#         df = get_stockinfo(code="test", fuzzy=True, as_dataframe=True)
#         self.assertEqual(len(self.params), df.shape[0])

#         res = get_stockinfo(code="1", fuzzy=True)
#         self.assertEqual(1, len(res))
#         df = get_stockinfo(code="1", fuzzy=True, as_dataframe=True)
#         self.assertEqual(1, df.shape[0])

#     def test_OperationStockinfo_read_by_industry(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_stockinfo(industry="矿产")
#         self.assertEqual(2, len(res))
#         df = get_stockinfo(industry="矿产", as_dataframe=True)
#         self.assertEqual(2, df.shape[0])

#     def test_OperationStockinfo_read_by_industry_fuzzy(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_stockinfo(industry="矿", fuzzy=True)
#         self.assertEqual(2, len(res))
#         df = get_stockinfo(industry="矿", fuzzy=True, as_dataframe=True)
#         self.assertEqual(2, df.shape[0])

#     def test_OperationStockinfo_read_by_currency(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_stockinfo(currency=CURRENCY_TYPES.CNY)
#         self.assertEqual(2, len(res))
#         df = get_stockinfo(currency=CURRENCY_TYPES.CNY, as_dataframe=True)
#         self.assertEqual(2, df.shape[0])

#     def test_OperationStockinfo_read_by_listdate(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_stockinfo(list_date="2020-02-01")
#         self.assertEqual(2, len(res))
#         df = get_stockinfo(list_date="2020-02-01", as_dataframe=True)
#         self.assertEqual(2, df.shape[0])

#     def test_OperationStockinfo_read_by_delistdate(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         res = get_stockinfo(delist_date="2020-04-01")
#         self.assertEqual(2, len(res))
#         df = get_stockinfo(delist_date="2020-04-01", as_dataframe=True)
#         self.assertEqual(2, df.shape[0])

#     def test_OperationStockinfo_delete(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         codes = {}
#         for i in self.params:
#             if i["code"] not in codes.keys():
#                 codes[i["code"]] = 1
#             else:
#                 codes[i["code"]] += 1

#         for i in codes.keys():
#             size2 = get_table_size(MStockInfo)
#             delete_stockinfo(code=i)
#             time.sleep(0.1)
#             size3 = get_table_size(MStockInfo)
#             self.assertEqual(-codes[i], size3 - size2)

#     def test_OperationStockinfo_softdelete(self) -> None:
#         self.rebuild_table()
#         l = []
#         size0 = get_table_size(MStockInfo)
#         for i in self.params:
#             item = MStockInfo()
#             item.set(i["code"], i["code_name"], i["industry"], i["currency"], i["list_date"], i["delist_date"])
#             l.append(item)
#         add_stockinfos(l)
#         time.sleep(0.1)
#         size1 = get_table_size(MStockInfo)
#         self.assertEqual(len(self.params), size1 - size0)
#         codes = {}
#         for i in self.params:
#             if i["code"] not in codes.keys():
#                 codes[i["code"]] = 1
#             else:
#                 codes[i["code"]] += 1

#         for i in codes.keys():
#             size2 = get_table_size(MStockInfo)
#             softdelete_stockinfo(code=i)
#             time.sleep(0.1)
#             size3 = get_table_size(MStockInfo)
#             self.assertEqual(-codes[i], size3 - size2)

#     def test_OperationStockinfo_exists(self) -> None:
#         pass

#     def test_OperationStockinfo_exceptions(self) -> None:
#         pass
