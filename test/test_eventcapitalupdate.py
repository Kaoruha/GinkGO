import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.event.capital_update import EventCapitalUpdate
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.ginkgo_data import GINKGODATA


class EventCapitalUpdateTest(unittest.TestCase):
    """
    UnitTest for Event Capital Update.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventCapitalUpdateTest, self).__init__(*args, **kwargs)
        self.params = [{"code": "test"}]

    def test_EventBaseInit_OK(self) -> None:
        print("")
        gl.logger.warn("EventCaptitalUpdate 初始化 测试开始.")
        for i in self.params:
            GINKGODATA.drop_table(MOrder)
            GINKGODATA.create_table(MOrder)
            o = MOrder()
            o.status = 3
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate()
            e.get_order(uuid)
            print(e)
        gl.logger.warn("EventCapitalUpdate 初始化 测试完成.")
