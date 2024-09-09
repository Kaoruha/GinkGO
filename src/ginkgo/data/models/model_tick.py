import pandas as pd
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from functools import singledispatchmethod
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import datetime_normalize, base_repr
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class MTick(MClickBase):
    __abstract__ = True
    __tablename__ = "tick"

    code = Column(String(), default="ginkgo_test_code")
    price = Column(DECIMAL(20, 10), default=0)
    volume = Column(Integer, default=0)
    direction = Column(ChoiceType(TICKDIRECTION_TYPES, impl=Integer()), default=1)

    def __init__(self, *args, **kwargs) -> None:
        super(MTick, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        price: float,
        volume: int,
        direction: TICKDIRECTION_TYPES,
        timestamp: any,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        self.price = round(price, 6)
        self.volume = volume
        self.direction = direction
        self.timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df.code
        self.price = df.price
        self.volume = df.volume
        self.direction = df.direction
        self.timestamp = datetime_normalize(df.timestamp)
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
