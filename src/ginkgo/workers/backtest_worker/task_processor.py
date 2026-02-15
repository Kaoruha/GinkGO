"""
Backtest Task Processor

单个回测任务处理器（对应ExecutionNode的PortfolioProcessor）

职责：
- 任务生命周期管理（启动、运行、停止、清理）
- 调用EngineAssemblyService装配TimeControlledEventEngine
- 执行回测并上报进度
- 处理结果和异常
"""

from threading import Thread, Event
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import time

from ginkgo.workers.backtest_worker.models import BacktestTask, BacktestTaskState, EngineStage
from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
from ginkgo.workers.backtest_worker.progress_tracker import ProgressTracker
# GLOG removed
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine


class BacktestProcessor(Thread):
    """回测任务处理器"""

    def __init__(self, task: BacktestTask, worker_id: str, progress_tracker: ProgressTracker):
        """
        初始化任务处理器

        Args:
            task: 回测任务
            worker_id: 所属Worker ID
            progress_tracker: 进度上报器
        """
        super().__init__(daemon=True)
        self.task = task
        self.worker_id = worker_id
        self.progress_tracker = progress_tracker

        # 线程控制
        self._stop_event = Event()
        self._engine: Optional[TimeControlledEventEngine] = None
        self._exception: Optional[Exception] = None
        self._result: Optional[Dict[str, Any]] = None

    def run(self):
        """执行回测任务"""
        self.task.started_at = datetime.utcnow()
        self.task.worker_id = self.worker_id

        try:
            print(f"[{self.task.task_uuid[:8]}] Starting backtest task: {self.task.name}")

            # 保存进度回调到config中
            self.task.config._progress_callback = self._on_progress

            # 阶段1: 数据准备
            self.task.state = BacktestTaskState.DATA_PREPARING
            self.task.current_stage = EngineStage.DATA_PREPARING
            self.progress_tracker.report_stage(self.task, EngineStage.DATA_PREPARING, "Preparing data...")
            time.sleep(0.5)  # 给上报一点时间

            # 阶段2: 引擎装配
            self.task.state = BacktestTaskState.ENGINE_BUILDING
            self.task.current_stage = EngineStage.ENGINE_BUILDING
            self.progress_tracker.report_stage(self.task, EngineStage.ENGINE_BUILDING, "Building engine...")

            assembly_service = EngineAssemblyService()
            self._engine = assembly_service.build_engine_from_task(self.task)

            # 阶段3: 运行回测
            self.task.state = BacktestTaskState.RUNNING
            self.task.current_stage = EngineStage.RUNNING
            self.progress_tracker.report_stage(self.task, EngineStage.RUNNING, "Running backtest...")

            # 执行回测
            result = self._engine.run()

            # 计算回测结果
            self._result = self._calculate_result(result)

            # 通知分析器回测结束
            if hasattr(self._engine, 'notify_analyzers_backtest_end'):
                self._engine.notify_analyzers_backtest_end()

            # 阶段4: 完成处理
            self.task.state = BacktestTaskState.COMPLETED
            self.task.progress = 100.0
            self.task.completed_at = datetime.utcnow()
            self.task.result = self._result

            self.progress_tracker.report_completed(self.task, self._result)
            print(f"[{self.task.task_uuid[:8]}] Backtest completed successfully")

        except InterruptedError:
            self.task.state = BacktestTaskState.CANCELLED
            self.task.completed_at = datetime.utcnow()
            self.progress_tracker.report_cancelled(self.task)
            print(f"[{self.task.task_uuid[:8]}] Backtest cancelled")

        except Exception as e:
            self._exception = e
            self.task.state = BacktestTaskState.FAILED
            self.task.error = str(e)
            self.task.completed_at = datetime.utcnow()

            self.progress_tracker.report_failed(self.task, str(e))
            print(f"[{self.task.task_uuid[:8]}] Backtest failed: {e}")
            import traceback
            print(traceback.format_exc())

    def _on_progress(self, progress: float, current_date: str, current_time: datetime = None):
        """进度回调（由引擎调用）"""
        if self._stop_event.is_set():
            raise InterruptedError("Task was cancelled")

        self.task.progress = progress
        self.task.current_date = current_date

        # 每2秒上报一次（由ProgressTracker控制频率）
        self.progress_tracker.report_progress(self.task, progress, current_date)

    def _calculate_result(self, engine_result: Dict[str, Any]) -> Dict[str, Any]:
        """计算回测结果"""
        try:
            # 从引擎获取Portfolio
            portfolio = self._engine.portfolios[self.task.portfolio_uuid]

            # 基础指标
            initial_cash = self.task.config.initial_cash
            final_cash = portfolio.get_cash()
            total_return = (final_cash - initial_cash) / initial_cash if initial_cash > 0 else 0

            # TODO: 计算更多指标
            result = {
                "task_uuid": self.task.task_uuid,
                "total_return": total_return,
                "annual_return": 0.0,  # TODO
                "sharpe_ratio": 0.0,  # TODO
                "max_drawdown": 0.0,  # TODO
                "win_rate": 0.0,  # TODO
                "profit_loss_ratio": 0.0,
                "total_trades": 0,
                "total_days": 0,
                "daily_returns": [],
                "equity_curve": [],
                "drawdowns": [],
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
            }

            return result

        except Exception as e:
            print(f"Failed to calculate result: {e}")
            return {
                "task_uuid": self.task.task_uuid,
                "total_return": 0.0,
                "error": str(e),
            }

    def cancel(self):
        """取消任务"""
        print(f"[{self.task.task_uuid[:8]}] Cancelling task...")
        self._stop_event.set()

        if self._engine and hasattr(self._engine, 'stop'):
            self._engine.stop()

        self.task.state = BacktestTaskState.CANCELLED
        self.progress_tracker.report_cancelled(self.task)

    def get_status(self) -> dict:
        """获取任务状态"""
        return {
            "task_uuid": self.task.task_uuid,
            "name": self.task.name,
            "state": self.task.state.value,
            "progress": self.task.progress,
            "current_stage": self.task.current_stage.value,
            "current_date": self.task.current_date,
            "started_at": self.task.started_at.isoformat() if self.task.started_at else None,
            "error": self.task.error,
        }


class InterruptedError(Exception):
    """任务被中断"""
    pass
