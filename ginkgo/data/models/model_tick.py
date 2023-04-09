import pandas as pd
from functools import singledispatchmethod
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.data.models.model_base import MBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from sqlalchemy import Column, String, Integer, DECIMAL
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from clickhouse_sqlalchemy import engines
from sqlalchemy_utils import ChoiceType
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class MTick(MBase):
    __abstract__ = False
    __tablename__ = "tick"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(25), default="ginkgo_test_code")
    price = Column(DECIMAL(9, 2), default=0)
    volume = Column(Integer, default=0)

    def __init__(self):
        super().__init__()

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        source: SOURCE_TYPES,
        price: float,
        volume: int,
        datetime,
    ):
        self.code = code
        self.source = source
        self.price = price
        self.volume = volume
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.DataFrame):
        pass

    def __repr__(self):
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
