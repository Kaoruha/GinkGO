import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column

from .model_mysqlbase import MMysqlBase
from ...enums import SOURCE_TYPES, EVENT_TYPES
from ...libs import base_repr


class MEngineHandlerMapping(MMysqlBase):
    __abstract__ = False
    __tablename__ = "engine_handler_mapping"

    engine_id: Mapped[str] = mapped_column(String(32), default="")
    handler_id: Mapped[str] = mapped_column(String(32), default="")
    type: Mapped[EVENT_TYPES] = mapped_column(Enum(EVENT_TYPES), default=EVENT_TYPES.OTHER)
    name: Mapped[str] = mapped_column(String(32), default="ginkgo_bind")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        engine_id: str,
        handler_id: Optional[str] = None,
        type: Optional[EVENT_TYPES] = None,
        name: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.engine_id = engine_id
        if handler_id is not None:
            self.handler_id = handler_id
        if type is not None:
            self.type = type
        if name is not None:
            self.name = name
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.engine_id = df["engine_id"]
        self.handler_id = df["handler_id"]
        self.name = df["name"]
        self.type = df["type"]
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
