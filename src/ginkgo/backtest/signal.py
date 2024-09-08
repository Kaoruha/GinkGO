import pandas as pd
import uuid
import datetime
from functools import singledispatchmethod
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.backtest.base import Base


class Signal(Base):
    """
    Signal Class.
    """

    def __init__(
        self,
        code: str = "Default Signal Code",
        direction: DIRECTION_TYPES = None,
        timestamp: any = None,
        engine_id: str = "",
        *args,
        **kwargs
    ) -> None:
        super(Signal, self).__init__(*args, **kwargs)
        self.set(code, direction, timestamp, engine_id)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        timestamp: any,
        engine_id: str = "",
    ):
        self._code: str = code
        self._direction: DIRECTION_TYPES = direction
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)
        self._engine_id = engine_id

    @set.register
    def _(self, df: pd.Series):
        """
        Set from dataframe
        """
        self._code: str = df.code
        self._timestamp: datetime.datetime = datetime_normalize(df.timestamp)
        self._engine_id = df.engine_id
        self._direction: DIRECTION_TYPES = DIRECTION_TYPES(df.direction)
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    @property
    def code(self) -> str:
        return self._code

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def backtest_id(self) -> str:
        return self._engine_id

    @property
    def portfolio_id(self) -> str:
        return self._engine_id

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @property
    def source(self) -> SOURCE_TYPES:
        return self._source

    def __repr__(self) -> str:
        return base_repr(self, Signal.__name__, 12, 60)
