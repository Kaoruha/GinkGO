import datetime
import pandas as pd
from functools import singledispatchmethod
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.backtest.base import Base


class Tick(Base):
    def __init__(
        self,
        code: str = "ginkgo_test_tick_code",
        price: float = 0,
        volume: int = 0,
        timestamp: str or datetime.datetime = None,
    ) -> None:
        self.set(code, price, volume, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(self, code: str, price: float, volume: int, timestamp) -> None:
        self._code = code
        self._price = price
        self._volume = volume
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, tick: pd.Series):
        self._code = tick.code
        self._price = tick.price
        self._volume = tick.volume
        self._timestamp = tick.timestamp

    @property
    def code(self) -> str:
        return self._code

    @property
    def price(self) -> float:
        return self._price

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def __repr__(self) -> str:
        return base_repr(self, "DB" + Tick.__name__.capitalize(), 12, 46)
