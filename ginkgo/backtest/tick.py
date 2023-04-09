import datetime
import pandas as pd
from functools import singledispatchmethod
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class Tick(object):
    def __init__(
        self,
        code: str,
        price: float,
        volume: int,
        timestamp: str or datetime.datetime,
    ) -> None:
        self.__timestamp = None  # DateTime
        self.code = "sh.600001"
        self.price = 0
        self.volume = 0

        self.set(code, price, volume, timestamp)

    @property
    def timestamp(self) -> datetime.datetime:
        return self.__timestamp

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(self, code: str, price: float, volume: int, timestamp) -> None:
        self.code = code
        self.price = price
        self.volume = volume
        self.__timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, tick: pd.DataFrame):
        # TODO read data from model tick
        pass

    def __repr__(self) -> str:
        return base_repr(self, "DB" + Tick.__name__.capitalize(), 12, 46)
