# import unittest
# import datetime
# from time import sleep
# from ginkgo.backtest.events.price_update import EventPriceUpdate
# from ginkgo.backtest.bar import Bar
# from ginkgo.backtest.tick import Tick
# from ginkgo import GCONF, GLOG
# from ginkgo.enums import (
#     DIRECTION_TYPES,
#     ORDER_TYPES,
#     ORDERSTATUS_TYPES,
#     SOURCE_TYPES,
#     FREQUENCY_TYPES,
#     PRICEINFO_TYPES,
# )


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
#                 "sim_code": "unittest_code",
#                 "sim_source": SOURCE_TYPES.BAOSTOCK,
#                 "sim_timestampe": "2022-02-12 02:12:20",
#                 "sim_fre": FREQUENCY_TYPES.DAY,
#                 "sim_open": 19,
#                 "sim_high": 19,
#                 "sim_low": 19,
#                 "sim_close": 19,
#                 "sim_volume": 1900,
#                 "sim_price": 10.21,
#             }
#         ]

#     def test_EventPU_Init(self) -> None:
#         sleep(GCONF.HEARTBEAT)
#         result = True
#         for i in self.params:
#             try:
#                 e = EventPriceUpdate()
#             except Exception as e:
#                 result = False
#         self.assertEqual(result, True)

#     def test_EventPU_InitBar(self) -> None:
#         sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             b = Bar(
#                 i["sim_code"],
#                 i["sim_open"],
#                 i["sim_high"],
#                 i["sim_low"],
#                 i["sim_close"],
#                 i["sim_volume"],
#                 i["sim_fre"],
#                 i["sim_timestampe"],
#             )
#             e = EventPriceUpdate(b)
#             self.assertEqual(e.price_type, PRICEINFO_TYPES.BAR)

#     def test_EventPU_InitTick(self) -> None:
#         sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             t = Tick(
#                 i["sim_code"], i["sim_price"], i["sim_volume"], i["sim_timestampe"]
#             )
#             e = EventPriceUpdate(t)
#             self.assertEqual(e.price_type, PRICEINFO_TYPES.TICK)
