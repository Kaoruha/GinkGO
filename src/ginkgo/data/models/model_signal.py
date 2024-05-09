import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MSignal(MClickBase):
    __abstract__ = False
    __tablename__ = "signal"

    code = Column(String(), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    portfolio_id = Column(String(), default="")
    reason = Column(String(), default="")

    def __init__(self, *args, **kwargs) -> None:
        super(MSignal, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        portfolio_id: str,
        datetime: any,
        code: str,
        direction: DIRECTION_TYPES,
        reason: str,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.timestamp = datetime_normalize(datetime)
        self.code = code
        self.direction = direction
        self.reason = reason

    @set.register
    def _(self, df: pd.Series) -> None:
        pass

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
