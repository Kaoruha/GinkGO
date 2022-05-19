from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.events import *
from ginkgo.backtest.enums import *


e = EventEngine(heartbeat=0, timersleep=2, is_timer_on=False)

me = MarketEvent(
    code="test_event", raw="fuckingcrazy", markert_event_type=MarketEventType.NEWS
)


class test(object):
    def __init__(self):
        self.count = 0
        self.timercount = 0

    def mh(self, event):
        print(f"process {event.code} {self.count}")
        self.count += 1
        if self.count < 200:
            e.put(event)

    def th(self):
        e.put(me)
        self.timercount += 1
        print(f"定期任务 {self.timercount}")


t = test()
e.set_timerlimit(20)
e.register(event_type=EventType.MARKET, handler=t.mh)
e.register_timer_handler(t.th)

e.start()
e.put(me)
