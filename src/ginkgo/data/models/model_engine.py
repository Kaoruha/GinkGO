import datetime
import pandas as pd

from functools import singledispatchmethod
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import base_repr


class MEngine(MMysqlBase):
    __abstract__ = False
    __tablename__ = "engine"

    name: Mapped[str] = mapped_column(String(32), default="ginkgo_test_engine")
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        name: str,
        is_live: bool = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        if is_live is not None:
            self.is_live = is_live
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        self.name = df["name"]
        self.is_live = df["is_live"]
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
