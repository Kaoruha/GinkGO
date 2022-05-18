import unittest
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.events import *
from ginkgo.backtest.enums import *
from ginkgo.libs import GINKGOLOGGER as gl


class EventEngineTest(unittest.TestCase):
    """
    事件引擎类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventEngineTest, self).__init__(*args, **kwargs)

    def reset(self) -> EventEngine:
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

        def MarketH():
            gl.logger.debug("Try to process MarketEvent")

        def MarketH2():
            gl.logger.debug("Try to process MarketEvent2")

        e = self.reset()
        e.register(EventType.MARKET, MarketH)
        self.assertEqual(
            first={"count": 1, "func": MarketH},
            second={
                "count": len(e._handlers[EventType.MARKET]),
                "func": e._handlers[EventType.MARKET][0],
            },
        )

        e.register(EventType.MARKET, MarketH)
        self.assertEqual(
            first={"count": 1, "func": MarketH},
            second={
                "count": len(e._handlers[EventType.MARKET]),
                "func": e._handlers[EventType.MARKET][0],
            },
        )

        e.register(EventType.MARKET, MarketH2)
        self.assertEqual(
            first={"count": 2, "func": MarketH2},
            second={
                "count": len(e._handlers[EventType.MARKET]),
                "func": e._handlers[EventType.MARKET][1],
            },
        )

        gl.logger.critical("EventEngine事件Handler注册测试结束")

    def test_WithdrawEvent_OK(self):
        print("")
        gl.logger.critical("EventEngine事件注销测试开始")

        def MarketH():
            gl.logger.debug("Try to process MarketEvent")

        e = self.reset()

        e.register(EventType.MARKET, MarketH)
        l = 0
        for k, v in e._handlers.items():
            l += len(v)
        self.assertEqual(first=1, second=l)
        e.withdraw(EventType.MARKET, MarketH)
        l2 = 0
        for k, v in e._handlers.items():
            l2 += len(v)
        self.assertEqual(first=0, second=l2)

        gl.logger.critical("EventEngine事件注销测试结束")

    def test_PutEvent_OK(self):
        print("")
        gl.logger.critical("EventEngine事件推入测试开始")
        e = self.reset()
        params = [
            # 0code,1raw,2type,3count
            ("testcode", 1, MarketEventType.NEWS, 1),
            ("testcode", 1, MarketEventType.NEWS, 2),
            ("testcode2", 31, MarketEventType.BAR, 3),
            ("testcode3", 21, MarketEventType.TICK, 4),
        ]
        for i in params:
            events = MarketEvent(code=i[0], raw=i[1], markert_event_type=i[2])
            e.put(events)
            self.assertEqual(first=i[3], second=e._event_queue.qsize())
        gl.logger.critical("EventEngine事件推入测试结束")

    def test_RegisterGeneral_OK(self):
        print("")
        gl.logger.critical("EventEngine通用事件注册测试开始")
        e = self.reset()

        def genh():
            print(f"This is General Handler")

        def genh2():
            print(f"This is General Handler2")

        e.register_general_handler(genh)
        self.assertEqual(first=1, second=len(e._general_handlers))
        e.register_general_handler(genh)
        self.assertEqual(first=1, second=len(e._general_handlers))
        e.register_general_handler(genh2)
        self.assertEqual(first=2, second=len(e._general_handlers))

        gl.logger.critical("EventEngine通用事件注册测试结束")

    def test_WithdrawGeneral_OK(self):
        print("")
        gl.logger.critical("EventEngine通用事件注销测试开始")
        e = self.reset()

        def genh():
            print(f"This is General Handler")

        e.register_general_handler(genh)
        self.assertEqual(first=1, second=len(e._general_handlers))
        e.withdraw_general_handler(genh)
        self.assertEqual(first=0, second=len(e._general_handlers))
        gl.logger.critical("EventEngine通用事件注销测试结束")

    def test_RegisterTimer_OK(self):
        print("")
        gl.logger.critical("EventEngine计时器事件注册测试开始")
        e = self.reset()

        def timerh():
            print(f"This is Timer Handler")

        def timerh2():
            print(f"This is Timer Handler2")

        e.register_timer_handler(timerh)
        self.assertEqual(first=1, second=len(e._timer_handlers))
        e.register_timer_handler(timerh)
        self.assertEqual(first=1, second=len(e._timer_handlers))
        e.register_timer_handler(timerh2)
        self.assertEqual(first=2, second=len(e._timer_handlers))
        gl.logger.critical("EventEngine计时器事件注册测试结束")

    def test_WithdrawTimer_OK(self):
        print("")
        gl.logger.critical("EventEngine计时器事件注销测试开始")
        e = self.reset()

        def timerh():
            print(f"This is Timer Handler")

        e.register_timer_handler(timerh)
        self.assertEqual(first=1, second=len(e._timer_handlers))

        e.withdraw_timer_handler(timerh)
        self.assertEqual(first=0, second=len(e._timer_handlers))
        gl.logger.critical("EventEngine计时器事件注销测试结束")
