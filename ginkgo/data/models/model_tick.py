import pandas as pd
from functools import singledispatchmethod
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import datetime_normalize, base_repr
from ginkgo import GCONF
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
)
from sqlalchemy import Column, String, Integer, DECIMAL
from clickhouse_sqlalchemy import engines
from sqlalchemy_utils import ChoiceType


class MTick(MClickBase):
    __abstract__ = False
    __tablename__ = "tick"

    if GCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.MergeTree(order_by=("timestamp",)),)

    code = Column(String(), default="ginkgo_test_code")
    price = Column(DECIMAL(20, 10), default=0)
    volume = Column(Integer, default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MTick, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self, code: str, price: float, volume: int, time_stamp: str or datetime.datetime
    ) -> None:
        self.code = code
        self.price = round(price, 6)
        self.volume = volume
        self.timestamp = datetime_normalize(time_stamp)
        self.price = round(
            price,
        )

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.price = df.price
        self.volume = df.volume
        self.timestamp = datetime_normalize(df.timestamp)
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
