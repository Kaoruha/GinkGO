import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, BLOB
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MLivePortfolio(MMysqlBase):
    """
    Similar to backtest.
    """

    __abstract__ = False
    __tablename__ = "live_portfolio"

    engine_id = Column(String(40), default="")
    name = Column(String(40), default="default_live")
    start_at = Column(DateTime, default=datetime_normalize("1950-01-01"))
    content = Column(BLOB)
    profit = Column(DECIMAL(20, 8), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MLivePortfolio, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        name: str,
        engine_id: str,
        start_at: any,
        content: any,
    ) -> None:
        self.name = name
        self.engine_id = engine_id
        self.uuid = engine_id
        self.start_at = datetime_normalize(start_at)
        self.content = content
        self.profit = 0

    def update_profit(self, profit: float) -> None:
        self.profit = round(profit, 6)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
