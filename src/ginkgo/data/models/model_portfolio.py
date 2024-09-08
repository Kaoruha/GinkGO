import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, BLOB

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MPortfolio(MMysqlBase):
    """
    Similar to backtest.
    """

    __abstract__ = False
    __tablename__ = "portfolio"

    name = Column(String(40), default="default_live")

    def __init__(self, *args, **kwargs) -> None:
        super(MLivePortfolio, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(self, name: str, *args, **kwargs) -> None:
        self.name = name

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
