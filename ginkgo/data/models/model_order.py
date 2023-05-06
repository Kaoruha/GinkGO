import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_base import MBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class MOrder(MBase):
    __abstract__ = False
    __tablename__ = "order"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(50), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    type = Column(ChoiceType(ORDER_TYPES, impl=Integer()), default=1)
    status = Column(ChoiceType(ORDERSTATUS_TYPES, impl=Integer()), default=1)
    volume = Column(Integer, default=0)
    limit_price = Column(DECIMAL(9, 2), default=0)

    def __init__(self):
        super().__init__()

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        type: ORDER_TYPES,
        status: ORDERSTATUS_TYPES,
        volume: int,
        limit_price: float,
        datetime,
    ):
        self.code = code
        self.direction = direction
        self.type = type
        self.status = status
        self.volume = volume
        self.limit_price = limit_price
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.direction = df.direction
        self.type = df.type
        self.status = df.status
        self.volume = df.volume
        self.limit_price = df.limit_price
        self.timestamp = df.timestamp

    def __repr__(self):
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)