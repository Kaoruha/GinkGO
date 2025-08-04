import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column

from .model_mysqlbase import MMysqlBase
from ...enums import SOURCE_TYPES, ENGINESTATUS_TYPES
from ...libs import base_repr


class MEngine(MMysqlBase):
    __abstract__ = False
    __tablename__ = "engine"

    name: Mapped[str] = mapped_column(String(64), default="ginkgo_test_engine")
    status: Mapped[ENGINESTATUS_TYPES] = mapped_column(Enum(ENGINESTATUS_TYPES), default=ENGINESTATUS_TYPES.IDLE)
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
            self.status = status
        if is_live is not None:
            self.is_live = is_live
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.name = df["name"]
        self.status = df["status"]
        self.is_live = df["is_live"]
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
