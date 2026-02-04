# Upstream: API Server (回测任务管理)
# Downstream: MySQL (backtest_tasks 表)
# Role: MBacktestTask 回测任务 MySQL 模型，提供任务配置和状态管理支持


import datetime
import json
from typing import Optional

from sqlalchemy import String, Float, Text, DateTime
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion


class MBacktestTask(MMysqlBase, ModelConversion):
    """
    回测任务模型

    支持完整的回测任务生命周期管理：
    - 任务创建和配置
    - 状态跟踪 (PENDING/RUNNING/COMPLETED/FAILED/CANCELLED)
    - 进度更新
    - 结果存储
    - Worker 分配
    """
    __abstract__ = False
    __tablename__ = "backtest_tasks"

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), comment="任务名称")
    portfolio_uuid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, comment="主投资组合UUID（兼容旧版）")
    portfolio_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="投资组合名称")
    portfolio_uuids: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="多投资组合UUID列表（JSON数组）")

    # 状态信息
    state: Mapped[str] = mapped_column(String(20), default="PENDING", comment="任务状态")
    progress: Mapped[float] = mapped_column(Float, default=0.0, comment="进度百分比 (0-100)")

    # 配置和结果 (JSON 格式存储)
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="回测配置JSON")
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="回测结果JSON")

    # Worker 信息
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="执行任务的Worker ID")

    # 错误信息
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")

    # 时间字段
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="开始时间")
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="完成时间")

    def get_config_dict(self) -> dict:
        """获取配置字典"""
        if self.config:
            try:
                return json.loads(self.config)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_config_dict(self, config: dict) -> None:
        """设置配置字典"""
        self.config = json.dumps(config) if config else None

    def get_result_dict(self) -> dict:
        """获取结果字典"""
        if self.result:
            try:
                return json.loads(self.result)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_result_dict(self, result: dict) -> None:
        """设置结果字典"""
        self.result = json.dumps(result) if result else None

    def get_portfolio_uuids(self) -> list:
        """获取投资组合UUID列表"""
        if self.portfolio_uuids:
            try:
                return json.loads(self.portfolio_uuids)
            except json.JSONDecodeError:
                pass

        # 兼容旧版：如果 portfolio_uuids 为空，返回 [portfolio_uuid]
        if self.portfolio_uuid:
            return [self.portfolio_uuid]
        return []

    def set_portfolio_uuids(self, uuids: list) -> None:
        """设置投资组合UUID列表"""
        if uuids:
            self.portfolio_uuids = json.dumps(uuids)
            # 同步更新 portfolio_uuid（主Portfolio）
            self.portfolio_uuid = uuids[0]
        else:
            self.portfolio_uuids = None
            self.portfolio_uuid = None
