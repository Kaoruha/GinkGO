from ginkgo.backtest.event.base_event import EventBase
from ginkgo.backtest.enums import EventType, PriceInfo
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick


class EventPriceUpdate(EventBase):
    def __init__(self, price_info, *args, **kwargs) -> None:
        super(EventPriceUpdate, self).__init__(*args, **kwargs)
        self.__type = EventType.PRICEUPDATE
        self.__price_type = None
        self.code = "sh.600001"
        self.volume = 0
        self.__bar = None
        self.__tick = None

    @property
    def price_type(self):
        return self.__price_type

    @property
    def price_info(self):
        if self.price_type == PriceInfo.BAR:
            return self.__bar
        elif self.price_type == PriceInfo.TICK:
            return self.__tick
        else:
            return None

    def update_bar(self, bar: Bar) -> None:
        self.__price_type = PriceInfo.BAR
        if not isinstance(bar, Bar):
            return
        else:
            self.__tick = None
            self.__bar = bar
            self.update_time(bar.timestamp)

    def update_tick(self, tick: Tick) -> None:
        self.__price_type = PriceInfo.TICK
        if not isinstance(tick, Tick):
            return
        else:
            self.__bar = None
            self.__tick = tick
            self.update_time(tick.timestamp)
