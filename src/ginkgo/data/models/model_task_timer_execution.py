# Upstream: TaskTimer (定时任务触发记录), TaskTimerExecutionService
# Downstream: MMysqlBase, 工具函数
# Role: 定时任务执行记录MySQL模型，记录每次定时任务的触发和执行结果

"""
TaskTimer Execution Record Model

定时任务执行记录模型：记录每次定时任务的触发时间、执行状态、耗时、参数和结果。
支持 triggered → success/failed 状态流转。
"""

import datetime
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs import base_repr


class MTaskTimerExecution(MMysqlBase):
    """
    定时任务执行记录

    业务语义：
    - 每次定时任务触发 = 一条执行记录
    - 状态流转：triggered → success / failed
    - params/result 为 JSON 字段，适配不同任务类型的扩展需求
    """
    __abstract__ = False
    __tablename__ = "task_timer_execution"

    # 任务标识
    job_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="任务名称")
    command: Mapped[str] = mapped_column(String(64), nullable=False, comment="命令类型")
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="TaskTimer 节点标识")
    cron_expr: Mapped[str] = mapped_column(String(32), default="", comment="cron 表达式快照")

    # 执行状态
    status: Mapped[str] = mapped_column(String(16), default="triggered", comment="执行状态: triggered/success/failed")

    # 时间信息
    triggered_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now, comment="触发时间")
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="完成时间")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, comment="执行耗时(毫秒)")

    # 结果信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="失败原因")
    params: Mapped[Optional[str]] = mapped_column(JSON, nullable=True, comment="任务参数(JSON)")
    result: Mapped[Optional[str]] = mapped_column(JSON, nullable=True, comment="执行结果(JSON)")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type for update method.")

    @update.register
    def _from_dict(self, data: dict, *args, **kwargs) -> None:
        """从字典更新字段"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "MTaskTimerExecution", 12)
