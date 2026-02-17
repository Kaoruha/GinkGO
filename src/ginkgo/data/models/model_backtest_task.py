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
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
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
    task_id: Mapped[str] = mapped_column(String(128), unique=True, comment="任务会话ID")
    engine_id: Mapped[str] = mapped_column(String(64), default="", comment="所属引擎ID")
    portfolio_id: Mapped[str] = mapped_column(String(32), default="", comment="关联投资组合ID")

    # 运行时间信息
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), comment="开始时间")
    end_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), default=None, comment="结束时间")
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, default=None, comment="运行时长(秒)")

    # 运行状态
    status: Mapped[str] = mapped_column(String(32), default="running", comment="运行状态: running/completed/failed/stopped")
    error_message: Mapped[Optional[str]] = mapped_column(Text, default="", comment="错误信息")

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
        task_id: str,
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
        self.task_id = task_id
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
            "task_id", "start_time", "status"
        }

        # 验证必填字段
        missing_fields = required_fields - set(df.index)
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        self.task_id = df["task_id"]
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

    def get_task_summary(self) -> dict:
        """
        获取任务摘要信息

        Returns:
            dict: 任务摘要
        """
        return {
            'uuid': self.uuid,
            'task_id': self.task_id,
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

    def __repr__(self) -> str:
        return base_repr(self, f"BacktestTask[{self.status}]", 12, 80)


# 向后兼容别名
MRunRecord = MBacktestTask
