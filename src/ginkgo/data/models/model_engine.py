import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from .model_mysqlbase import MMysqlBase
from ...enums import SOURCE_TYPES, ENGINESTATUS_TYPES
from ...libs import base_repr


class MEngine(MMysqlBase):
    __abstract__ = False
    __tablename__ = "engine"

    name: Mapped[str] = mapped_column(String(64), default="ginkgo_test_engine")
    status: Mapped[int] = mapped_column(TINYINT, default=-1)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        name: str,
        status: Optional[ENGINESTATUS_TYPES] = None,
        is_live: Optional[bool] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        if status is not None:
            self.status = ENGINESTATUS_TYPES.validate_input(status) or -1
        if is_live is not None:
            self.is_live = is_live
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.name = df["name"]
        self.status = ENGINESTATUS_TYPES.validate_input(df["status"]) or -1
        self.is_live = df["is_live"]
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
