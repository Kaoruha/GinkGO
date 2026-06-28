# Upstream: BacktestWorker, BacktestProcessor (创建/使用任务对象)
# Downstream: BacktestProcessor, ProgressTracker (任务状态和配置)
# Role: 回测任务数据模型(BacktestTask/BacktestConfig/状态枚举)

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
    """回测配置（状态主体，ADR-018：默认表归 DTO BacktestAssignmentConfig）

    无默认值——所有 11 字段 required。映射函数 assignment_to_backtest_config 显式传全；
    进程内直接构造（测试/CLI 直跑）也须显式传全，杜绝 BacktestConfig↔DTO 默认 drift。
    """

    start_date: str
    end_date: str
    initial_cash: float
    commission_rate: float
    slippage_rate: float
    benchmark_return: float
    max_position_ratio: float
    stop_loss_ratio: float
    take_profit_ratio: float
    frequency: str
    # 分析器配置（Engine 级别）
    analyzers: list[AnalyzerConfig]


def assignment_to_backtest_config(cmd) -> "BacktestConfig":
    """ADR-018：StartAssignment（DTO 信使）→ BacktestConfig（worker 状态主体）。

    第三者胶水映射，不挂 DTO 也不挂状态主体（ADR-010 信使/主体分离）。
    analyzers list[dict] → list[AnalyzerConfig]，字段不全转 MalformedAssignmentError
    （与消费端窄捕一致）。DTO 唯一默认表已填齐 9 optional，此处逐字段复制。
    """
    from ginkgo.interfaces.dtos.backtest_assignment_dto import MalformedAssignmentError

    cfg = cmd.config
    analyzers = []
    for d in cfg.analyzers:
        try:
            analyzers.append(AnalyzerConfig(**d))
        except TypeError as e:
            raise MalformedAssignmentError(f"invalid analyzer config {d!r}: {e}") from e
    return BacktestConfig(
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        initial_cash=cfg.initial_cash,
        commission_rate=cfg.commission_rate,
        slippage_rate=cfg.slippage_rate,
        benchmark_return=cfg.benchmark_return,
        max_position_ratio=cfg.max_position_ratio,
        stop_loss_ratio=cfg.stop_loss_ratio,
        take_profit_ratio=cfg.take_profit_ratio,
        frequency=cfg.frequency,
        analyzers=analyzers,
    )


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
