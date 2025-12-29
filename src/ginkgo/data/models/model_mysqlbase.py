# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: MySQL基础数据模型继承MBase提供uuid/created_at/updated_at/is_del等字段






import uuid
import pandas as pd
import datetime

from types import FunctionType, MethodType
from typing import Optional
from sqlalchemy import Enum, String, DateTime, Boolean
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ginkgo.data.models.model_base import MBase
from ginkgo.libs import datetime_normalize
from ginkgo.libs.utils.display import base_repr
from ginkgo.enums import SOURCE_TYPES


class Base(DeclarativeBase):
    pass


class MMysqlBase(Base, MBase):
    """
    MySQL Base Model

    最小基础模型，提供所有MySQL表共享的字段：
    - uuid: 主键，组件实例唯一标识
    - 元数据字段：create_at, update_at, is_del等

    对于需要engine_id/run_id的模型，请多重继承MBacktestRecordBase。
    """
    __abstract__ = True
    __tablename__ = "MysqlBaseModel"

    # 基础ID字段
    uuid: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    
    # 元数据字段
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
        try:
            result = SOURCE_TYPES.validate_input(source)
            self.source = result if result is not None else -1
        except Exception:
            # 如果转换过程中出现任何异常（如传入无效字符串），则设置为-1
            self.source = -1

    def delete(self, *args, **kwargs) -> None:
        self.is_del = True

    def cancel_delete(self, *args, **kwargs) -> None:
        self.is_del = False

    def __init__(self, **kwargs):
        """初始化MMysqlBase实例，自动处理枚举字段转换"""
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
