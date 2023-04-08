import datetime
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_base import MBase
from ginkgo.backtest.bar import Bar
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
)


class MDaybar(MBase):
    __abstract__ = False
    __tablename__ = "daybar"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(25), default="ginkgo_test_code")
    source = Column(ChoiceType(SOURCE_TYPES, impl=Integer()), default=1)
    p_open = Column(DECIMAL(9, 2), default=0)
    p_high = Column(DECIMAL(9, 2), default=0)
    p_low = Column(DECIMAL(9, 2), default=0)
    p_close = Column(DECIMAL(9, 2), default=0)
    volume = Column(Integer, default=0)

    def __init__(self):
        super().__init__()

    @singledispatchmethod
    def set(self):
        pass

    @set.register
    def _(
        self,
        code: str,
        source: SOURCE_TYPES,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        datetime,
    ):
        self.code = code
        self.source = source
        self.p_open = round(open_, 2)
        self.p_high = round(high, 2)
        self.p_low = round(low, 2)
        self.p_close = round(close, 2)
        self.volume = volume
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, bar: Bar, source: SOURCE_TYPES):
        if bar.frequency != FREQUENCY_TYPES.DAY:
            gl.logger.warn(f"The bar is not daybar, your data might be wrong.")
            return

        self.code = bar.code
        self.p_open = bar.open
        self.p_high = bar.high
        self.p_low = bar.low
        self.p_close = bar.close
        self.volume = bar.volume
        self.timestamp = bar.timestamp
        self.source = source

    def __repr__(self):
        return base_repr(self, "DB"+self.__tablename__.capitalize(), 12, 46)
