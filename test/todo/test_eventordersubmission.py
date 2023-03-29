import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.event.base_event import EventBase
from ginkgo.backtest.enums import OrderStatus


class EventOrderSubmissionTest(unittest.TestCase):
    """
    UnitTest for Event Order Submission.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventOrderSubmissionTest, self).__init__(*args, **kwargs)

    def test_EventBaseInit_OK(self) -> None:
        print("")
        gl.logger.warn("EventBase初始化 测试开始.")
        s = OrderStatus.NEW
        gl.logger.info(s)
        # params = [
        #     {"type": "priceupdate"},
        #     {"type": "orderfill"},
        #     {"type": "prICeupdate"},
        # ]
        # for i in range(len(params)):
        #     item = params[i]
        #     e = EventBase()
        #     e.event_type = item["type"]
        #     print(e)
        gl.logger.warn("EventBase初始化 测试完成.")
