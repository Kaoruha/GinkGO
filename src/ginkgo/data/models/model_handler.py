import datetime

from functools import singledispatchmethod
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import base_repr


class MHandler(MMysqlBase):
    __abstract__ = False
    __tablename__ = "handler"

    name: Mapped[str] = mapped_column(String(32), default="test_handler")
    lib_path: Mapped[str] = mapped_column(String(255), default="")
    func_name: Mapped[str] = mapped_column(String(255), default="")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        name: str,
        lib_path:str=None,
        func_name:str=None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        if lib_path is not None:
            self.lib_path = lib_path
        if func_name is not None:
            self.func_name = func_name
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)

