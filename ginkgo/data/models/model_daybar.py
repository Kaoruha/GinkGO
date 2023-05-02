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
)


class MDaybar(MBase):
    __abstract__ = False
    __tablename__ = "daybar"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(25), default="ginkgo_test_code")
    p_open = Column(DECIMAL(9, 2), default=0)
    p_high = Column(DECIMAL(9, 2), default=0)
    p_low = Column(DECIMAL(9, 2), default=0)
    p_close = Column(DECIMAL(9, 2), default=0)
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
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        datetime: str or datetime.datetime,
    ):
        self.code = code
        self.open = round(open, 2)
        self.high = round(high, 2)
        self.low = round(low, 2)
        self.close = round(close, 2)
        self.volume = volume
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.Series):
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

    def to_df(self) -> pd.Series:
        data = {
            "timestamp": self.timestamp,
            "code": self.code.strip(b"\x00".decode()),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "uuid": self.uuid.strip(b"\x00".decode()),
        }
        return pd.Series(data)

    def __repr__(self):
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
