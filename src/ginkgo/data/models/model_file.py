import pandas as pd
import datetime

from functools import singledispatchmethod
from sqlalchemy import String, Enum, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MFile(MMysqlBase):
    __abstract__ = False
    __tablename__ = "file"

    type: Mapped[FILE_TYPES] = mapped_column(Enum(FILE_TYPES), default=FILE_TYPES.OTHER)
    name: Mapped[str] = mapped_column(String(40), default="ginkgo_file")
    data: Mapped[bytes] = mapped_column(LargeBinary, default=b"")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type --> {args}")

    @update.register(str)
    def _(
        self,
        name: str,
        type: FILE_TYPES = None,
        data: bytes = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        if type is not None:
            self.type = type
        if data is not None:
            self.data = data
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        # TODO
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
