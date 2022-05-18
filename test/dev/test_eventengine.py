import unittest
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.libs import GINKGOLOGGER as gl


class EventEngineTest(unittest.TestCase):
    """
    事件引擎类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventEngineTest, self).__init__(*args, **kwargs)

    def reset_engine(self) -> EventEngine:
        e = EventEngine(heartbeat=0.1, timersleep=2, is_timer_on=True)
        return e

    def test_InitEngine_OK(self):
        print("")
        gl.logger.critical("EventEngine初始化测试开始")
        params = [
            # # 0heartbeat, 1timebreak, 2timeron
            (0.1, 0.1, True),
            (0.12, 0.4, True),
            (1.1, 2.1, False),
        ]
        for i in params:
            e = EventEngine(heartbeat=i[0], timersleep=i[1], is_timer_on=i[2])
            self.assertEqual(
                first={
                    "heartbeat": i[0],
                    "timersleep": i[1],
                    "timeron": i[2],
                },
                second={
                    "heartbeat": e.heartbeat,
                    "timersleep": e.timersleep,
                    "timeron": e._timer_on,
                },
            )

        gl.logger.critical("EventEngine初始化测试结束")

    def test_RegisterEventHandler_OK(self):
        print("")
        gl.logger.critical("EventEngine事件Handler注册测试开始")
        gl.logger.critical("EventEngine事件Handler注册测试结束")

    def test_WithdrawEvent_OK(self):
        print("")
        gl.logger.critical("EventEngine事件注销测试开始")
        gl.logger.critical("EventEngine事件注销测试结束")

    def test_PutEvent_OK(self):
        print("")
        gl.logger.critical("EventEngine事件推入测试开始")
        gl.logger.critical("EventEngine事件推入测试结束")

    def test_RegisterGeneral_OK(self):
        print("")
        gl.logger.critical("EventEngine通用事件注册测试开始")
        gl.logger.critical("EventEngine通用事件注册测试结束")

    def test_WithdrawGeneral_OK(self):
        print("")
        gl.logger.critical("EventEngine通用事件注销测试开始")
        gl.logger.critical("EventEngine通用事件注销测试结束")

    def test_RegisterTimer_OK(self):
        print("")
        gl.logger.critical("EventEngine计时器事件注册测试开始")
        gl.logger.critical("EventEngine计时器事件注册测试结束")

    def test_WithdrawTimer_OK(self):
        print("")
        gl.logger.critical("EventEngine计时器事件注销测试开始")
        gl.logger.critical("EventEngine计时器事件注销测试结束")

    def test_run_notimer(self):
        print("")
        gl.logger.critical("EventEngine无计时器运行测试开始")
        gl.logger.critical("EventEngine无计时器运行测试结束")

    def test_run_timer(self):
        print("")
        gl.logger.critical("EventEngine计时器运行测试开始")
        gl.logger.critical("EventEngine计时器运行测试结束")

    def test_run_withtimer(self):
        print("")
        gl.logger.critical("EventEngine运行测试开始")
        gl.logger.critical("EventEngine运行测试结束")
