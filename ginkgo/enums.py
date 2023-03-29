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


class TICKDIRECTION_TYPES(EnumBase):
    MINUSTICK = 1
    ZEROMINUSTICK = 2
    PLUSTICK = 3
    ZEROPLUSTICK = 4


class EVENT_TYPES(EnumBase):
    PRICEUPDATE = 1
    ORDERSUBMISSION = 2
    ORDERFILL = 3
    TRADEEXCUTION = 4
    POSITIONUPDATE = 5
    CAPTIALUPDATE = 6
    NEWSRECIEVE = 7


class PRICEINFO_TYPES(EnumBase):
    BAR = 1
    TICK = 2


class SOURCE_TYPES(EnumBase):
    SIM = 1
    REALTIME = 2
    SINA = 3
    BAOSTOCK = 4


class DIRECTION_TYPES(EnumBase):
    LONG = 1
    SHORT = -1


class ORDER_TYPES(EnumBase):
    MARKETORDER = 1
    LIMITORDER = 2


class ORDERSTATUS_TYPES(EnumBase):
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4


class FREQUENCY_TYPES(EnumBase):
    DAY = 1
    MIN5 = 2
