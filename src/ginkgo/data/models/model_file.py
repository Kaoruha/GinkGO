import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Enum, LargeBinary, Boolean
from sqlalchemy.dialects.mysql import TINYINT, MEDIUMBLOB
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MFile(MMysqlBase):
    __abstract__ = False
    __tablename__ = "file"

    type: Mapped[int] = mapped_column(TINYINT, default=-1)
    name: Mapped[str] = mapped_column(String(40), default="ginkgo_file")
    data: Mapped[bytes] = mapped_column(MEDIUMBLOB, default=b"")

    # 版本管理字段
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", comment="版本号")
    parent_uuid: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="父版本UUID")
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否最新版本")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type --> {args}")

    @update.register(str)
    def _(
        self,
        name: str,
        type: Optional[FILE_TYPES] = None,
        data: Optional[bytes] = None,
        source: Optional[SOURCE_TYPES] = None,
        version: Optional[str] = None,
        parent_uuid: Optional[str] = None,
        is_latest: Optional[bool] = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        if type is not None:
            self.type = FILE_TYPES.validate_input(type) or -1
        if data is not None:
            self.data = data
        if source is not None:
            self.set_source(source)
        if version is not None:
            self.version = version
        if parent_uuid is not None:
            self.parent_uuid = parent_uuid
        if is_latest is not None:
            self.is_latest = is_latest
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        # TODO
        if "source" in df.keys():
            self.set_source(df["source"])
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MFile实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理type字段的枚举转换
        if 'type' in kwargs:
            from ginkgo.enums import FILE_TYPES
            result = FILE_TYPES.validate_input(kwargs['type'])
            self.type = result if result is not None else -1
            del kwargs['type']
        # 调用父类构造函数处理source字段
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
