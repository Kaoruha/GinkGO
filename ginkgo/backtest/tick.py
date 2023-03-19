import datetime
from ginkgo.libs.ginkgo_pretty import pretty_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class Tick(object):
    def __init__(
        self,
        code: str,
        price: float,
        volume: int,
        timestamp,
    ) -> None:
        self.__timestamp = None  # DateTime
        self.code = "sh.600001"
        self.price = 0
        self.volume = 0

        self.update(code, price, volume, timestamp)

    @property
    def timestamp(self):
        return self.__timestamp

    def update(self, code: str, price: float, volume: int, timestamp) -> None:
        self.code = code
        self.price = price
        self.volume = volume
        self.__timestamp = datetime_normalize(timestamp)

    def __repr__(self) -> str:
        mem = f"MEM   : {hex(id(self))}"
        date = f"Date  : {self.timestamp}"
        price = f"Price : {self.price}"
        volume = f"Volume: {self.volume}"
        msg = [mem, date, price, volume]

        return pretty_repr(Tick.__name__, msg, 40)
