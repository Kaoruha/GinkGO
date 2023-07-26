# import unittest
# import datetime
# from ginkgo.backtest.events.capital_update import EventCapitalUpdate
# from ginkgo.data.models.model_order import MOrder
# from ginkgo.backtest.bar import Bar
# from ginkgo.data.ginkgo_data import GDATA
# from ginkgo import GLOG
# from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


# class EventCapitalUpdateTest(unittest.TestCase):
#     """
#     UnitTest for Event Capital Update.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventCapitalUpdateTest, self).__init__(*args, **kwargs)
#         self.dev = False
#         # Params for order
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "dir": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.FILLED,
#                 "limit_price": 2.2,
#                 "freeze": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventCU_Init(self) -> None:
#         for i in self.params:
#             e = EventCapitalUpdate()

#     def test_EventCU_GetOrder(self) -> None:
#         result = True
#         # Clean the Table
#         GDATA.drop_table(MOrder)
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             # Insert an Order
#             o = MOrder()
#             o.set(
#                 i["code"],
#                 i["dir"],
#                 i["type"],
#                 i["status"],
#                 i["volume"],
#                 i["limit_price"],
#                 i["freeze"],
#                 i["transaction_price"],
#                 i["remain"],
#                 i["timestamp"],
#             )
#             GDATA.add(o)
#             GDATA.commit()
#             # Try Get
#             uuid = o.uuid
#             e = EventCapitalUpdate()
#             e.get_order(uuid)
#             self.assertEqual(e.order_id, uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["dir"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.freeze, i["freeze"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])
