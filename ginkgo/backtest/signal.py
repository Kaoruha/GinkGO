import pandas as pd
import datetime
from functools import singledispatchmethod
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.libs import gen_uuid4
from ginkgo.backtest.base import Base


class Signal(Base):
    def __init__(
        self,
        code: str = "Default Signal Code",
        direction: DIRECTION_TYPES = None,
        timestamp: str or datetime.datetime = None,
        uuid: str = "",
        *args,
        **kwargs
    ) -> None:
        super(Signal, self).__init__(*args, **kwargs)
        self.set(code, direction, timestamp, uuid)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        timestamp: str or datetime.datetime,
        uuid: str = "",
    ):
        self._code: str = code
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)
        self._direction: DIRECTION_TYPES = direction

        if len(uuid) > 0:
            self._uuid: str = uuid
        else:
            self._uuid = gen_uuid4()

    @set.register
    def _(self, df: pd.Series):
        """
        Set from dataframe
        """
        self._code: str = df.code
        self._timestamp: datetime.datetime = df.timestamp
        self._uuid: str = df.uuid
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
    def uuid(self) -> str:
        return self._uuid

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @property
    def source(self) -> SOURCE_TYPES:
        return self._source

    def __repr__(self) -> str:
        return base_repr(self, Order.__name__, 12, 60)