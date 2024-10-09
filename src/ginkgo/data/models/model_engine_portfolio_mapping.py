import datetime
import pandas as pd

from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import base_repr


class MEnginePortfolioMapping(MMysqlBase):
    __abstract__ = False
    __tablename__ = "engine_portfolio_mapping"

    engine_id: Mapped[str] = mapped_column(String(32), default="")
    portfolio_id: Mapped[str] = mapped_column(String(32), default="")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        engine_id: str,
        portfolio_id: str = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.engine_id = engine_id
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.engine_id = df["engine_id"]
        self.portfolio_id = df["portfolio_id"]
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
