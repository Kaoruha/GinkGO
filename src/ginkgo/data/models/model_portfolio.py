import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, DECIMAL, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .model_mysqlbase import MMysqlBase
from ...backtest.entities.order import Order
from ...enums import DIRECTION_TYPES, SOURCE_TYPES
from ...libs import base_repr, datetime_normalize


class MPortfolio(MMysqlBase):
    """
    Similar to backtest.
    """

    __abstract__ = False
    __tablename__ = "portfolio"

    name: Mapped[str] = mapped_column(String(64), default="default_live")
    backtest_start_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    backtest_end_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        name: str,
        backtest_start_date: Optional[any] = None,
        backtest_end_date: Optional[any] = None,
        is_live: Optional[bool] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs
    ) -> None:
        self.name = name
        if backtest_start_date is not None:
            self.backtest_start_date = datetime_normalize(backtest_start_date)
        if backtest_end_date is not None:
            self.backtest_end_date = datetime_normalize(backtest_end_date)
        if is_live is not None:
            self.is_live = is_live
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        # TODO
        self.name = df["name"]
        self.backtest_start_date = datetime_normalize(df["backtest_start_date"])
        self.backtest_end_date = datetime_normalize(df["backtest_end_date"])
        self.is_live = df["is_live"]
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
