import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MOrderRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "order_record"

    code = Column(String(40), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    type = Column(ChoiceType(ORDER_TYPES, impl=Integer()), default=1)
    volume = Column(Integer, default=0)
    transaction_price = Column(DECIMAL(20, 10), default=0)
    remain = Column(DECIMAL(20, 10), default=0)
    fee = Column(DECIMAL(20, 10), default=0)
    portfolio_id = Column(String(40), default="")

    def __init__(self, *args, **kwargs) -> None:
        super(MOrderRecord, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        portfolio_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        type: ORDER_TYPES,
        volume: int,
        transaction_price: float,
        remain: float,
        fee: float,
        timestamp: any,
        *args,
        **kwargs,
    ) -> None:
        self.code = str(code)
        self.direction = direction
        self.type = type
        self.volume = int(volume)
        self.transaction_price = float(transaction_price)
        self.remain = float(remain)
        self.fee = float(fee)
        self.timestamp = datetime_normalize(timestamp)
        self.portfolio_id = str(portfolio_id)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
