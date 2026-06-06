# Upstream: 数据同步 API (update_data), DataSyncRecordService
# Downstream: MMysqlBase, 工具函数
# Role: 数据同步记录MySQL模型，记录每次数据同步操作的类型、状态、耗时和统计

"""
Data Sync Record Model

数据同步记录模型：记录每次数据同步操作的类型、股票代码、执行状态、耗时和统计。
支持 running → success / partial / failed 状态流转。
"""

import datetime
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs import base_repr


class MDataSyncRecord(MMysqlBase):
    """
    数据同步记录

    业务语义：
    - 每次数据同步操作 = 一条记录（按 code 粒度）
    - 状态流转：running → success / partial / failed
    - stockinfo 同步 code 字段为 "ALL"
    """
    __abstract__ = False
    __tablename__ = "data_sync_record"

    # 同步类型
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="同步类型: stockinfo/bars/ticks/adjustfactor")
    code: Mapped[str] = mapped_column(String(32), nullable=False, comment="股票代码，stockinfo 为 ALL")

    # 执行状态
    status: Mapped[str] = mapped_column(String(16), default="running", comment="状态: running/success/partial/failed")

    # 时间信息
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now, comment="同步开始时间")
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="同步完成时间")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, comment="执行耗时(毫秒)")

    # 同步统计
    records_processed: Mapped[int] = mapped_column(Integer, default=0, comment="处理记录数")
    records_added: Mapped[int] = mapped_column(Integer, default=0, comment="新增记录数")
    records_updated: Mapped[int] = mapped_column(Integer, default=0, comment="更新记录数")
    records_failed: Mapped[int] = mapped_column(Integer, default=0, comment="失败记录数")

    # 结果信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="失败原因")
    sync_strategy: Mapped[str] = mapped_column(String(32), default="", comment="同步策略: full/incremental/smart")

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
        return base_repr(self, "MDataSyncRecord", 12)
