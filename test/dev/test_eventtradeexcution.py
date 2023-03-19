# import unittest
# import datetime
# from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
# from ginkgo.backtest.event.base_event import EventBase


# class EventTradeExcutionTest(unittest.TestCase):
#     """
#     UnitTest for Event Trade Excution.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(EventTradeExcutionTest, self).__init__(*args, **kwargs)

#     def test_EventBaseInit_OK(self) -> None:
#         print("")
#         gl.logger.warn("EventBase初始化 测试开始.")
#         params = [
#             {"type": "priceupdate"},
#             {"type": "orderfill"},
#             {"type": "prICeupdate"},
#         ]
#         for i in range(len(params)):
#             item = params[i]
#             e = EventBase()
#             e.event_type = item["type"]
#             print(e)
#         gl.logger.warn("EventBase初始化 测试完成.")
