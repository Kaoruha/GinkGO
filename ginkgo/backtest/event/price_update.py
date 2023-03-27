from ginkgo.backtest.event.base_event import EventBase
from ginkgo.enums import EVENT_TYPES, PRICEINFO_TYPES, SOURCE_TYPES
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick
from ginkgo.libs.ginkgo_pretty import pretty_repr


class EventPriceUpdate(EventBase):
    def __init__(self, price_info, *args, **kwargs) -> None:
        super(EventPriceUpdate, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.PRICEUPDATE
        self.__price_type = None
        self.__bar = None
        self.__tick = None

        if isinstance(price_info, Bar):
            self.update_bar(price_info)
        elif isinstance(price_info, Tick):
            self.update_tick(price_info)

    @property
    def price_type(self):
        return self.__price_type

    @property
    def price_info(self):
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.__bar
        elif self.price_type == PRICEINFO_TYPES.TICK:
            return self.__tick
        else:
            return None

    def update_bar(self, bar: Bar) -> None:
        self.__price_type = PRICEINFO_TYPES.BAR
        if not isinstance(bar, Bar):
            return
        else:
            self.__tick = None
            self.__bar = bar
            self.__timestamp = bar.timestamp

    def update_tick(self, tick: Tick) -> None:
        self.__price_type = PRICEINFO_TYPES.TICK
        if not isinstance(tick, Tick):
            return
        else:
            self.__bar = None
            self.__tick = tick
            self.__timestamp = tick.timestamp

    def __repr__(self):
        mem = f"Mem   : {hex(id(self))}"
        event_id = f"ID    : {self.id}"
        source = f"Source: {self.source} : {self.source.value}"
        date = f"Date  : {self.timestamp}"
        event_t = f"Type  : {self.event_type} : {self.event_type.value}"
        price_t = f"Price : {self.price_type} : {self.price_type.value}"
        msg = [mem, event_id, source, date, event_t, price_t]

        if self.price_type == PRICEINFO_TYPES.BAR:
            open_ = f"Open  : {self.__bar.open}"
            high = f"High  : {self.__bar.high}"
            low = f"Low   : {self.__bar.low}"
            close = f"Close : {self.__bar.close}"
            volume = f"Volume: {self.__bar.volume}"
            msg.append(open_)
            msg.append(high)
            msg.append(low)
            msg.append(close)
            msg.append(volume)
        elif self.price_type == PRICEINFO_TYPES.TICK:
            price = f"Price : {self.__tick.price}"
            volume = f"Volume: {self.__tick.volume}"
            msg.append(price)
            msg.append(volume)

        return pretty_repr(EventPriceUpdate.__name__, msg, 50)
