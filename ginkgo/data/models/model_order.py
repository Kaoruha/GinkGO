import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_base import MBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MOrder(MBase):
    __abstract__ = False
    __tablename__ = "order"

    if GCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.ReplacingMergeTree(order_by=("timestamp",)),)

    code = Column(String(), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    type = Column(ChoiceType(ORDER_TYPES, impl=Integer()), default=1)
    status = Column(ChoiceType(ORDERSTATUS_TYPES, impl=Integer()), default=1)
    volume = Column(Integer, default=0)
    limit_price = Column(DECIMAL(20, 10), default=0)
    frozen = Column(DECIMAL(20, 10), default=0)
    transaction_price = Column(DECIMAL(20, 10), default=0)
    remain = Column(DECIMAL(20, 10), default=0)
    fee = Column(DECIMAL(20, 10), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MOrder, self).__init__(*args, **kwargs)

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
        frozen: float,
        transaction_price: float,
        remain: float,
        fee: float,
        timestamp: any,
        uuid: str,
    ) -> None:
        self.uuid = uuid
        self.code = code
        self.direction = direction
        self.type = type
        self.status = status
        self.volume = volume
        self.limit_price = round(limit_price, 6)
        self.frozen = frozen
        self.transaction_price = transaction_price
        self.remain = remain
        self.fee = fee
        self.timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.direction = df.direction
        self.type = df.type
        self.status = df.status
        self.volume = df.volume
        self.limit_price = df.limit_price
        self.limit_price = round(df.limit_price, 6)
        self.frozen = df.frozen
        self.transaction_price = df.transaction_price
        self.remain = df.remain
        self.fee = df.fee
        self.timestamp = df.timestamp
        self.uuid = df.uuid
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
