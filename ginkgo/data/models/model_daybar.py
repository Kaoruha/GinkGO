import datetime
import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL
from ginkgo.data.models.model_base import MBase
from ginkgo.backtest.bar import Bar
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    FREQUENCY_TYPES,
    SOURCE_TYPES,
)


class MDaybar(MBase):
    __abstract__ = False
    __tablename__ = "daybar"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(), default="ginkgo_test_code")
    open = Column(DECIMAL(9, 6), default=0)
    high = Column(DECIMAL(9, 6), default=0)
    low = Column(DECIMAL(9, 6), default=0)
    close = Column(DECIMAL(9, 6), default=0)
    volume = Column(Integer, default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MDaybar, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        datetime: str or datetime.datetime,
    ) -> None:
        self.code = code
        self.open = round(open, 6)
        self.high = round(high, 6)
        self.low = round(low, 6)
        self.close = round(close, 6)
        self.volume = volume
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.Series) -> None:
        if df.frequency != FREQUENCY_TYPES.DAY.value:
            gl.logger.warn(f"The bar is not daybar, your data might be wrong.")
            return
        self.code = df.code
        self.open = df.open
        self.high = df.high
        self.low = df.low
        self.close = df.close
        self.volume = df.volume
        self.timestamp = df.timestamp
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
