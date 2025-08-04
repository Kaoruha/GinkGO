import pandas as pd
import uuid
import datetime

from typing import Optional
from types import FunctionType, MethodType
from sqlalchemy import Enum, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from clickhouse_sqlalchemy import engines


from .model_base import MBase
from ...libs import datetime_normalize
from ...libs.utils.display import base_repr
from ...enums import SOURCE_TYPES


class Base(DeclarativeBase):
    pass


class MClickBase(Base, MBase):
    __abstract__ = True
    __tablename__ = "ClickBaseModel"
    __table_args__ = (
        engines.MergeTree(order_by=("timestamp",)),
        {"extend_existing": True},
    )

    uuid: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    meta: Mapped[Optional[str]] = mapped_column(String(255), default="{}")
    desc: Mapped[Optional[str]] = mapped_column(String(255), default="This man is lazy, there is no description.")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)
    # timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)
    source: Mapped[SOURCE_TYPES] = mapped_column(Enum(SOURCE_TYPES), default=SOURCE_TYPES.OTHER)

    def __getattribute__(self, name):
        """自动清理 ClickHouse 字符串字段的尾部空字节"""
        value = super().__getattribute__(name)
        
        # 对字符串值进行清理，并且要检查这是否是数据库字段
        if isinstance(value, str) and not name.startswith('_'):
            # 检查是否是映射的数据库字段
            try:
                if hasattr(self.__class__, name):
                    attr = getattr(self.__class__, name)
                    if hasattr(attr, 'type'):
                        # 应用与 to_dataframe() 相同的清理逻辑
                        return value.strip('\x00')
            except:
                # 如果检查失败，安全地返回原值
                pass
                
        return value

    def update(self) -> None:
        raise NotImplementedError("Model Class need to overload Function set to transit data.")

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 80)
