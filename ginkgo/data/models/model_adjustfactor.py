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


class MAdjustfactor(MBase):
    __abstract__ = False
    __tablename__ = "adjustfactor"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    # code dividOperateDate foreAdjustFactor backAdjustFactor adjustFactor
    code = Column(String(), default="ginkgo_test_code")
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
        date,
    ) -> None:
        self.code = code
        self.foreadjustfactor = foreadjustfactor
        self.backadjustfactor = backadjustfactor
        self.adjustfactor = adjustfactor
        self.timestamp = datetime_normalize(date)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.foreadjustfactor = df.foreadjustfactor
        self.backadjustfactor = df.backadjustfactor
        self.adjustfactor = adjustfactor
        self.timestamp = df.timestamp
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
