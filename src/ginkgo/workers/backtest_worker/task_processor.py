"""
Backtest Task Processor

单个回测任务处理器（对应ExecutionNode的PortfolioProcessor）

职责：
- 任务生命周期管理（启动、运行、停止、清理）
- 调用 EngineAssemblyService 装配引擎
- 执行回测并上报进度
- 处理结果和异常
"""

from threading import Thread, Event
from typing import Optional, Dict, Any
from datetime import datetime
import time

from ginkgo.workers.backtest_worker.models import BacktestTask, BacktestTaskState, EngineStage
from ginkgo.workers.backtest_worker.progress_tracker import ProgressTracker
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo import services
from ginkgo.libs import GinkgoLogger
from ginkgo.trading.time.clock import now as clock_now


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

        # 服务
        self._assembly_service = services.trading.services.engine_assembly_service()
        self._portfolio_service = services.data.portfolio_service()

    def run(self):
        """执行回测任务"""
        self.task.started_at = datetime.utcnow()
        self.task.worker_id = self.worker_id

        try:
            print(f"[{self.task.task_uuid[:8]}] Starting backtest task: {self.task.name}")

            # 阶段1: 数据准备
            self.task.state = BacktestTaskState.DATA_PREPARING
            self.task.current_stage = EngineStage.DATA_PREPARING
            self.progress_tracker.report_stage(self.task, EngineStage.DATA_PREPARING, "Preparing data...")
            time.sleep(0.5)

            # 阶段2: 引擎装配
            self.task.state = BacktestTaskState.ENGINE_BUILDING
            self.task.current_stage = EngineStage.ENGINE_BUILDING
            self.progress_tracker.report_stage(self.task, EngineStage.ENGINE_BUILDING, "Building engine...")

            self._engine = self._assemble_engine()

            # 阶段3: 运行回测
            self.task.state = BacktestTaskState.RUNNING
            self.task.current_stage = EngineStage.RUNNING
            self.progress_tracker.report_stage(self.task, EngineStage.RUNNING, "Running backtest...")

            # 执行回测（run() 启动引擎后立即返回，需要等待引擎完成）
            result = self._engine.run()

            # 等待引擎主线程完成
            self._wait_for_engine_completion()

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

    def _wait_for_engine_completion(self, timeout: float = 3600.0):
        """
        等待引擎主线程完成

        Args:
            timeout: 最大等待时间（秒），默认1小时
        """
        if self._engine is None:
            return

        # 获取引擎的主线程
        main_thread = getattr(self._engine, '_main_thread', None)
        if main_thread is None:
            print(f"[{self.task.task_uuid[:8]}] Engine has no main thread, skipping wait")
            return

        # 检查线程是否已启动
        if not main_thread.is_alive():
            print(f"[{self.task.task_uuid[:8]}] Engine main thread already completed")
            return

        # 等待线程完成
        print(f"[{self.task.task_uuid[:8]}] Waiting for engine to complete...")
        main_thread.join(timeout=timeout)

        if main_thread.is_alive():
            print(f"[{self.task.task_uuid[:8]}] Engine did not complete within {timeout}s, forcing stop")
            self._engine.stop()
            main_thread.join(timeout=10.0)
        else:
            print(f"[{self.task.task_uuid[:8]}] Engine completed successfully")

    def _assemble_engine(self) -> TimeControlledEventEngine:
        """
        装配回测引擎

        将 BacktestTask 转换为 EngineAssemblyService 需要的参数格式
        """
        print(f"[{self.task.task_uuid[:8]}] Assembling backtest engine...")

        # 1. 构建引擎配置
        engine_data = {
            "name": f"BacktestEngine_{self.task.task_uuid[:8]}",
            "run_id": self.task.task_uuid,
            "backtest_start_date": self.task.config.start_date,
            "backtest_end_date": self.task.config.end_date,
            "initial_capital": self.task.config.initial_cash,
            "commission_rate": self.task.config.commission_rate,
            "slippage_rate": self.task.config.slippage_rate,
            "broker": "backtest",
            "frequency": self.task.config.frequency,
        }

        # 2. 获取 Portfolio 配置和组件
        portfolio_config, portfolio_components = self._get_portfolio_config_and_components()

        # 3. 构建 portfolio mappings
        portfolio_mapping = type('PortfolioMapping', (), {
            'portfolio_id': self.task.portfolio_uuid
        })()
        portfolio_mappings = [portfolio_mapping]

        # 4. 构建 portfolio_configs 和 portfolio_components 字典
        portfolio_configs = {self.task.portfolio_uuid: portfolio_config}
        portfolio_components_dict = {self.task.portfolio_uuid: portfolio_components}

        # 5. 创建 logger
        now = clock_now().strftime("%Y%m%d%H%M%S")
        logger = GinkgoLogger(
            logger_name=f"backtest_{self.task.task_uuid[:8]}",
            file_names=[f"bt_{self.task.task_uuid[:8]}_{now}"],
            console_log=False
        )

        # 6. 调用 EngineAssemblyService
        result = self._assembly_service.assemble_backtest_engine(
            engine_id=self.task.task_uuid,
            engine_data=engine_data,
            portfolio_mappings=portfolio_mappings,
            portfolio_configs=portfolio_configs,
            portfolio_components=portfolio_components_dict,
            logger=logger
        )

        if not result.success:
            raise RuntimeError(f"Failed to assemble engine: {result.error}")

        print(f"[{self.task.task_uuid[:8]}] Engine assembled successfully")
        return result.data

    def _get_portfolio_config_and_components(self) -> tuple:
        """
        获取 Portfolio 配置和组件

        必须从数据库加载，没有组件配置视为错误
        """
        # 从数据库加载
        portfolio_result = self._portfolio_service.load_portfolio_with_components(
            portfolio_id=self.task.portfolio_uuid
        )

        if not portfolio_result.is_success() or not portfolio_result.data:
            raise ValueError(f"Portfolio {self.task.portfolio_uuid} not found in database")

        # 从数据库获取配置
        config = self._extract_portfolio_config_from_db(portfolio_result.data)

        # 获取组件文件映射
        components = self._get_portfolio_components_from_db()

        if not components:
            raise ValueError(
                f"Portfolio {self.task.portfolio_uuid} has no component configured. "
                f"Please bind at least one strategy to the portfolio before running backtest."
            )

        # 检查是否有策略组件
        if not components.get("strategies"):
            raise ValueError(
                f"Portfolio {self.task.portfolio_uuid} has no strategy configured. "
                f"Please bind at least one strategy to the portfolio before running backtest."
            )

        print(f"[{self.task.task_uuid[:8]}] Loaded portfolio {self.task.portfolio_uuid} from database")
        return config, components

    def _extract_portfolio_config_from_db(self, portfolio_data) -> Dict[str, Any]:
        """从数据库结果提取 Portfolio 配置"""
        return {
            "uuid": self.task.portfolio_uuid,
            "name": portfolio_data.name if hasattr(portfolio_data, 'name') else f"Portfolio_{self.task.portfolio_uuid[:8]}",
            "cash": float(portfolio_data.cash) if hasattr(portfolio_data, 'cash') else self.task.config.initial_cash,
            "initial_capital": self.task.config.initial_cash,
        }

    def _get_portfolio_components_from_db(self) -> Dict[str, Any]:
        """从数据库获取 Portfolio 组件配置"""
        try:
            from ginkgo.data.containers import container as data_container
            from ginkgo.enums import FILE_TYPES

            # 获取文件映射 CRUD
            file_mapping_crud = data_container.cruds.portfolio_file_mapping()

            # 查询映射 - 使用 find_by_portfolio 或 find
            mappings = file_mapping_crud.find(
                filters={"portfolio_id": self.task.portfolio_uuid, "is_del": False}
            )
            if not mappings:
                print(f"[{self.task.task_uuid[:8]}] No file mappings found for portfolio {self.task.portfolio_uuid}")
                return None

            components = {
                "strategies": [],
                "sizers": [],
                "selectors": [],
                "risk_managers": [],
                "analyzers": []
            }

            # FILE_TYPES 值到组件分类的映射
            type_mapping = {
                FILE_TYPES.STRATEGY.value: "strategies",
                FILE_TYPES.SIZER.value: "sizers",
                FILE_TYPES.SELECTOR.value: "selectors",
                FILE_TYPES.RISKMANAGER.value: "risk_managers",
                FILE_TYPES.ANALYZER.value: "analyzers",
            }

            for mapping in mappings:
                # 使用 mapping.type (不是 component_type)
                component_type = mapping.type
                category = type_mapping.get(component_type)
                if category and category in components:
                    components[category].append({
                        "file_id": mapping.file_id,
                        "mapping_uuid": mapping.uuid,
                    })

            print(f"[{self.task.task_uuid[:8]}] Components loaded: strategies={len(components['strategies'])}, "
                  f"sizers={len(components['sizers'])}, risk_managers={len(components['risk_managers'])}")

            return components

        except Exception as e:
            print(f"[{self.task.task_uuid[:8]}] Failed to get portfolio components: {e}")
            import traceback
            traceback.print_exc()
            return None

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
            # 从引擎获取Portfolio（portfolios 是 list）
            portfolios = getattr(self._engine, 'portfolios', [])
            portfolio = None

            # 在列表中查找匹配的 portfolio
            for p in portfolios:
                if getattr(p, 'uuid', None) == self.task.portfolio_uuid:
                    portfolio = p
                    break

            # 如果没找到，使用第一个 portfolio
            if portfolio is None and portfolios:
                portfolio = portfolios[0]

            if portfolio:
                initial_cash = self.task.config.initial_cash
                final_cash = float(portfolio.cash) if hasattr(portfolio, 'cash') else initial_cash
                total_return = (final_cash - initial_cash) / initial_cash if initial_cash > 0 else 0
            else:
                total_return = 0.0
                initial_cash = self.task.config.initial_cash
                final_cash = initial_cash

            result = {
                "task_uuid": self.task.task_uuid,
                "initial_cash": initial_cash,
                "final_cash": final_cash,
                "total_return": total_return,
                "annual_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "total_signals": 0,
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
