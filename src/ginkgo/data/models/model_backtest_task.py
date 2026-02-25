<<<<<<< HEAD
# Upstream: API Server (回测任务管理)
# Downstream: MySQL (backtest_tasks 表)
# Role: MBacktestTask 回测任务 MySQL 模型，提供任务配置和状态管理支持


import datetime
import json
from typing import Optional

from sqlalchemy import String, Float, Text, DateTime
=======
# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: MBacktestTask回测任务模型继承MBacktestRecordBase定义回测任务数据结构和字段支持回测历史追踪

"""
Backtest Task Model

回测任务模型：记录每次回测执行的完整信息，是回测列表的核心实体。

Note: 此模型由 MRunRecord 重命名而来，增加了 portfolio_id 等字段。
详见 specs/011-quant-research-modules/backtest-task-model.md

Author: Ginkgo Team
Version: 2.0.0
"""

import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Integer, Text, DateTime
>>>>>>> 011-quant-research
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
<<<<<<< HEAD
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
=======
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MBacktestTask(MMysqlBase, MBacktestRecordBase):
    """
    回测任务模型：记录每次回测执行的完整信息

    业务语义：
    - 一次回测执行 = 一个 BacktestTask
    - 包含执行结果（收益率、最大回撤等）
    - 关联到 Engine（引擎配置）和 Portfolio（投资组合）

    该模型用于：
    - 回测列表展示
    - 追踪每次回测的完整生命周期
    - 统计回测性能指标
    - 存储配置快照用于问题调试
    - 支持回测历史分析和对比
    """
    __abstract__ = False
    __tablename__ = "backtest_task"

    # 执行标识信息
    run_id: Mapped[str] = mapped_column(String(32), unique=True, comment="运行会话ID（统一标识）")
    name: Mapped[str] = mapped_column(String(255), default="", comment="任务名称（用户可读标识）")
    engine_id: Mapped[str] = mapped_column(String(64), default="", comment="所属引擎ID")
    portfolio_id: Mapped[str] = mapped_column(String(32), default="", comment="关联投资组合ID")

    # 回测数据区间
    backtest_start_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="回测开始日期")
    backtest_end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="回测结束日期")

    # 运行时间信息
    start_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, comment="开始时间")
    end_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), default=None, comment="结束时间")
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, default=None, comment="运行时长(秒)")

    # 运行状态
    status: Mapped[str] = mapped_column(String(32), default="created", comment="运行状态: created/pending/running/completed/failed/stopped")
    error_message: Mapped[Optional[str]] = mapped_column(Text, default="", comment="错误信息")

    # 进度信息（SSE推送支持）
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="进度百分比 0-100")
    current_stage: Mapped[str] = mapped_column(String(32), default="", comment="当前阶段: DATA_PREPARING/ENGINE_BUILDING/RUNNING/FINALIZING")
    current_date: Mapped[str] = mapped_column(String(32), default="", comment="当前处理的业务日期")

    # 业务统计
    total_orders: Mapped[int] = mapped_column(Integer, default=0, comment="订单总数")
    total_signals: Mapped[int] = mapped_column(Integer, default=0, comment="信号总数")
    total_positions: Mapped[int] = mapped_column(Integer, default=0, comment="持仓记录数")
    total_events: Mapped[int] = mapped_column(Integer, default=0, comment="事件总数")

    # 性能指标
    avg_event_processing_ms: Mapped[Optional[float]] = mapped_column(String(32), default="0", comment="平均事件处理时间(毫秒)")
    peak_memory_mb: Mapped[Optional[float]] = mapped_column(String(32), default="0", comment="峰值内存使用(MB)")

    # 配置和环境信息
    config_snapshot: Mapped[str] = mapped_column(Text, default="{}", comment="配置快照JSON")
    environment_info: Mapped[str] = mapped_column(Text, default="{}", comment="环境信息JSON")

    # 运行结果摘要
    final_portfolio_value: Mapped[Optional[str]] = mapped_column(String(32), default="0", comment="最终组合价值")
    total_pnl: Mapped[Optional[str]] = mapped_column(String(32), default="0", comment="总盈亏")
    max_drawdown: Mapped[Optional[str]] = mapped_column(String(32), default="0", comment="最大回撤")
    sharpe_ratio: Mapped[Optional[str]] = mapped_column(String(32), default="0", comment="夏普比率")
    annual_return: Mapped[Optional[str]] = mapped_column(String(32), default="0", comment="年化收益率")
    win_rate: Mapped[Optional[str]] = mapped_column(String(32), default="0", comment="胜率")

    business_timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="业务时间戳")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        run_id: str,
        name: str = "",
        engine_id: str = "",
        portfolio_id: str = "",
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        status: str = "running",
        error_message: str = "",
        total_orders: int = 0,
        total_signals: int = 0,
        total_positions: int = 0,
        total_events: int = 0,
        config_snapshot: str = "{}",
        environment_info: str = "{}",
        final_portfolio_value: str = "0",
        total_pnl: str = "0",
        max_drawdown: str = "0",
        sharpe_ratio: str = "0",
        annual_return: str = "0",
        win_rate: str = "0",
        business_timestamp: Optional[datetime.datetime] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.run_id = run_id
        self.name = name
        self.engine_id = engine_id
        self.portfolio_id = portfolio_id
        self.status = status
        self.error_message = error_message
        self.total_orders = total_orders
        self.total_signals = total_signals
        self.total_positions = total_positions
        self.total_events = total_events
        self.config_snapshot = config_snapshot
        self.environment_info = environment_info
        self.final_portfolio_value = final_portfolio_value
        self.total_pnl = total_pnl
        self.max_drawdown = max_drawdown
        self.sharpe_ratio = sharpe_ratio
        self.annual_return = annual_return
        self.win_rate = win_rate

        if business_timestamp is not None:
            self.business_timestamp = datetime_normalize(business_timestamp)

        if start_time is not None:
            self.start_time = datetime_normalize(start_time)
        else:
            self.start_time = datetime.datetime.now()

        if end_time is not None:
            self.end_time = datetime_normalize(end_time)
            # 计算运行时长
            if self.start_time and self.end_time:
                delta = self.end_time - self.start_time
                self.duration_seconds = int(delta.total_seconds())

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1

        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {
            "run_id", "start_time", "status"
        }

        # 验证必填字段
        missing_fields = required_fields - set(df.index)
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        self.run_id = df["run_id"]
        self.start_time = datetime_normalize(df["start_time"])
        self.status = df["status"]

        # 可选字段
        if "engine_id" in df.index:
            self.engine_id = str(df["engine_id"])
        if "portfolio_id" in df.index:
            self.portfolio_id = str(df["portfolio_id"])
        if "end_time" in df.index and pd.notna(df["end_time"]):
            self.end_time = datetime_normalize(df["end_time"])
        if "error_message" in df.index:
            self.error_message = str(df["error_message"])
        if "total_orders" in df.index:
            self.total_orders = int(df["total_orders"])
        if "total_signals" in df.index:
            self.total_signals = int(df["total_signals"])
        if "total_positions" in df.index:
            self.total_positions = int(df["total_positions"])
        if "total_events" in df.index:
            self.total_events = int(df["total_events"])
        if "config_snapshot" in df.index:
            self.config_snapshot = str(df["config_snapshot"])
        if "environment_info" in df.index:
            self.environment_info = str(df["environment_info"])
        if "final_portfolio_value" in df.index:
            self.final_portfolio_value = str(df["final_portfolio_value"])
        if "total_pnl" in df.index:
            self.total_pnl = str(df["total_pnl"])
        if "max_drawdown" in df.index:
            self.max_drawdown = str(df["max_drawdown"])
        if "sharpe_ratio" in df.index:
            self.sharpe_ratio = str(df["sharpe_ratio"])
        if "annual_return" in df.index:
            self.annual_return = str(df["annual_return"])
        if "win_rate" in df.index:
            self.win_rate = str(df["win_rate"])

        if "business_timestamp" in df.index and pd.notna(df["business_timestamp"]):
            self.business_timestamp = datetime_normalize(df["business_timestamp"])

        if "source" in df.index:
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1

        self.update_at = datetime.datetime.now()

    def start_task(self, config_snapshot: str = "{}", environment_info: str = "{}") -> None:
        """
        标记任务开始

        Args:
            config_snapshot (str): 配置快照JSON
            environment_info (str): 环境信息JSON
        """
        self.start_time = datetime.datetime.now()
        self.status = "running"
        self.config_snapshot = config_snapshot
        self.environment_info = environment_info
        self.update_at = datetime.datetime.now()

    def finish_task(self, status: str = "completed", error_message: str = "",
                    final_portfolio_value: str = "0", total_pnl: str = "0",
                    max_drawdown: str = "0", sharpe_ratio: str = "0",
                    annual_return: str = "0", win_rate: str = "0") -> None:
        """
        标记任务结束

        Args:
            status (str): 最终状态 (completed/failed/stopped)
            error_message (str): 错误信息
            final_portfolio_value (str): 最终组合价值
            total_pnl (str): 总盈亏
            max_drawdown (str): 最大回撤
            sharpe_ratio (str): 夏普比率
            annual_return (str): 年化收益率
            win_rate (str): 胜率
        """
        self.end_time = datetime.datetime.now()
        self.status = status
        self.error_message = error_message
        self.final_portfolio_value = final_portfolio_value
        self.total_pnl = total_pnl
        self.max_drawdown = max_drawdown
        self.sharpe_ratio = sharpe_ratio
        self.annual_return = annual_return
        self.win_rate = win_rate

        # 计算运行时长
        if self.start_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = int(delta.total_seconds())

        self.update_at = datetime.datetime.now()

    def update_statistics(self, total_orders: int = None, total_signals: int = None,
                          total_positions: int = None, total_events: int = None) -> None:
        """
        更新任务统计数据

        Args:
            total_orders (int): 订单总数
            total_signals (int): 信号总数
            total_positions (int): 持仓记录数
            total_events (int): 事件总数
        """
        if total_orders is not None:
            self.total_orders = total_orders
        if total_signals is not None:
            self.total_signals = total_signals
        if total_positions is not None:
            self.total_positions = total_positions
        if total_events is not None:
            self.total_events = total_events

        self.update_at = datetime.datetime.now()

    def update_progress(self, progress: int = None, current_stage: str = None,
                        current_date: str = None) -> None:
        """
        更新任务进度（用于SSE实时推送）

        Args:
            progress (int): 进度百分比 0-100
            current_stage (str): 当前阶段
            current_date (str): 当前处理的业务日期
        """
        if progress is not None:
            self.progress = int(min(100, max(0, progress)))
        if current_stage is not None:
            self.current_stage = current_stage
        if current_date is not None:
            self.current_date = current_date

        self.update_at = datetime.datetime.now()

    def get_task_summary(self) -> dict:
        """
        获取任务摘要信息

        Returns:
            dict: 任务摘要
        """
        return {
            'uuid': self.uuid,
            'run_id': self.run_id,
            'engine_id': self.engine_id,
            'portfolio_id': self.portfolio_id,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'statistics': {
                'total_orders': self.total_orders,
                'total_signals': self.total_signals,
                'total_positions': self.total_positions,
                'total_events': self.total_events,
            },
            'results': {
                'final_portfolio_value': self.final_portfolio_value,
                'total_pnl': self.total_pnl,
                'max_drawdown': self.max_drawdown,
                'sharpe_ratio': self.sharpe_ratio,
                'annual_return': self.annual_return,
                'win_rate': self.win_rate,
            },
            'error_message': self.error_message if self.error_message else None
        }

    @property
    def task_id(self) -> str:
        """向后兼容属性，返回 run_id"""
        return self.run_id

    def __repr__(self) -> str:
        return base_repr(self, f"BacktestTask[{self.status}]", 12, 80)


# 向后兼容别名
MRunRecord = MBacktestTask
>>>>>>> 011-quant-research
