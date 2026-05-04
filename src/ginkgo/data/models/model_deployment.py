# Upstream: DeploymentService
# Downstream: MySQL Database (deployment表)
# Role: 部署记录数据模型 - 追踪回测到纸上交易/实盘的部署历史

import datetime
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs.utils.display import base_repr


class DEPLOYMENT_STATUS:
    """部署状态"""
    PENDING = 0
    DEPLOYED = 1
    FAILED = 2
    STOPPED = 3


class MDeployment(MMysqlBase):
    __abstract__ = False
    __tablename__ = "deployment"

    source_task_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default=None, comment="回测任务ID（兼容旧数据）")
    target_portfolio_id: Mapped[str] = mapped_column(String(32), default="", comment="部署后的Portfolio ID")
    source_portfolio_id: Mapped[str] = mapped_column(String(32), default="", comment="原始回测Portfolio ID")
    mode: Mapped[int] = mapped_column(Integer, default=-1, comment="运行模式: 0=回测, 1=纸上交易, 2=实盘")
    account_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="实盘账号ID (live模式)")
    status: Mapped[int] = mapped_column(Integer, default=DEPLOYMENT_STATUS.PENDING, comment="部署状态")

    @singledispatchmethod
    def update(self, *args, **kwargs):
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(self, source_task_id: str, **kwargs):
        self.source_task_id = source_task_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
