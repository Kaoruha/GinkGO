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
        e = EventEngine(heartbeat=0.1)
        return e

    def test_InitEngine_OK(self):
        print("")
        gl.logger.warn("EventEngine初始化测试开始")
        params = [
            # # 0heartbeat
            (0.1,),
            (0.12,),
            (1.1,),
        ]
        for i in params:
            e = EventEngine(heartbeat=i[0])
            self.assertEqual(
                first={
                    "heartbeat": i[0],
                },
                second={
                    "heartbeat": e.heartbeat,
                },
            )

        gl.logger.warn("EventEngine初始化测试结束")

    def test_RegisterEventHandler_OK(self):
        print("")
        gl.logger.warn("EventEngine事件Handler注册测试开始")

        def MarketH():
            gl.logger.debug("Try to process MarketEvent")

        def MarketH2():
            gl.logger.debug("Try to process MarketEvent2")

        e = self.reset()
        e.register(EventType.MARKET, MarketH)
        self.assertEqual(
            first={"count": 1, "func": MarketH},
            second={
                "count": len(e.handlers[EventType.MARKET]),
                "func": e.handlers[EventType.MARKET][0],
            },
        )

        e.register(EventType.MARKET, MarketH)
        self.assertEqual(
            first={"count": 1, "func": MarketH},
            second={
                "count": len(e.handlers[EventType.MARKET]),
                "func": e.handlers[EventType.MARKET][0],
            },
        )

        e.register(EventType.MARKET, MarketH2)
        self.assertEqual(
            first={"count": 2, "func": MarketH2},
            second={
                "count": len(e.handlers[EventType.MARKET]),
                "func": e.handlers[EventType.MARKET][1],
            },
        )

        gl.logger.warn("EventEngine事件Handler注册测试结束")

    def test_WithdrawEvent_OK(self):
        print("")
        gl.logger.warn("EventEngine事件注销测试开始")

        def MarketH():
            gl.logger.debug("Try to process MarketEvent")

        e = self.reset()

        e.register(EventType.MARKET, MarketH)
        l = 0
        for k, v in e.handlers.items():
            l += len(v)
        self.assertEqual(first=1, second=l)
        e.withdraw(EventType.MARKET, MarketH)
        l2 = 0
        for k, v in e.handlers.items():
            l2 += len(v)
        self.assertEqual(first=0, second=l2)

        gl.logger.warn("EventEngine事件注销测试结束")

    def test_PutEvent_OK(self):
        print("")
        gl.logger.warn("EventEngine事件推入测试开始")
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
            self.assertEqual(first=i[3], second=e.events_queue.qsize())
        gl.logger.warn("EventEngine事件推入测试结束")

    def test_RegisterGeneral_OK(self):
        print("")
        gl.logger.warn("EventEngine通用事件注册测试开始")
        e = self.reset()

        def genh():
            print(f"This is General Handler")

        def genh2():
            print(f"This is General Handler2")

        e.register_general_handler(genh)
        self.assertEqual(first=1, second=len(e.general_handlers))
        e.register_general_handler(genh)
        self.assertEqual(first=1, second=len(e.general_handlers))
        e.register_general_handler(genh2)
        self.assertEqual(first=2, second=len(e.general_handlers))

        gl.logger.warn("EventEngine通用事件注册测试结束")

    def test_WithdrawGeneral_OK(self):
        print("")
        gl.logger.warn("EventEngine通用事件注销测试开始")
        e = self.reset()

        def genh():
            print(f"This is General Handler")

        e.register_general_handler(genh)
        self.assertEqual(first=1, second=len(e.general_handlers))
        e.withdraw_general_handler(genh)
        self.assertEqual(first=0, second=len(e.general_handlers))
        gl.logger.warn("EventEngine通用事件注销测试结束")
