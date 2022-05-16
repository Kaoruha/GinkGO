import unittest
from ginkgo.backtest.event_engine import EventEngine


class EventEngineTest(unittest.TestCase):
    """
    事件引擎类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventEngineTest, self).__init__(*args, **kwargs)
        self.engine = None

    def reset_engine(self) -> EventEngine:
        self.engine = EventEngine(heartbeat=0.001)
        return self.engine

    def test_InitEngine_OK(self):
        gl.logger.critical("EventEngine初始化测试开始")
        gl.logger.critical("EventEngine初始化测试结束")

    def test_ChangeHeartBreak_OK(self):
        gl.logger.critical("EventEngine设置心跳间隔测试开始")
        gl.logger.critical("EventEngine设置心跳间隔测试结束")

    def test_RegisterEventHandler_OK(self):
        gl.logger.critical("EventEngine事件Handler注册测试开始")
        gl.logger.critical("EventEngine事件Handler注册测试结束")

    def test_WithdrawEvent_OK(self):
        gl.logger.critical("EventEngine事件注销测试开始")
        gl.logger.critical("EventEngine事件注销测试结束")

    def test_PutEvent_OK(self):
        gl.logger.critical("EventEngine事件推入测试开始")
        gl.logger.critical("EventEngine事件推入测试结束")

    def test_RegisterGeneral_OK(self):
        gl.logger.critical("EventEngine通用事件注册测试开始")
        gl.logger.critical("EventEngine通用事件注册测试结束")

    def test_WithdrawGeneral_OK(self):
        gl.logger.critical("EventEngine通用事件注销测试开始")
        gl.logger.critical("EventEngine通用事件注销测试结束")

    # def test_get_price(self):
    #     """
    #     利用引擎获取价格数据
    #     """
    #     e = self.reset_engine()
    #     e.get_price('sh.688067', '2021-12-23')
    #     e.get_price('sh.688067', '2021-12-24')
    #     e.get_price('sz.002201', '2021-12-23')
    #     self.assertEqual(
    #         first={
    #             'info_queue': 3,
    #             'stock_list': 2,
    #         },
    #         second={
    #             'info_queue': e._info_queue.qsize(),
    #             'stock_list': len(e._price_pool.keys()),
    #         }
    #     )
