# Upstream: backtest_cli.run_task(), BacktestProcessor.run()
# Downstream: EngineAssemblyService, PortfolioService, BacktestResultAggregator
# Role: 回测编排器，统一回测执行链路：加载→装配→运行→收集结果


from datetime import datetime
from typing import Any, Dict, Optional

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.libs import GLOG
from ginkgo.workers.backtest_worker.task_helpers import (
    load_portfolio_components,
)


class OrchestratorResult:
    """编排器执行结果。"""

    def __init__(self, success: bool, error: str = "", data: Any = None):
        self.success = success
        self.error = error
        self.data = data or {}

    def is_success(self) -> bool:
        return self.success


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

    def run(self, task_id: str, config, portfolio_id: str,
            timeout: float = 3600.0) -> OrchestratorResult:
        """
        执行完整回测链路。

        Args:
            task_id: 回测任务 ID
            config: BacktestConfig 或等价配置对象
            portfolio_id: Portfolio UUID
            timeout: 等待引擎完成的最大秒数

        Returns:
            OrchestratorResult
        """
        try:
            # 1. 加载 portfolio 元数据（轻量，不绑定组件）
            portfolio_data = self._load_portfolio_metadata(portfolio_id)

            # 2. 加载组件映射
            components = self._load_components(portfolio_id)

            # 3. 装配引擎
            engine = self._assemble_engine(task_id, config, portfolio_id,
                                           portfolio_data, components)

            # 4. 运行引擎
            engine.start()

            # 5. 等待完成
            self._wait_for_engine(engine, timeout)

            # 6. 通知分析器
            if hasattr(engine, 'notify_analyzers_backtest_end'):
                engine.notify_analyzers_backtest_end()

            # 7. 收集结果
            agg_result = self._aggregate_results(
                task_id, portfolio_id, config,
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
                         portfolio_data, components):
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
        )

        if not result.success:
            raise RuntimeError(f"Engine assembly failed: {result.error}")

        return result.data

    def _wait_for_engine(self, engine, timeout: float):
        """等待引擎主线程完成。"""
        main_thread = getattr(engine, '_main_thread', None)
        if main_thread is None:
            return
        if not main_thread.is_alive():
            return
        main_thread.join(timeout=timeout)
        if main_thread.is_alive():
            GLOG.WARN(f"Engine did not complete within {timeout}s")
            engine.stop()
            main_thread.join(timeout=10.0)

    def _aggregate_results(self, task_id, portfolio_id, config):
        """汇总分析器结果。"""
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

        return self._result_aggregator.aggregate_and_save(
            task_id=task_id,
            portfolio_id=portfolio_id,
            engine_id=task_id,
            status="completed",
            backtest_start_date=backtest_start,
            backtest_end_date=backtest_end,
        )
