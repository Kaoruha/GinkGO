# import unittest
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
#     MOrder,
#     MTradeDay,
#     MStockInfo,
#     MSignal,
#     MTick,
#     MAdjustfactor,
#     MBar,
# )

# from ginkgo.backtest.bar import Bar
# from ginkgo.backtest.tick import Tick
# from ginkgo.backtest.order import Order
# from ginkgo.data.ginkgo_data import GDATA
# from ginkgo.libs.ginkgo_logger import GLOG


# class ModelOrderTest(unittest.TestCase):
#     """
#     UnitTest for Order.
#     """

#     # Init
#     # set data from bar
#     # store in to GDATA
#     # query from GDATA

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelOrderTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "code": "testordercode",
#                 "uuid": "uuidtestorderordertestuuid",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "status": ORDERSTATUS_TYPES.SUBMITTED,
#                 "source": SOURCE_TYPES.PORTFOLIO,
#                 "limit_price": 10.12,
#                 "volume": 2000,
#                 "frozen": 20240,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#                 "backtest_id": "testbacktestid1123",
#             }
#         ]

#         def test_ModelOrder_Init(self) -> None:
#             for i in self.params:
#                 o = MOrder()
#                 o.set_source(i["source"])

#         def test_ModelOrder_SetFromData(self) -> None:
#             for i in self.params:
#                 o = MOrder()
#                 o.set_source(i["source"])
#                 o.set(
#                     i["uuid"],
#                     i["code"],
#                     i["direction"],
#                     i["type"],
#                     i["status"],
#                     i["volume"],
#                     i["limit_price"],
#                     i["frozen"],
#                     i["transaction_price"],
#                     i["remain"],
#                     i["fee"],
#                     i["timestamp"],
#                     i["backtest_id"],
#                 )
#                 self.assertEqual(o.code, i["code"])
#                 self.assertEqual(o.direction, i["direction"])
#                 self.assertEqual(o.type, i["type"])
#                 self.assertEqual(o.status, i["status"])
#                 self.assertEqual(o.volume, i["volume"])
#                 self.assertEqual(o.limit_price, i["limit_price"])
#                 self.assertEqual(o.frozen, i["frozen"])
#                 self.assertEqual(o.transaction_price, i["transaction_price"])
#                 self.assertEqual(o.remain, i["remain"])
#                 self.assertEqual(o.fee, i["fee"])
#                 self.assertEqual(o.timestamp, i["timestamp"])
#                 self.assertEqual(o.source, i["source"])

#         def test_ModelOrder_SetFromDataFrame(self) -> None:
#             for i in self.params:
#                 o = MOrder()
#                 df = pd.DataFrame.from_dict(i, orient="index")[0]
#                 o.set(df)
#                 o.set_source(i["source"])
#                 self.assertEqual(o.code, i["code"])
#                 self.assertEqual(o.uuid, i["uuid"])
#                 self.assertEqual(o.direction, i["direction"])
#                 self.assertEqual(o.type, i["type"])
#                 self.assertEqual(o.status, i["status"])
#                 self.assertEqual(o.volume, i["volume"])
#                 self.assertEqual(o.limit_price, i["limit_price"])
#                 self.assertEqual(o.frozen, i["frozen"])
#                 self.assertEqual(o.transaction_price, i["transaction_price"])
#                 self.assertEqual(o.remain, i["remain"])
#                 self.assertEqual(o.fee, i["fee"])
#                 self.assertEqual(o.timestamp, i["timestamp"])
#                 self.assertEqual(o.source, i["source"])
#                 self.assertEqual(o.backtest_id, i["backtest_id"])

#         def test_ModelOrder_Insert(self) -> None:
#             GDATA.create_table(MOrder)
#             size0 = GDATA.get_table_size(MOrder)
#             o = MOrder()
#             GDATA.add(o)
#             size1 = GDATA.get_table_size(MOrder)
#             self.assertEqual(1, size1 - size0)

#         def test_ModelOrder_BatchInsert(self) -> None:
#             GDATA.create_table(MOrder)
#             times = random.random() * 50
#             times = int(times)
#             for j in range(times):
#                 size0 = GDATA.get_table_size(MOrder)
#                 print(f"ModelOrder BatchInsert Test : {j+1}", end="\r")
#                 num = random.random() * 50
#                 num = int(num)
#                 s = []
#                 for i in range(num):
#                     o = MOrder()
#                     s.append(o)
#                 GDATA.add_all(s)
#                 size1 = GDATA.get_table_size(MOrder)
#                 self.assertEqual(len(s), size1 - size0)

#     def test_ModelOrder_Query(self) -> None:
#         num = random.random() * 50
#         num = int(num)
#         GDATA.create_table(MOrder)

#         for i in range(num):
#             o = MOrder()
#             order_id = o.uuid
#             GDATA.add(o)
#             r = (
#                 GDATA.get_driver(MOrder)
#                 .session.query(MOrder)
#                 .filter(MOrder.uuid == order_id)
#                 .first()
#             )
#             self.assertNotEqual(r, None)

#     def test_ModelOrder_Update(self) -> None:
#         num = random.random() * 20
#         num = int(num)
#         GDATA.create_table(MOrder)
#         o = MOrder()
#         uuid = o.uuid
#         GDATA.add(o)
#         for i in range(num):
#             print(f"ModelOrder Update: {i+1}", end="\r")
#             item = (
#                 GDATA.get_driver(MOrder)
#                 .session.query(MOrder)
#                 .filter(MOrder.uuid == uuid)
#                 .first()
#             )
#             s = random.random() * 500
#             s = str(s)
#             s = s.encode("ascii")
#             s = base64.b64encode(s)
#             s = s.decode("ascii")
#             item.code = s
#             GDATA.get_driver(MOrder).session.merge(item)
#             GDATA.get_driver(MOrder).session.commit()
#             GDATA.get_driver(MOrder).session.close()
#             item2 = (
#                 GDATA.get_driver(MOrder)
#                 .session.query(MOrder)
#                 .filter(MOrder.uuid == uuid)
#                 .first()
#             )
#             self.assertEqual(s, item2.code)
