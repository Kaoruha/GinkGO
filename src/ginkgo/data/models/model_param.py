import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import base_repr


class MParam(MMysqlBase):
    __abstract__ = False
    __tablename__ = "params"

    mapping_id: Mapped[str] = mapped_column(String(32), default="")
    index: Mapped[int] = mapped_column(Integer, default=0)
    value: Mapped[str] = mapped_column(String(255), default="")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        mapping_id: str,
        index: Optional[int] = None,
        value: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.mapping_id = mapping_id
        if index is not None:
            self.index = index
        if value is not None:
            self.value = value
        if source is not None:
            self.set_source(source)

        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.mapping_id = df["mapping_id"]
        self.index = df["index"]
        self.value = df["value"]
        if "source" in df.keys():
            self.set_source(df["source"])
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MParam实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理source字段的枚举转换
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
            del kwargs['source']
        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
