import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES


class MPortfolioHandlerMapping(MMysqlBase):
    __abstract__ = False
    __tablename__ = "portfolio_handler_mapping"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="ginkgo_portfolio")
    handler_id: Mapped[str] = mapped_column(String(32), default="ginkgo_file")
    type: Mapped[EVENT_TYPES] = mapped_column(Enum(EVENT_TYPES), default=EVENT_TYPES.OTHER)
    name: Mapped[str] = mapped_column(String(32), default="ginkgo_bind")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        pass

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        handler_id: Optional[str] = None,
        type: Optional[EVENT_TYPES] = None,
        name: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        if name is not None:
            self.name = str(name)
        if handler_id is not None:
            self.handler_id = str(handler_id)
        if type is not None:
            self.type = type
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.handler_id = df["handler_id"]
        self.type = df["type"]
        self.name = df["name"]
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
