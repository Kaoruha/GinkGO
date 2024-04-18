import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import base_repr, datetime_normalize


class MPosition(MClickBase):
    __abstract__ = False
    __tablename__ = "position"

    code = Column(String(), default="ginkgo_test_code")
    backtest_id = Column(String(), default="")
    volume = Column(Integer, default=0)
    cost = Column(DECIMAL(20, 10), default=0)
    reason = Column(String(), default="")

    def __init__(self, *args, **kwargs) -> None:
        super(MPosition, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        backtest_id: str,
        datetime: any,
        code: str,
        volume: int,
        cost: float,
    ) -> None:
        self.backtest_id = backtest_id
        self.timestamp = datetime_normalize(datetime)
        self.code = code
        self.volume = int(volume)
        self.cost = float(cost)

    @set.register
    def _(self, df: pd.Series) -> None:
        pass

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
