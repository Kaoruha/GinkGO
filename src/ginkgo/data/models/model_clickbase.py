import pandas as pd
import uuid
import datetime

from typing import Optional
from types import FunctionType, MethodType
from sqlalchemy import Enum, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from clickhouse_sqlalchemy import engines, types

from ginkgo.data.models.model_base import MBase
from ginkgo.libs import datetime_normalize
from ginkgo.libs.utils.display import base_repr
from ginkgo.enums import SOURCE_TYPES


class Base(DeclarativeBase):
    pass


class MClickBase(Base, MBase):
    """
    ClickHouse Base Model

    基础模型提供：
    - uuid: 主键，组件实例唯一标识
    """
    __abstract__ = True
    __tablename__ = "ClickBaseModel"
    __table_args__ = (
        # 优化排序键：按时间排序
        engines.MergeTree(order_by=("timestamp",)),
        {"extend_existing": True},
    )

    # 基础ID字段
    uuid: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    
    # 元数据字段
    meta: Mapped[Optional[str]] = mapped_column(String(), default="{}")
    desc: Mapped[Optional[str]] = mapped_column(String(), default="This man is lazy, there is no description.")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)
    source: Mapped[int] = mapped_column(types.Int8, default=-1)

    def get_source_enum(self):
        """Convert database source integer back to enum for business layer"""
        return SOURCE_TYPES.from_int(self.source)

    def update(self) -> None:
        raise NotImplementedError("Model Class need to overload Function set to transit data.")

    def set_source(self, source, *args, **kwargs) -> None:
        """Set source with enum/int dual input support"""
        try:
            result = SOURCE_TYPES.validate_input(source)
            self.source = result if result is not None else -1
        except Exception:
            # 如果转换过程中出现任何异常（如传入无效字符串），则设置为-1
            self.source = -1

    def __init__(self, **kwargs):
        """初始化MClickBase实例，自动处理枚举字段转换"""
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
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 80)
