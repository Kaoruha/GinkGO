import uuid
import pandas as pd
import datetime

from types import FunctionType, MethodType
from typing import Optional
from sqlalchemy import Enum, String, DateTime, Boolean
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .model_base import MBase
from ...libs import datetime_normalize
from ...libs.utils.display import base_repr
from ...enums import SOURCE_TYPES


class Base(DeclarativeBase):
    pass


class MMysqlBase(Base, MBase):
    __abstract__ = True
    __tablename__ = "MysqlBaseModel"

    uuid: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    meta: Mapped[Optional[str]] = mapped_column(String(255), default="{}")
    desc: Mapped[Optional[str]] = mapped_column(String(255), default="This man is lazy, there is no description.")
    create_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now)
    update_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now)
    is_del: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[int] = mapped_column(TINYINT, default=-1)

    def get_source_enum(self):
        """Convert database source integer back to enum for business layer"""
        return SOURCE_TYPES.from_int(self.source)

    def update(self) -> None:
        raise NotImplementedError("Model Class need to overload Function update to transit data.")

    def set_source(self, source, *args, **kwargs) -> None:
        """Set source with enum/int dual input support"""
        self.source = SOURCE_TYPES.validate_input(source) or -1

    def delete(self, *args, **kwargs) -> None:
        self.is_del = True

    def cancel_delete(self, *args, **kwargs) -> None:
        self.is_del = False

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 80)
