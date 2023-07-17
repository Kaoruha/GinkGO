# import unittest
# import time
# import datetime
# import pandas as pd
# from ginkgo.backtest.order import Order
# from ginkgo.data.models import MOrder
# from ginkgo.enums import ORDER_TYPES, DIRECTION_TYPES, SOURCE_TYPES
# from ginkgo import GCONF, GLOG
# from ginkgo.data.ginkgo_data import GDATA


# class OrderTest(unittest.TestCase):
#     """
#     UnitTest for order.
#     """

#     # Init
#     # Change
#     # Amplitude

#     def __init__(self, *args, **kwargs) -> None:
#         super(OrderTest, self).__init__(*args, **kwargs)
#         self.dev = False
#         self.params = [
#             {
#                 "code": "sh.0000001",
#                 "timestamp": "2020-01-01 02:02:32",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.LIMITORDER,
#                 "volume": 100001,
#                 "limit_price": 10.0,
#                 "source": SOURCE_TYPES.SINA,
#             },
#             {
#                 "code": "sh.0000001",
#                 "timestamp": datetime.datetime.now(),
#                 "direction": DIRECTION_TYPES.SHORT,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 10002,
#                 "limit_price": None,
#                 "source": SOURCE_TYPES.SINA,
#             },
#         ]

#     def test_Order_Init(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         result = False
#         try:
#             o = Order()
#             result = True
#         except Exception as e:
#             pass

#         self.assertEqual(result, True)

#     def test_Order_Set(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for item in self.params:
#             o = Order()
#             o.set(
#                 item["code"],
#                 item["direction"],
#                 item["type"],
#                 item["volume"],
#                 item["limit_price"],
#                 item["timestamp"],
#             )
#             o.set_source(item["source"])
#             self.assertEqual(o.code, item["code"])
#             self.assertEqual(o.direction, item["direction"])
#             self.assertEqual(o.type, item["type"])
#             self.assertEqual(o.volume, item["volume"])
#             self.assertEqual(o.limit_price, item["limit_price"])
#             self.assertEqual(o.source, item["source"])

#     def test_Order_SetFromDataFrame(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for item in self.params:
#             data = {
#                 "timestamp": item["timestamp"],
#                 "code": item["code"],
#                 "direction": item["direction"],
#                 "type": item["type"],
#                 "volume": item["volume"],
#                 "status": 2,
#                 "limit_price": item["limit_price"],
#                 "uuid": "",
#                 "source": item["source"],
#             }
#             df = pd.Series(data)
#             o = Order()
#             o.set(df)
#             self.assertEqual(o.code, item["code"])
#             self.assertEqual(o.direction, item["direction"])
#             self.assertEqual(o.type, item["type"])
#             self.assertEqual(o.volume, item["volume"])
#             self.assertEqual(o.limit_price, item["limit_price"])
#             self.assertEqual(o.source, item["source"])

#     def test_Order_SetFromModel(self) -> None:
#         time.sleep(GCONF.HEARTBEAT)
#         for item in self.params:
#             data = {
#                 "timestamp": item["timestamp"],
#                 "code": item["code"],
#                 "direction": item["direction"],
#                 "type": item["type"],
#                 "volume": item["volume"],
#                 "status": 1,
#                 "limit_price": item["limit_price"],
#                 "source": item["source"],
#             }
#             df = pd.Series(data)
#             mo = MOrder()
#             mo.set(df)
#             GDATA.drop_table(MOrder)
#             GDATA.create_table(MOrder)
#             GDATA.add(mo)
#             GDATA.commit()
#             filter_rs: MOrder = GDATA.get_order(mo.uuid)
#             new_df = filter_rs.to_dataframe()
#             o = Order()
#             o.set(new_df)
#             self.assertEqual(o.code, item["code"])
#             self.assertEqual(o.direction, item["direction"])
#             self.assertEqual(o.type, item["type"])
#             self.assertEqual(o.volume, item["volume"])
#             self.assertEqual(o.limit_price, item["limit_price"])
#             self.assertEqual(o.source, item["source"])
