# Upstream: backtest_cli.run_task(), BacktestProcessor.run()
# Downstream: EngineAssemblyService, PortfolioService, BacktestResultAggregator
# Role: 回测编排器，统一回测执行链路：加载→装配→运行→收集结果


import os
from datetime import datetime
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.libs import GLOG
from ginkgo.workers.backtest_worker.task_helpers import (
    load_portfolio_components,
    preflight_data_coverage,
    build_preflight_warning,
)


class OrchestratorResult:
    """编排器执行结果。"""

    def __init__(self, success: bool, error: str = "", data: Any = None):
        self.success = success
        self.error = error
        self.data = data or {}

    def is_success(self) -> bool:
        return self.success


@runtime_checkable
class BacktestUseCase(Protocol):
    """#6449: 回测应用用例层契约。

    整洁架构的应用层入口——把"从 task 编排一次回测"这一业务用例固化成结构契约，
    让 CLI / API / worker 通过统一入口调用，而非各自重复 config 解析、preflight、
    状态机更新。BacktestOrchestrator 是该 Protocol 的参考实现。

    Note: structural typing（鸭子类型）—— BacktestOrchestrator 无需显式继承，
    只要实现了 run_from_task 即自动满足。@runtime_checkable 让 isinstance 可用。
    """

    def run_from_task(
        self,
        task,
        config_snapshot: Optional[Dict] = None,
        progress_callback=None,
        timeout: Optional[float] = None,
    ) -> OrchestratorResult:
        """从 task 对象编排一次回测。

        封装：config 解析 → preflight 数据预检 → 标 running → 委派 run()。
        业务层报"事实"（success=False + 原因），由调用方（CLI）翻译为框架异常。
        """
        ...


class BacktestOrchestrator:
    """
    回测编排器。

    统一 CLI 和 Worker 的回测执行链路，消除重复编排逻辑。
    职责：加载 portfolio 元数据 → 装配引擎 → 运行 → 等待 → 收集结果。
    """

    def __init__(self, assembly_service, portfolio_service,
                 task_service, result_aggregator):
        self._assembly_service = assembly_service
        self._portfolio_service = portfolio_service
        self._task_service = task_service
        self._result_aggregator = result_aggregator

    def run_from_task(
        self,
        task,
        config_snapshot: Optional[Dict] = None,
        progress_callback=None,
        timeout: Optional[float] = None,
    ) -> OrchestratorResult:
        """#6449: 从 task 对象编排回测（应用用例层入口）。

        封装 config 解析 + preflight 数据预检 + 标 running + 委派 run()。
        """
        import json as _json
        from ginkgo.workers.backtest_worker.models import BacktestConfig

        # 1. 解析 config_snapshot → BacktestConfig
        #    收敛点：CLI/worker 不再各自 11 行重复构造，由 UseCase 层统一解析。
        if config_snapshot is None:
            config_snapshot = task.config_snapshot
        if isinstance(config_snapshot, str):
            config_snapshot = _json.loads(config_snapshot)
        config = BacktestConfig(
            start_date=config_snapshot.get("start_date", "2024-01-01"),
            end_date=config_snapshot.get("end_date", "2024-12-31"),
            initial_cash=config_snapshot.get("initial_cash", 100000),
            commission_rate=config_snapshot.get("commission_rate", 0.0003),
            slippage_rate=config_snapshot.get("slippage_rate", 0.0001),
            benchmark_return=config_snapshot.get("benchmark_return", 0.0),
            max_position_ratio=config_snapshot.get("max_position_ratio", 0.3),
            stop_loss_ratio=config_snapshot.get("stop_loss_ratio", 0.05),
            take_profit_ratio=config_snapshot.get("take_profit_ratio", 0.15),
            frequency=config_snapshot.get("frequency", "DAY"),
            analyzers=[],
        )

        # 2. preflight 数据预检（#6282 数据覆盖前置阻断）
        #    收敛点：CLI 不再各自跑 preflight + raise typer.Exit，
        #    UseCase 层报业务事实（success=False + 原因），调用方翻译为框架异常。
        preflight_report = preflight_data_coverage(
            task.portfolio_id,
            str(config.start_date),
            str(config.end_date),
        )
        warning = build_preflight_warning(
            preflight_report,
            str(config.start_date),
            str(config.end_date),
        )
        if warning:
            if self._task_service is not None:
                self._task_service.update_status(task.uuid, "failed")
            return OrchestratorResult(
                success=False,
                error=f"preflight blocked: data coverage insufficient "
                      f"({warning[:200]})",
            )

        # 3. 标 running（用例契约：状态机更新由 UseCase 层管，调用方不必手动标）
        if self._task_service is not None:
            self._task_service.update_status(task.uuid, "running")

        # 4. 委派 run()
        result = self.run(
            task_id=task.uuid,
            config=config,
            portfolio_id=task.portfolio_id,
            progress_callback=progress_callback,
            timeout=timeout,
        )

        # #6449: 成功路径回填 backtest_end_date 给调用方（CLI FINALIZING 进度用）。
        # aggregator 只把它写进 DB task 表、不进返回 dict；config 解析下沉到本层后
        # 调用方拿不到 config.end_date，故由用例层在此回填，对齐 master 的
        # str(config.end_date) 语义。
        if result.is_success() and isinstance(result.data, dict):
            result.data["backtest_end_date"] = str(config.end_date)
        return result

    def run(self, task_id: str, config, portfolio_id: str,
            timeout: Optional[float] = None,
            progress_callback=None) -> OrchestratorResult:
        """
        执行完整回测链路。

        Args:
            task_id: 回测任务 ID
            config: BacktestConfig 或等价配置对象
            portfolio_id: Portfolio UUID
            timeout: 等待引擎完成的最大秒数。None 时依次取环境变量
                GINKGO_BACKTEST_TIMEOUT、默认 3600s（#6483：使超时可配置）。

        Returns:
            OrchestratorResult
        """
        try:
            # #6483: timeout 可配置——None 时读 GINKGO_BACKTEST_TIMEOUT，再 fallback 3600
            if timeout is None:
                env_val = os.environ.get("GINKGO_BACKTEST_TIMEOUT")
                if env_val:
                    try:
                        timeout = float(env_val)
                    except ValueError:
                        GLOG.WARN(
                            f"invalid GINKGO_BACKTEST_TIMEOUT={env_val!r}, using 3600"
                        )
                        timeout = 3600.0
                else:
                    timeout = 3600.0
            # 1. 加载 portfolio 元数据（轻量，不绑定组件）
            portfolio_data = self._load_portfolio_metadata(portfolio_id)

            # 2. 加载组件映射
            components = self._load_components(portfolio_id)

            # 3. 装配引擎
            engine = self._assemble_engine(task_id, config, portfolio_id,
                                           portfolio_data, components, progress_callback)

            # 4. 运行引擎
            engine.start()

            # 5. 等待完成（#6483: 返回是否超时，供聚合层如实报告状态）
            timed_out = self._wait_for_engine(engine, timeout)

            # 6. 通知分析器
            if hasattr(engine, 'notify_analyzers_backtest_end'):
                engine.notify_analyzers_backtest_end()

            # 7. 收集结果
            agg_result = self._aggregate_results(
                task_id, portfolio_id, config, timed_out=timed_out,
                engine=engine,
            )

            # #6483: 超时返回 success=False，task_processor.run L107
            # `if not result.is_success(): raise` 据此自动标 FAILED，主流程零改动。
            if timed_out:
                return OrchestratorResult(
                    success=False,
                    error=(
                        "Backtest timed out: engine did not finish within the "
                        "wall-clock limit (data may be truncated)"
                    ),
                    data=agg_result.data if agg_result.is_success() else {},
                )

            return OrchestratorResult(
                success=True,
                data=agg_result.data if agg_result.is_success() else {},
            )

        except Exception as e:
            GLOG.ERROR(f"BacktestOrchestrator.run failed: {e}")
            if self._task_service:
                self._task_service.update_status(task_id, "failed",
                                                 error_message=str(e))
            return OrchestratorResult(success=False, error=str(e))

    def _load_portfolio_metadata(self, portfolio_id: str):
        """轻量加载 portfolio 元数据，不做组件绑定。"""
        result = self._portfolio_service.get(portfolio_id=portfolio_id)
        if not result.is_success() or not result.data:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        return result.data[0] if isinstance(result.data, list) else result.data

    def _load_components(self, portfolio_id: str) -> Dict:
        """加载 portfolio 组件映射（由 EngineAssemblyService 的 ComponentLoader 做实例化）。"""
        return load_portfolio_components(portfolio_id)

    def _assemble_engine(self, task_id, config, portfolio_id,
                         portfolio_data, components, progress_callback=None):
        """构建引擎装配参数并调用 EngineAssemblyService。"""
        from ginkgo.workers.backtest_worker.task_helpers import (
            build_engine_data,
            build_portfolio_config,
        )

        engine_data = build_engine_data(config, task_id=task_id)
        portfolio_config = build_portfolio_config(
            portfolio_id, portfolio_data, config.initial_cash
        )

        # 构建 portfolio mapping
        mapping = type("PortfolioMapping", (), {"portfolio_id": portfolio_id})()

        result = self._assembly_service.assemble_backtest_engine(
            engine_id=task_id,
            engine_data=engine_data,
            portfolio_mappings=[mapping],
            portfolio_configs={portfolio_id: portfolio_config},
            portfolio_components={portfolio_id: components},
            progress_callback=progress_callback,
        )

        if not result.success:
            raise RuntimeError(f"Engine assembly failed: {result.error}")

        return result.data

    def _wait_for_engine(self, engine, timeout: float) -> bool:
        """等待引擎主线程完成。

        Returns:
            True 表示引擎超时未完成（已被强制 stop）；False 表示正常结束。
            #6483: 调用方据此决定回测报 incomplete 还是 completed，避免超时被吞。
        """
        main_thread = getattr(engine, '_main_thread', None)
        if main_thread is None:
            return False
        if not main_thread.is_alive():
            return False
        main_thread.join(timeout=timeout)
        if main_thread.is_alive():
            GLOG.WARN(f"Engine did not complete within {timeout}s")
            engine.stop()
            main_thread.join(timeout=10.0)
            return True
        return False

    def _aggregate_results(self, task_id, portfolio_id, config,
                           timed_out: bool = False, engine=None):
        """汇总分析器结果。

        #6483: 超时不再静默标 completed——如实写 incomplete 并附 error_message，
        避免被墙钟超时截断的回测显示"已完成"。超时时 backtest_end_date 取
        引擎实际跑到的时间（engine.now），而非配置的谎言值。
        """
        backtest_start = None
        backtest_end = None
        if hasattr(config, 'start_date') and config.start_date:
            try:
                backtest_start = datetime.strptime(str(config.start_date)[:10], "%Y-%m-%d")
            except ValueError:
                GLOG.DEBUG(f"handled error")
                pass
        if hasattr(config, 'end_date') and config.end_date:
            try:
                backtest_end = datetime.strptime(str(config.end_date)[:10], "%Y-%m-%d")
            except ValueError:
                GLOG.DEBUG(f"handled error")
                pass

        if timed_out:
            status = "incomplete"
            error_message = (
                "Backtest timed out: engine did not finish within the "
                "wall-clock limit (data may be truncated)"
            )
            # #6483: end_date 取引擎实际跑到的时间，而非配置的 end_date（后者会让
            # 用户误以为跑满整个区间）。engine.now 是 @property（见
            # arch_engine_now_property_exists），防御性读取防异常引擎。
            if engine is not None and hasattr(engine, 'now'):
                try:
                    engine_now = engine.now
                    if isinstance(engine_now, datetime):
                        backtest_end = engine_now
                except Exception:
                    GLOG.DEBUG("handled error reading engine.now on timeout")
        else:
            status = "completed"
            error_message = ""

        return self._result_aggregator.aggregate_and_save(
            task_id=task_id,
            portfolio_id=portfolio_id,
            engine_id=task_id,
            status=status,
            error_message=error_message,
            backtest_start_date=backtest_start,
            backtest_end_date=backtest_end,
        )
