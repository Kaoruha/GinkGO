import datetime
import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.backtest.bar import Bar
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    FREQUENCY_TYPES,
    SOURCE_TYPES,
)


class MBar(MClickBase):
    __abstract__ = False
    __tablename__ = "bar"

    code = Column(String(), default="ginkgo_test_code")
    open = Column(DECIMAL(20, 10), default=0)
    high = Column(DECIMAL(20, 10), default=0)
    low = Column(DECIMAL(20, 10), default=0)
    close = Column(DECIMAL(20, 10), default=0)
    volume = Column(Integer, default=0)
    frequency = Column(ChoiceType(FREQUENCY_TYPES, impl=Integer()), default=1)

    def __init__(self, *args, **kwargs) -> None:
        super(MBar, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        """
        code: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        frequency: FREQUENCY_TYPES,
        datetime: any,
        """
        pass

    @set.register
    def _(
        self,
        code: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        frequency: FREQUENCY_TYPES,
        datetime: any,
    ) -> None:
        self.code = code
        self.open = round(open, 6)
        self.high = round(high, 6)
        self.low = round(low, 6)
        self.close = round(close, 6)
        self.volume = volume
        self.frequency = frequency
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.open = df.open
        self.high = df.high
        self.low = df.low
        self.close = df.close
        self.volume = df.volume
        self.timestamp = df.timestamp
        self.frequency = df.frequency
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
