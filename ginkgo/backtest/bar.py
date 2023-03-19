import datetime
from ginkgo.libs.ginkgo_pretty import pretty_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class Bar(object):
    def __init__(
        self,
        code: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        timestamp,
    ) -> None:
        self.__timestamp = None  # DateTime
        self.code = "sh.600001"
        self.open = 0
        self.high = 0
        self.low = 0
        self.close = 0
        self.volume = 0

        self.update(code, open_, high, low, close, volume, timestamp)

    def update(
        self,
        code: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        timestamp: datetime.datetime,
    ) -> None:
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

        self.__timestamp = datetime_normalize(timestamp)

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def open_(self) -> float:
        return self.open

    @property
    def chg(self) -> float:
        r = self.close - self.open
        r = round(r, 2)
        return r

    @property
    def amplitude(self) -> float:
        r = self.high - self.low
        r = round(r, 2)
        return r

    def __repr__(self) -> str:
        mem = f"MEM   : {hex(id(self))}"
        date = f"Date  : {self.timestamp}"
        open_ = f"Open  : {self.open}"
        high = f"High  : {self.high}"
        low = f"Low   : {self.low}"
        close = f"Close : {self.close}"
        volume = f"Volume: {self.volume}"
        msg = [mem, date, open_, high, low, close, volume]
        return pretty_repr(Bar.__name__, msg, 40)
