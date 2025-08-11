import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Enum, Boolean
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from .model_mysqlbase import MMysqlBase
from ...libs import base_repr, datetime_normalize
from ...enums import SOURCE_TYPES, FILE_TYPES


class MPortfolioFileMapping(MMysqlBase):
    __abstract__ = False
    __tablename__ = "portfolio_file_mapping"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="ginkgo_portfolio")
    file_id: Mapped[str] = mapped_column(String(32), default="ginkgo_file")
    name: Mapped[str] = mapped_column(String(64), default="ginkgo_bind")
    type: Mapped[int] = mapped_column(TINYINT, default=-1)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        pass

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        file_id: Optional[str] = None,
        name: Optional[str] = None,
        type: Optional[FILE_TYPES] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        if name is not None:
            self.name = str(name)
        if type is not None:
            self.type = FILE_TYPES.validate_input(type) or -1
        if file_id is not None:
            self.file_id = str(file_id)
        if type is not None:
            self.type = FILE_TYPES.validate_input(type) or -1
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.file_id = df["file_id"]
        self.type = FILE_TYPES.validate_input(df["type"]) or -1
        self.name = df["name"]
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df.source) or -1
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
