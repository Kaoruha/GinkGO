"""
Backtest Task Models

回测任务数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class BacktestTaskState(str, Enum):
    """回测任务状态"""

    PENDING = "PENDING"
    DATA_PREPARING = "DATA_PREPARING"
    ENGINE_BUILDING = "ENGINE_BUILDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EngineStage(str, Enum):
    """引擎执行阶段"""

    DATA_PREPARING = "DATA_PREPARING"
    ENGINE_BUILDING = "ENGINE_BUILDING"
    RUNNING = "RUNNING"
    FINALIZING = "FINALIZING"


@dataclass
class AnalyzerConfig:
    """分析器配置"""
    name: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestConfig:
    """回测配置"""

    start_date: str
    end_date: str
    initial_cash: float = 100000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0001
    benchmark_return: float = 0.0
    max_position_ratio: float = 0.3
    stop_loss_ratio: float = 0.05
    take_profit_ratio: float = 0.15
    frequency: str = "DAY"
    # 分析器配置（Engine 级别）
    analyzers: list[AnalyzerConfig] = field(default_factory=list)


@dataclass
class BacktestTask:
    """回测任务"""

    task_uuid: str
    portfolio_uuid: str
    name: str
    config: BacktestConfig
    state: BacktestTaskState = BacktestTaskState.PENDING
    progress: float = 0.0
    current_stage: EngineStage = EngineStage.DATA_PREPARING
    current_date: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def create(cls, portfolio_uuid: str, name: str, config: BacktestConfig) -> "BacktestTask":
        return cls(
            task_uuid=str(uuid.uuid4()),
            portfolio_uuid=portfolio_uuid,
            name=name,
            config=config,
        )
