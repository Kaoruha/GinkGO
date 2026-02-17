# Upstream: Backtest Engines (EngineHistoric, EngineLive)
# Downstream: BacktestTaskService (更新回测任务结果), AnalyzerService (读取分析器数据)
# Role: BacktestResultAggregator 回测结果汇总器在回测结束时汇总分析器结果写回BacktestTask

"""
Backtest Result Aggregator

回测结果汇总器，在回测结束时：
1. 从 ClickHouse 读取各分析器的最终结果
2. 汇总统计指标（夏普比率、最大回撤、胜率等）
3. 调用 BacktestTaskService 更新回测任务记录
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ginkgo.libs import GLOG, time_logger
from ginkgo.data.services.base_service import ServiceResult


class BacktestResultAggregator:
    """
    回测结果汇总器

    职责：
    - 在回测结束时被引擎调用
    - 从分析器服务读取各指标数据
    - 汇总计算最终结果
    - 更新 BacktestTask 记录

    使用示例:
    ```python
    aggregator = BacktestResultAggregator(
        analyzer_service=analyzer_service,
        backtest_task_service=backtest_task_service
    )

    result = aggregator.aggregate_and_save(
        task_id="BT_001",
        portfolio_id="portfolio_001",
        engine_id="engine_001"
    )
    ```
    """

    # 分析器名称常量
    ANALYZER_NET_VALUE = "net_value"
    ANALYZER_MAX_DRAWDOWN = "max_drawdown"
    ANALYZER_SHARPE_RATIO = "sharpe_ratio"
    ANALYZER_ANNUAL_RETURN = "annualized_return"  # 注意：与analyzer.name保持一致
    ANALYZER_WIN_RATE = "win_rate"
    ANALYZER_VOLATILITY = "volatility"
    ANALYZER_PROFIT = "ProfitAna"  # 注意：Profit分析器的name是ProfitAna
    ANALYZER_SIGNAL_COUNT = "signal_count"

    def __init__(
        self,
        analyzer_service=None,
        backtest_task_service=None,
        signal_crud=None,
        order_crud=None
    ):
        """
        初始化汇总器

        Args:
            analyzer_service: 分析器服务（读取分析器数据）
            backtest_task_service: 回测任务服务（更新任务结果）
            signal_crud: Signal CRUD（统计信号数）
            order_crud: Order CRUD（统计订单数）
        """
        self._analyzer_service = analyzer_service
        self._backtest_task_service = backtest_task_service
        self._signal_crud = signal_crud
        self._order_crud = order_crud

    @time_logger
    def aggregate_and_save(
        self,
        task_id: str,
        portfolio_id: str,
        engine_id: str = "",
        status: str = "completed",
        error_message: str = "",
        duration_seconds: Optional[int] = None
    ) -> ServiceResult:
        """
        汇总分析器结果并保存到 BacktestTask

        Args:
            task_id: 回测任务ID
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            status: 回测状态 (completed/failed/stopped)
            error_message: 错误信息
            duration_seconds: 运行时长

        Returns:
            ServiceResult: 汇总结果
        """
        try:
            GLOG.INFO(f"Aggregating backtest results for task: {task_id}")

            # 1. 汇总各项指标
            metrics = self._aggregate_metrics(task_id, portfolio_id, engine_id)

            # 2. 统计业务数据
            stats = self._aggregate_stats(task_id, portfolio_id, engine_id)

            # 3. 更新 BacktestTask (任务应该在运行前已创建)
            result_fields = {
                "final_portfolio_value": metrics.get("final_portfolio_value", "0"),
                "total_pnl": metrics.get("total_pnl", "0"),
                "max_drawdown": metrics.get("max_drawdown", "0"),
                "sharpe_ratio": metrics.get("sharpe_ratio", "0"),
                "annual_return": metrics.get("annual_return", "0"),
                "win_rate": metrics.get("win_rate", "0"),
                "total_orders": stats.get("total_orders", 0),
                "total_signals": stats.get("total_signals", 0),
                "total_positions": stats.get("total_positions", 0),
                "total_events": stats.get("total_events", 0),
            }

            if self._backtest_task_service:
                update_result = self._backtest_task_service.update_status(
                    task_id=task_id,
                    status=status,
                    error_message=error_message,
                    **result_fields
                )

                if not update_result.is_success():
                    GLOG.ERROR(f"Failed to update backtest task: {update_result.error}")
                    # 不返回错误，允许汇总继续完成（任务可能未预先创建）
                    GLOG.WARN(f"Backtest task may not exist. Create it before running backtest.")

            GLOG.INFO(f"Backtest results saved for task: {task_id}")
            return ServiceResult.success({
                "task_id": task_id,
                "metrics": metrics,
                "stats": stats
            }, "Backtest results aggregated successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to aggregate backtest results: {e}")
            return ServiceResult.error(f"Failed to aggregate results: {str(e)}")

    def _get_dataframe(self, result) -> Any:
        """
        从 ServiceResult 中提取 DataFrame

        处理 ModelList 或 DataFrame 类型的返回值

        Args:
            result: ServiceResult 对象

        Returns:
            DataFrame 或 None
        """
        import pandas as pd

        if not result.is_success() or result.data is None:
            return None

        data = result.data

        # 如果已经是 DataFrame
        if isinstance(data, pd.DataFrame):
            return data

        # 如果是 ModelList，使用其 to_dataframe() 方法
        if hasattr(data, 'to_dataframe') and callable(data.to_dataframe):
            return data.to_dataframe()

        # 如果是空列表
        if isinstance(data, list) and len(data) == 0:
            return pd.DataFrame()

        return None

    def _aggregate_metrics(
        self,
        task_id: str,
        portfolio_id: str,
        engine_id: str
    ) -> Dict[str, str]:
        """
        汇总分析器指标

        Args:
            task_id: 任务ID
            portfolio_id: 投资组合ID
            engine_id: 引擎ID

        Returns:
            Dict[str, str]: 指标字典
        """
        metrics = {
            "final_portfolio_value": "0",
            "total_pnl": "0",
            "max_drawdown": "0",
            "sharpe_ratio": "0",
            "annual_return": "0",
            "win_rate": "0",
        }

        if not self._analyzer_service:
            GLOG.DEBUG("Analyzer service not available, returning default metrics")
            return metrics

        try:
            # 获取净值数据 - 用于计算最终资产和总盈亏
            net_value_result = self._analyzer_service.get_by_run_id(
                run_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=self.ANALYZER_NET_VALUE,
                limit=10000
            )

            df = self._get_dataframe(net_value_result)
            if df is not None and len(df) > 0:
                # 最终净值
                final_value = float(df['value'].iloc[-1])
                metrics["final_portfolio_value"] = str(final_value)

                # 总盈亏 = 最终净值 - 初始净值
                initial_value = float(df['value'].iloc[0])
                total_pnl = final_value - initial_value
                metrics["total_pnl"] = str(total_pnl)

            # 获取最大回撤
            drawdown_result = self._analyzer_service.get_by_run_id(
                run_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=self.ANALYZER_MAX_DRAWDOWN,
                limit=10000
            )

            df = self._get_dataframe(drawdown_result)
            if df is not None and len(df) > 0:
                # 最大回撤是最小的（负值最大的）回撤值
                max_drawdown = abs(float(df['value'].min()))
                metrics["max_drawdown"] = str(max_drawdown)

            # 获取夏普比率（取最后值）
            sharpe_result = self._analyzer_service.get_by_run_id(
                run_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=self.ANALYZER_SHARPE_RATIO,
                limit=1000
            )

            df = self._get_dataframe(sharpe_result)
            if df is not None and len(df) > 0:
                sharpe = float(df['value'].iloc[-1])
                metrics["sharpe_ratio"] = str(sharpe)

            # 获取年化收益
            annual_return_result = self._analyzer_service.get_by_run_id(
                run_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=self.ANALYZER_ANNUAL_RETURN,
                limit=1000
            )

            df = self._get_dataframe(annual_return_result)
            if df is not None and len(df) > 0:
                annual_return = float(df['value'].iloc[-1])
                metrics["annual_return"] = str(annual_return)

            # 获取胜率
            win_rate_result = self._analyzer_service.get_by_run_id(
                run_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=self.ANALYZER_WIN_RATE,
                limit=1000
            )

            df = self._get_dataframe(win_rate_result)
            if df is not None and len(df) > 0:
                win_rate = float(df['value'].iloc[-1])
                metrics["win_rate"] = str(win_rate)

        except Exception as e:
            GLOG.ERROR(f"Error aggregating metrics: {e}")

        return metrics

    def _aggregate_stats(
        self,
        task_id: str,
        portfolio_id: str,
        engine_id: str
    ) -> Dict[str, int]:
        """
        汇总业务统计数据

        Args:
            task_id: 任务ID
            portfolio_id: 投资组合ID
            engine_id: 引擎ID

        Returns:
            Dict[str, int]: 统计字典
        """
        stats = {
            "total_orders": 0,
            "total_signals": 0,
            "total_positions": 0,
            "total_events": 0,
        }

        # 统计信号数
        if self._signal_crud:
            try:
                count_result = self._signal_crud.count(
                    filters={"run_id": task_id, "portfolio_id": portfolio_id}
                )
                stats["total_signals"] = count_result or 0
            except Exception as e:
                GLOG.DEBUG(f"Could not count signals: {e}")

        # 统计订单数
        if self._order_crud:
            try:
                count_result = self._order_crud.count(
                    filters={"run_id": task_id, "portfolio_id": portfolio_id}
                )
                stats["total_orders"] = count_result or 0
            except Exception as e:
                GLOG.DEBUG(f"Could not count orders: {e}")

        return stats

    def get_net_value_data(
        self,
        task_id: str,
        portfolio_id: str
    ) -> Dict[str, List]:
        """
        获取净值曲线数据（用于前端图表）

        Args:
            task_id: 任务ID
            portfolio_id: 投资组合ID

        Returns:
            Dict with 'strategy' and 'benchmark' data lists
        """
        result = {
            "strategy": [],
            "benchmark": []
        }

        if not self._analyzer_service:
            return result

        try:
            net_value_result = self._analyzer_service.get_by_run_id(
                run_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=self.ANALYZER_NET_VALUE,
                limit=10000
            )

            df = self._get_dataframe(net_value_result)
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    timestamp = row.get('timestamp') or row.get('business_timestamp')
                    if timestamp:
                        if isinstance(timestamp, str):
                            time_str = timestamp[:10]  # YYYY-MM-DD
                        else:
                            time_str = timestamp.strftime('%Y-%m-%d')

                        result["strategy"].append({
                            "time": time_str,
                            "value": float(row['value'])
                        })

        except Exception as e:
            GLOG.ERROR(f"Error getting net value data: {e}")

        return result
