import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy_utils import ChoiceType
from sqlalchemy import Column, String, Integer, DECIMAL
from ginkgo.data.models.model_base import MBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class MOrder(MBase):
    __abstract__ = False
    __tablename__ = "order"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(25), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    order_type = Column(ChoiceType(ORDER_TYPES, impl=Integer()), default=1)
    status = Column(ChoiceType(ORDERSTATUS_TYPES, impl=Integer()), default=1)
    source = Column(ChoiceType(SOURCE_TYPES, impl=Integer()), default=1)
    volume = Column(Integer, default=0)
    limit_price = Column(DECIMAL(9, 2), default=0)

    def __init__(self):
        super().__init__()

    @singledispatchmethod
    def set(self):
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        order_type: ORDER_TYPES,
        status: ORDERSTATUS_TYPES,
        source: SOURCE_TYPES,
        volume: int,
        limit_price: float,
        datetime,
    ):
        self.code = code
        self.direction = direction
        self.order_type = order_type
        self.status = status
        self.source = source
        self.volume = volume
        self.limit_price = limit_price
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, order: pd.DataFrame, source: SOURCE_TYPES) -> None:
        self.code = order.code
        self.direction = order.direction
        self.order_type = order.order_type
        self.status = order.status
        self.source = source
        self.volume = order.volume
        self.limit_price = order.limit_price
        self.timestamp = order.timestamp

    def __repr__(self):
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
