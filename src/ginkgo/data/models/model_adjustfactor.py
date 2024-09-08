import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.backtest.order import Order
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MAdjustfactor(MMysqlBase):
    __abstract__ = False
    __tablename__ = "adjustfactor"

    code = Column(String(40), default="ginkgo_test_code")
    foreadjustfactor = Column(DECIMAL(20, 10), default=0)
    backadjustfactor = Column(DECIMAL(20, 10), default=0)
    adjustfactor = Column(DECIMAL(20, 10), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MAdjustfactor, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        foreadjustfactor: float,
        backadjustfactor: float,
        adjustfactor: float,
        timestamp,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        self.foreadjustfactor = foreadjustfactor
        self.backadjustfactor = backadjustfactor
        self.adjustfactor = adjustfactor
        self.timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df.code
        self.foreadjustfactor = df.foreadjustfactor
        self.backadjustfactor = df.backadjustfactor
        self.adjustfactor = df.adjustfactor
        self.timestamp = df.timestamp
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
