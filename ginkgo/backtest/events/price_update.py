import datetime
from ginkgo.backtest.events.base_event import EventBase
from functools import singledispatchmethod
from ginkgo.enums import EVENT_TYPES, PRICEINFO_TYPES, SOURCE_TYPES
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick
from ginkgo.libs import base_repr
from ginkgo import GLOG
from ginkgo.data.ginkgo_data import GDATA


class EventPriceUpdate(EventBase):
    """
    PriceUpdate Only after new price info comes.
    """

    def __init__(self, price_info: Bar or Tick = None, *args, **kwargs) -> None:
        super(EventPriceUpdate, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.PRICEUPDATE
        self._price_type = None

        if price_info:
            self.set(price_info)

    @property
    def price_type(self):
        return self._price_type

    @property
    def price_info(self):
        if self._price_type == PRICEINFO_TYPES.BAR:
            return self._bar
        elif self._price_type == PRICEINFO_TYPES.TICK:
            return self._tick
        else:
            GLOG.logger.warn(f"!! The PriceInfo not set yet. Please check your code")
            return None

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(self, price: Bar):
        self._price_type = PRICEINFO_TYPES.BAR
        self._bar = price
        self._tick = None

    @set.register
    def _(self, price: Tick):
        self._price_type = PRICEINFO_TYPES.TICK
        self._tick = price
        self._bar = None

    @property
    def code(self) -> str:
        if self.price_info is None:
            return None
        return self.price_info.code

    @property
    def timestamp(self) -> datetime.datetime:
        if self.price_info is None:
            return None
        return self.price_info.timestamp

    @property
    def price(self) -> float:
        if self.price_info is None:
            return None
        if self.price_type == PRICEINFO_TYPES.TICK:
            return self.price_info.price
        else:
            GLOG.logger.warn(
                f"The Price is Bar Type, but your are asking tick type price value."
            )
            return None

    @property
    def volume(self) -> int:
        if self.price_info is None:
            return None
        return self.price_info.volume

    @property
    def open(self) -> float:
        if self.price_info is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.price_info.open
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type open value."
            )
            return None

    @property
    def high(self) -> float:
        if self.price_info is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.price_info.high
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type high value."
            )
            return None

    @property
    def low(self) -> float:
        if self.price_info is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.price_info.low
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type low value."
            )
            return None

    @property
    def close(self) -> float:
        if self.price_info is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.price_info.close
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type close value."
            )
            return None

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
