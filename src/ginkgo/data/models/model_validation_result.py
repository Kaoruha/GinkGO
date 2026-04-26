# Upstream: ValidationResultCRUD, ValidationService
# Downstream: MMysqlBase, MySQL Database
# Role: 验证结果数据模型 - 存储各类验证方法的计算结果

import datetime
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs.utils.display import base_repr


class VALIDATION_STATUS:
    RUNNING = 0
    COMPLETED = 1
    FAILED = 2


class MValidationResult(MMysqlBase):
    __abstract__ = False
    __tablename__ = "validation_result"

    task_id: Mapped[str] = mapped_column(String(32), default="", index=True, comment="回测任务ID")
    portfolio_id: Mapped[str] = mapped_column(String(32), default="", index=True, comment="组合ID(冗余)")
    method: Mapped[str] = mapped_column(String(32), default="", index=True, comment="验证方法")
    config: Mapped[str] = mapped_column(Text, default="{}", comment="JSON: 输入参数含 version")
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON: 完整结果")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="摘要评分")
    status: Mapped[int] = mapped_column(Integer, default=VALIDATION_STATUS.RUNNING, comment="状态")

    @singledispatchmethod
    def update(self, *args, **kwargs):
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(self, method: str, **kwargs):
        self.method = method
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
