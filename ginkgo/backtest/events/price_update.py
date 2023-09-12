import datetime
import pandas as pd
from ginkgo.backtest.events.base_event import EventBase
from functools import singledispatchmethod
from ginkgo.enums import EVENT_TYPES, PRICEINFO_TYPES, SOURCE_TYPES
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick
from ginkgo.libs import pretty_repr
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
    def value(self):
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
        if self.value is None:
            return None
        return self.value.code

    @property
    def timestamp(self) -> datetime.datetime:
        if self.value is None:
            return None
        return self.value.timestamp

    @property
    def price(self) -> float:
        if self.value is None:
            return None
        if self.price_type == PRICEINFO_TYPES.TICK:
            return self.value.price
        else:
            GLOG.logger.warn(
                f"The Price is Bar Type, but your are asking tick type price value."
            )
            return None

    @property
    def volume(self) -> int:
        if self.value is None:
            return None
        return self.value.volume

    @property
    def open(self) -> float:
        if self.value is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.value.open
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type open value."
            )
            return None

    @property
    def high(self) -> float:
        if self.value is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.value.high
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type high value."
            )
            return None

    @property
    def low(self) -> float:
        if self.value is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.value.low
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type low value."
            )
            return None

    @property
    def close(self) -> float:
        if self.value is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.value.close
        else:
            GLOG.logger.warn(
                f"The Price is Tick Type, but your are asking Bar type close value."
            )
            return None

    def to_dataframe(self):
        df = None
        # Tick
        if self.price_type == PRICEINFO_TYPES.TICK:
            # TODO
            pass
        # Bar
        elif self.price_type == PRICEINFO_TYPES.BAR:
            d = {
                "code": self.code,
                "timestamp": self.timestamp,
                "source": self.source,
                "open": self.open,
                "high": self.high,
                "low": self.low,
                "close": self.close,
                "volume": self.volume,
                "source": self.source,
            }
            df = pd.DataFrame.from_dict(d, orient="index").transpose()

        return df

    def __repr__(self):
        mem = f"      Mem: {hex(id(self))}"
        event_id = f"     UUID: {self.uuid}"
        source = f"   Source: {self.source} : {self.source.value}"
        date = f"     Date: {self.timestamp}"
        event_t = f"     Type: {self.event_type} : {self.event_type.value}"
        price_t = f"    Price: {self.price_type} : {self.price_type.value}"
        code = f"     Code: {self.code}"
        msg = [mem, event_id, source, date, event_t, price_t, code]

        if self.price_type == PRICEINFO_TYPES.BAR:
            open_ = f"     Open: {self.value.open}"
            high = f"     High: {self.value.high}"
            low = f"      Low: {self.value.low}"
            close = f"    Close: {self.value.close}"
            volume = f"   Volume: {self.value.volume}"
            msg.append(open_)
            msg.append(high)
            msg.append(low)
            msg.append(close)
            msg.append(volume)
        elif self.price_type == PRICEINFO_TYPES.TICK:
            price = f"    Price: {self.value.price}"
            volume = f"   Volume: {self.value.volume}"
            msg.append(price)
            msg.append(volume)

        return pretty_repr(EventPriceUpdate.__name__, msg, 54)
