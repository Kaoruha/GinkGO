import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs import base_repr, datetime_normalize


class MPositionLive(MMysqlBase):
    __abstract__ = False
    __tablename__ = "position_live"

    code = Column(String(40), default="ginkgo_test_code")
    portfolio_id = Column(String(40), default="")
    volume = Column(Integer, default=0)
    cost = Column(DECIMAL(20, 10), default=0)
    price = Column(DECIMAL(20, 10), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MPositionLive, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        portfolio_id: str,
        datetime: any,
        code: str,
        price: float,
        cost: float,
        volume: int,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.timestamp = datetime_normalize(datetime)
        self.code = code
        self.volume = int(volume)
        self.cost = float(cost)
        self.price = float(price)

    @set.register
    def _(self, df: pd.Series) -> None:
        pass

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
