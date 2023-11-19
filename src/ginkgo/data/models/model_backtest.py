import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MBacktest(MClickBase):
    __abstract__ = False
    __tablename__ = "backtest"

    backtest_id = Column(String(), default="")
    start_at = Column(DateTime, default=datetime_normalize("1950-01-01"))
    finish_at = Column(DateTime, default=datetime_normalize("1950-01-01"))

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
        finish_at: any = None,
    ) -> None:
        self.backtest_id = backtest_id
        self.start_at = datetime_normalize(start_at)
        self.finish_at = (
            datetime_normalize(finish_at)
            if finish_at
            else datetime_normalize("1950-01-01")
        )

    @set.register
    def _(self, df: pd.Series) -> None:
        pass

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
