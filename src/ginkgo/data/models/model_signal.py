import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
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
    backtest_id = Column(String(), default="")
    strategy_id = Column(String(), default="")
    strategy_name = Column(String(), default="")

    def __init__(self, *args, **kwargs) -> None:
        super(MSignal, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        backtest_id: str,
        strategy_id: str,
        strategy_name: str,
        datetime: any,
    ) -> None:
        self.code = code
        self.direction = direction
        self.backtest_id = backtest_id
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.Series) -> None:
        pass

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
