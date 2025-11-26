import datetime
import pandas as pd
from functools import singledispatchmethod
from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES, PRICEINFO_TYPES, SOURCE_TYPES
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick
from ginkgo.libs import pretty_repr
from ginkgo.libs.utils.display import base_repr


class EventPriceUpdate(EventBase):
    """
    PriceUpdate Only after new price info comes.
    """

    def __init__(self, payload: Bar or Tick = None, *args, **kwargs) -> None:
        super(EventPriceUpdate, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.PRICEUPDATE)
        self._price_type = None

        if payload:
            self.set(payload)

    @property
    def price_type(self):
        return self._price_type


    @property
    def payload(self):
        """获取事件载荷数据"""
        if self._price_type == PRICEINFO_TYPES.BAR:
            return self._bar
        elif self._price_type == PRICEINFO_TYPES.TICK:
            return self._tick
        else:
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
        if self.payload is None:
            return None
        return self.payload.code

    @property
    def timestamp(self) -> datetime.datetime:
        """
        事件时间戳 - 始终返回事件创建时间
        """
        return super().timestamp

    @property
    def business_timestamp(self) -> datetime.datetime:
        """
        业务数据时间戳 - 返回价格数据的时间，如果没有价格数据则返回事件时间
        """
        if self.payload is None:
            return self.timestamp
        return self.payload.timestamp

    @property
    def price(self) -> float:
        if self.payload is None:
            return None
        if self.price_type == PRICEINFO_TYPES.TICK:
            return self.payload.price
        else:
            self.log("WARN", f"The Price is Bar Type, but your are asking tick type price value.")
            return None

    @property
    def volume(self) -> int:
        if self.payload is None:
            return None
        return self.payload.volume

    @property
    def open(self) -> float:
        if self.payload is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.payload.open
        else:
            self.log("WARN", f"The Price is Tick Type, but your are asking Bar type open value.")
            return None

    @property
    def high(self) -> float:
        if self.payload is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.payload.high
        else:
            self.log("WARN", f"The Price is Tick Type, but your are asking Bar type high value.")
            return None

    @property
    def low(self) -> float:
        if self.payload is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.payload.low
        else:
            self.log("DEBUG", f"The Price is Tick Type, but your are asking Bar type low value.")
            return None

    @property
    def close(self) -> float:
        if self.payload is None:
            return None
        if self.price_type == PRICEINFO_TYPES.BAR:
            return self.payload.close
        else:
            self.log("DEBUG", f"The Price is Tick Type, but your are asking Bar type close value.")
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
        return base_repr(self, EventPriceUpdate.__name__, 16, 60)
