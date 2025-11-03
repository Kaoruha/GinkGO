import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import base_repr


class MHandler(MMysqlBase, ModelConversion):
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
        lib_path: Optional[str] = None,
        func_name: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        if lib_path is not None:
            self.lib_path = lib_path
        if func_name is not None:
            self.func_name = func_name
        if source is not None:
            self.set_source(source)
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MHandler实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理source字段的枚举转换
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
            # 从kwargs中移除source，避免重复赋值
            del kwargs['source']
        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
