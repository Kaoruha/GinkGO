import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, BLOB
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MBacktest(MMysqlBase):
    __abstract__ = False
    __tablename__ = "backtest"

    backtest_id = Column(String(40), default="")
    start_at = Column(DateTime, default=datetime_normalize("1950-01-01"))
    finish_at = Column(DateTime, default=datetime_normalize("1950-01-01"))
    content = Column(BLOB)
    profit = Column(DECIMAL(20, 8), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MBacktest, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        backtest_id: str,
        start_at: any,
        content: any,
        finish_at: any = None,
    ) -> None:
        self.backtest_id = backtest_id
        self.start_at = datetime_normalize(start_at)
        self.content = content
        self.profit = 0
        self.finish_at = (
            datetime_normalize(finish_at)
            if finish_at
            else datetime_normalize("1950-01-01")
        )

    def update_profit(self, profit: float) -> None:
        self.profit = round(profit, 6)

    def finish(self, finish_at: any) -> None:
        self.finish_at = datetime_normalize(finish_at)
        self.update = datetime_normalize(finish_at)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
