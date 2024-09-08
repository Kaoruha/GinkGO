import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MOrder(MMysqlBase):
    __abstract__ = False
    __tablename__ = "order"

    code = Column(String(40), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    type = Column(ChoiceType(ORDER_TYPES, impl=Integer()), default=1)
    status = Column(ChoiceType(ORDERSTATUS_TYPES, impl=Integer()), default=1)
    volume = Column(Integer, default=0)
    limit_price = Column(DECIMAL(20, 10), default=0)
    frozen = Column(DECIMAL(20, 10), default=0)
    transaction_price = Column(DECIMAL(20, 10), default=0)
    remain = Column(DECIMAL(20, 10), default=0)
    fee = Column(DECIMAL(20, 10), default=0)
    backtest_id = Column(String(40), default="")

    def __init__(self, *args, **kwargs) -> None:
        super(MOrder, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        uuid: str,
        code: str,
        direction: DIRECTION_TYPES,
        type: ORDER_TYPES,
        status: ORDERSTATUS_TYPES,
        volume: int,
        limit_price: float,
        frozen: float,
        transaction_price: float,
        remain: float,
        fee: float,
        timestamp: any,
        backtest_id: str,
        *args,
        **kwargs,
    ) -> None:
        self.uuid = uuid
        self.code = code
        self.direction = direction
        self.type = type
        self.status = status
        self.volume = volume
        self.limit_price = round(limit_price, 6)
        self.frozen = frozen
        self.transaction_price = round(transaction_price, 6)
        self.remain = remain
        self.fee = fee
        self.timestamp = datetime_normalize(timestamp)
        self.backtest_id = backtest_id

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df.code
        self.direction = df.direction
        self.type = df.type
        self.status = df.status
        self.volume = df.volume
        self.limit_price = df.limit_price
        self.limit_price = round(df.limit_price, 6)
        self.frozen = df.frozen
        self.transaction_price = round(df.transaction_price, 6)
        self.remain = df.remain
        self.fee = df.fee
        self.timestamp = df.timestamp
        self.uuid = df.uuid
        self.backtest_id = df.backtest_id
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
