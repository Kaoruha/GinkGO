# import datetime
# import uuid
# import unittest
# import pandas as pd
# from time import sleep
# from ginkgo.backtest.events import (
#     EventBase,
#     EventCapitalUpdate,
#     EventOrderCanceled,
#     EventOrderExecute,
#     EventOrderFilled,
#     EventOrderRelated,
#     EventOrderSubmitted,
#     EventPositionUpdate,
#     EventPriceUpdate,
# )
# from ginkgo.data.models.model_order import MOrder
# from ginkgo.data.models.model_order import MOrder
# from ginkgo.data.ginkgo_data import GDATA
# from ginkgo.libs.ginkgo_logger import GLOG
# from ginkgo.backtest.bar import Bar
# from ginkgo.backtest.tick import Tick
# from ginkgo.libs import datetime_normalize
# from ginkgo.enums import (
#     DIRECTION_TYPES,
#     ORDER_TYPES,
#     ORDERSTATUS_TYPES,
#     SOURCE_TYPES,
#     FREQUENCY_TYPES,
#     PRICEINFO_TYPES,
#     EVENT_TYPES,
# )


# class EventBaseTest(unittest.TestCase):
#     """
#     UnitTest for BaseEvent.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventBaseTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "source": SOURCE_TYPES.SIM,
#                 "type": EVENT_TYPES.PRICEUPDATE,
#                 "timestamp": datetime.datetime.now(),
#             },
#             {
#                 "source": SOURCE_TYPES.TEST,
#                 "type": "orderfill",
#                 "timestamp": "2020-01-01",
#             },
#             {
#                 "source": SOURCE_TYPES.TUSHARE,
#                 "type": "ORDERSubmission",
#                 "timestamp": 19000101,
#             },
#         ]

#     def test_EventBase_Init(self) -> None:
#         for i in self.params:
#             e = EventBase()
#             e.set_type(["type"])
#             e.set_source(i["source"])
#             e.set_time(i["timestamp"])

#             self.assertEqual(e.source, i["source"])
#             self.assertEqual(e.timestamp, datetime_normalize(i["timestamp"]))


# class EventCapitalUpdateTest(unittest.TestCase):
#     """
#     UnitTest for Event Capital Update.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventCapitalUpdateTest, self).__init__(*args, **kwargs)
#         # Params for order
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "uuid": uuid.uuid4().hex,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.FILLED,
#                 "limit_price": 2.2,
#                 "frozen": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventCU_Init(self) -> None:
#         for i in self.params:
#             e = EventCapitalUpdate()

#     def test_EventCU_GetOrder(self) -> None:
#         # Clean the Table
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             o = MOrder()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o.set(df)
#             GDATA.add(o)
#             GDATA.commit()
#             # # Try Get
#             e = EventCapitalUpdate(o.uuid)
#             self.assertEqual(e.order_id, o.uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["direction"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.frozen, i["frozen"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])


# class EventOrderCanceledTest(unittest.TestCase):
#     """
#     UnitTest for Event Capital Update.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventOrderCanceledTest, self).__init__(*args, **kwargs)
#         # Params for order
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "uuid": uuid.uuid4().hex,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.CANCELED,
#                 "limit_price": 2.2,
#                 "frozen": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventOC_Init(self) -> None:
#         for i in self.params:
#             e = EventOrderCanceled()

#     def test_EventOC_GetOrder(self) -> None:
#         # Clean the Table
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             # Insert an Order
#             o = MOrder()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o.set(df)
#             GDATA.add(o)
#             GDATA.commit()
#             # Try Get
#             e = EventOrderCanceled(o.uuid)
#             self.assertEqual(e.order_id, o.uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["direction"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.frozen, i["frozen"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])


# class EventOrderExecuteTest(unittest.TestCase):
#     """
#     UnitTest for Event Capital Update.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventOrderExecuteTest, self).__init__(*args, **kwargs)
#         # Params for order
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "uuid": uuid.uuid4().hex,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.FILLED,
#                 "limit_price": 2.2,
#                 "frozen": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventOC_Init(self) -> None:
#         for i in self.params:
#             e = EventOrderExecute()

#     def test_EventOC_GetOrder(self) -> None:
#         # Clean the Table
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             # Insert an Order
#             o = MOrder()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o.set(df)
#             GDATA.add(o)
#             GDATA.commit()
#             # Try Get
#             e = EventOrderExecute(o.uuid)
#             self.assertEqual(e.order_id, o.uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["direction"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.frozen, i["frozen"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])


# class EventOrderFilledTest(unittest.TestCase):
#     """
#     UnitTest for Event Capital Update.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventOrderFilledTest, self).__init__(*args, **kwargs)
#         # Params for order
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "uuid": uuid.uuid4().hex,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.FILLED,
#                 "limit_price": 2.2,
#                 "frozen": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventOF_Init(self) -> None:
#         for i in self.params:
#             e = EventOrderFilled()

#     def test_EventOF_GetOrder(self) -> None:
#         # Clean the Table
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             # Insert an Order
#             o = MOrder()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o.set(df)
#             GDATA.add(o)
#             GDATA.commit()
#             # Try Get
#             e = EventOrderFilled(o.uuid)
#             self.assertEqual(e.order_id, o.uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["direction"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.frozen, i["frozen"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])


# class EventOrderRelatedTest(unittest.TestCase):
#     """
#     UnitTest for Event Capital Update.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventOrderRelatedTest, self).__init__(*args, **kwargs)
#         # Params for order
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "uuid": uuid.uuid4().hex,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.FILLED,
#                 "limit_price": 2.2,
#                 "frozen": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventOR_Init(self) -> None:
#         for i in self.params:
#             e = EventOrderRelated()

#     def test_EventOR_GetOrder(self) -> None:
#         # Clean the Table
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             # Insert an Order
#             o = MOrder()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o.set(df)
#             GDATA.add(o)
#             GDATA.commit()
#             # Try Get
#             e = EventOrderRelated(o.uuid)
#             self.assertEqual(e.order_id, o.uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["direction"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.frozen, i["frozen"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])


# class EventOrderSubmittedTest(unittest.TestCase):
#     """
#     UnitTest for Event Capital Update.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventOrderSubmittedTest, self).__init__(*args, **kwargs)
#         # Params for order
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "uuid": uuid.uuid4().hex,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.FILLED,
#                 "limit_price": 2.2,
#                 "frozen": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventOR_Init(self) -> None:
#         for i in self.params:
#             e = EventOrderSubmitted()

#     def test_EventOR_GetOrder(self) -> None:
#         # Clean the Table
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             # Insert an Order
#             o = MOrder()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o.set(df)
#             GDATA.add(o)
#             GDATA.commit()
#             # Try Get
#             e = EventOrderSubmitted(o.uuid)
#             self.assertEqual(e.order_id, o.uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["direction"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.frozen, i["frozen"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])


# class EventPositionUpdateTest(unittest.TestCase):
#     """
#     UnitTest for OrderSubmission.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventPositionUpdateTest, self).__init__(*args, **kwargs)
#         self.dev = False
#         self.params = [
#             {
#                 "code": "unit_test_code",
#                 "uuid": uuid.uuid4().hex,
#                 "source": SOURCE_TYPES.BAOSTOCK,
#                 "direction": DIRECTION_TYPES.LONG,
#                 "type": ORDER_TYPES.MARKETORDER,
#                 "volume": 2000,
#                 "status": ORDERSTATUS_TYPES.FILLED,
#                 "limit_price": 2.2,
#                 "frozen": 44000,
#                 "transaction_price": 0,
#                 "remain": 0,
#                 "fee": 0,
#                 "timestamp": datetime.datetime.now(),
#             }
#         ]

#     def test_EventPU_Init(self) -> None:
#         for i in self.params:
#             e = EventPositionUpdate()

#     def test_EventPU_GetOrder(self) -> None:
#         # Clean the Table
#         GDATA.create_table(MOrder)
#         for i in self.params:
#             # Insert an Order
#             o = MOrder()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o.set(df)
#             GDATA.add(o)
#             GDATA.commit()
#             # Try Get
#             e = EventPositionUpdate(o.uuid)
#             self.assertEqual(e.order_id, o.uuid)
#             self.assertEqual(e.code, i["code"])
#             self.assertEqual(e.direction, i["direction"])
#             self.assertEqual(e.order_type, i["type"])
#             self.assertEqual(e.volume, i["volume"])
#             self.assertEqual(e.frozen, i["frozen"])
#             self.assertEqual(e.transaction_price, i["transaction_price"])
#             self.assertEqual(e.remain, i["remain"])


# class EventPriceUpdateTest(unittest.TestCase):
#     """
#     UnitTest for OrderSubmission.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventPriceUpdateTest, self).__init__(*args, **kwargs)
#         self.dev = False
#         self.params = [
#             {
#                 "code": "unittest_code",
#                 "source": SOURCE_TYPES.TEST,
#                 "timestamp": "2022-02-12 02:12:20",
#                 "frequency": FREQUENCY_TYPES.DAY,
#                 "open": 19,
#                 "high": 19,
#                 "low": 19,
#                 "close": 19,
#                 "volume": 1900,
#                 "price": 10.21,
#             },
#             {
#                 "code": "unittest_code22",
#                 "source": SOURCE_TYPES.TUSHARE,
#                 "timestamp": "2022-02-12 02:12:20",
#                 "frequency": FREQUENCY_TYPES.DAY,
#                 "open": 11,
#                 "high": 12,
#                 "low": 10.22,
#                 "close": 12.1,
#                 "volume": 19010,
#                 "price": 10.01,
#             },
#         ]

#     def test_EventPU_Init(self) -> None:
#         for i in self.params:
#             e = EventPriceUpdate()

#     def test_EventPU_Bar(self) -> None:
#         for i in self.params:
#             b = Bar()
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             b.set(df)
#             e = EventPriceUpdate()
#             e.set(b)
#             e.set_source(i["source"])
#             self.assertEqual(i["code"], e.code)
#             self.assertEqual(i["source"], e.source)
#             self.assertEqual(datetime_normalize(i["timestamp"]), e.timestamp)
#             self.assertEqual(i["volume"], e.volume)
#             self.assertEqual(i["open"], e.open)
#             self.assertEqual(i["high"], e.high)
#             self.assertEqual(i["low"], e.low)
#             self.assertEqual(i["close"], e.close)


# #     # TODO Tick
