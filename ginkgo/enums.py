from enum import Enum, IntEnum


class EnumBase(Enum):
    @classmethod
    def enum_convert(cls, string):
        r = None
        try:
            r = cls[string.upper()]
        except Exception as e:
            print(e)
        return r

    # def __repr__(self):
    #     return self.value


class TickDirection(EnumBase):
    MINUSTICK = 1
    ZEROMINUSTICK = 2
    PLUSTICK = 3
    ZEROPLUSTICK = 4


class EventType(EnumBase):
    PRICEUPDATE = 1
    ORDERSUBMISSION = 2
    ORDERFILL = 3
    TRADEEXCUTION = 4
    POSITIONUPDATE = 5
    CAPTIALUPDATE = 6
    NEWSRECIEVE = 7


class PriceInfo(EnumBase):
    BAR = 1
    TICK = 2


class Source(EnumBase):
    SIM = 1
    REALTIME = 2
    SINA = 3
    BAOSTOCK = 4


class Direction(EnumBase):
    LONG = 1
    SHORT = 2


class OrderType(EnumBase):
    MARKETORDER = 1
    LIMITORDER = 2


class OrderStatus(EnumBase):
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4
