import datetime


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
    ):
        self.timestamp = None  # DateTime
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
    ):
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

        if isinstance(timestamp, datetime.datetime):
            self.timestamp = timestamp
        elif isinstance(timestamp, str):
            t = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            self.timestamp = t

    @property
    def open_(self):
        return self.open

    @property
    def chg(self):
        r = self.close - self.open
        r = round(r, 2)
        return r

    @property
    def amplitude(self):
        r = self.high - self.low
        r = round(r, 2)
        return r

    def __repr__(self):
        bar = f"MEM   : {hex(id(self))}"
        date = f"Date  : {self.timestamp}"
        open_ = f"Open  : {self.open}"
        high = f"High  : {self.high}"
        low = f"Low   : {self.low}"
        close = f"Close : {self.close}"
        volume = f"Volume: {self.volume}"
        txt = [bar, date, open_, high, low, close, volume]
        width = 40
        title = "=" * (width // 2 - 3) + " BAR "
        title += "=" * (width - len(title))
        r = "\n"
        r += title
        for i in range(7):
            t = txt[i]
            r += "\n"
            r += t
            r += " " * (width - len(t) - 1)
            r += "#"
        r += "\n"
        r += "=" * width
        return r
