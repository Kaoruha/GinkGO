# import unittest
# import time
# import datetime
# import pandas as pd
# from ginkgo.libs import GINKGOLOGGER as gl
# from ginkgo.backtest.order import Order
# from ginkgo.data.ginkgo_data import GINKGODATA
# from ginkgo.data.models.model_signal import MSignal
# from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

# from ginkgo.libs.ginkgo_conf import GINKGOCONF


# class ModelSignalTest(unittest.TestCase):
#     """
#     UnitTest for Signal
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelSignalTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "code": "testordercode",
#                 "direction": DIRECTION_TYPES.LONG,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_ModelSignal_Init(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         result = True
#         for i in self.params:
#             try:
#                 s = MSignal()
#                 s.set(
#                     i["code"],
#                     i["direction"],
#                     i["timestamp"],
#                     i["source"],
#                 )
#             except Exception as e:
#                 result = False
#         self.assertEqual(result, True)


#     def test_ModelSignal_SetFromData(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         for i in self.params:
#             o = MSignal()
#             data = {
#                 "code": i["code"],
#                 "direction": i["direction"],
#                 "type": i["order_type"],
#                 "status": i["status"],
#                 "volume": i["volume"],
#                 "timestamp": i["timestamp"],
#                 "limit_price": i["limit_price"],
#             }
#             o.set(pd.Series(data))
#             o.set_source(i["source"])
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.direction, i["direction"])
#             self.assertEqual(o.type, i["order_type"])
#             self.assertEqual(o.status, i["status"])
#             self.assertEqual(o.volume, i["volume"])
#             self.assertEqual(o.limit_price, i["limit_price"])
#             self.assertEqual(o.limit_price, i["limit_price"])
#             self.assertEqual(o.timestamp, i["timestamp"])

#     def test_ModelSignal_Insert(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         result = True
#         GINKGODATA.drop_table(MSignal)
#         GINKGODATA.create_table(MSignal)
#         try:
#             o = MSignal()
#             GINKGODATA.add(o)
#             GINKGODATA.commit()
#         except Exception as e:
#             result = False

#         self.assertEqual(result, True)

#     def test_ModelSignal_BatchInsert(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         result = True
#         GINKGODATA.drop_table(MSignal)
#         GINKGODATA.create_table(MSignal)
#         try:
#             s = []
#             for i in range(10):
#                 o = MSignal()
#                 s.append(o)

#             GINKGODATA.add_all(s)
#             GINKGODATA.commit()
#         except Exception as e:
#             result = False

#         self.assertEqual(result, True)

#     def test_ModelSignal_Query(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         result = True
#         GINKGODATA.drop_table(MSignal)
#         GINKGODATA.create_table(MSignal)
#         try:
#             o = MSignal()
#             GINKGODATA.add(o)
#             GINKGODATA.commit()
#             r = GINKGODATA.session.query(MSignal).first()
#         except Exception as e:
#             result = False

#         self.assertNotEqual(r, None)
#         self.assertEqual(result, True)
