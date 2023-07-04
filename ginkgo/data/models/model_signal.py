import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_base import MBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class MSignal(MBase):
    __abstract__ = False
    __tablename__ = "signal"

    if GCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.MergeTree(order_by=("timestamp",)),)

    code = Column(String(), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)

    def __init__(self, *args, **kwargs) -> None:
        super(MSignal, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        datetime: str or datetime.datetime,
    ) -> None:
        self.code = code
        self.direction = direction
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.direction = df.direction
        self.timestamp = df.timestamp
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
