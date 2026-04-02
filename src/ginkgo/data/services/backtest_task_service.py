# Upstream: CLI Commands (ginkgo backtest list/run/delete)、API Server (回测任务API)
# Downstream: BaseService (继承提供服务基础能力)、BacktestTaskCRUD (回测任务CRUD)、AnalyzerService (分析服务)
# Role: BacktestTaskService回测任务服务提供回测任务管理功能支持交易系统功能和组件集成提供完整业务支持

"""
Backtest Task Service

回测任务业务服务，提供：
- 回测任务 CRUD
- 任务状态管理
- 任务结果查询
- 与引擎、投资组合的关联管理
"""

import time
import json
from typing import List, Union, Any, Optional, Dict
import pandas as pd
from datetime import datetime

from ginkgo.libs import cache_with_expiration, retry, GLOG
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.interfaces.kafka_topics import KafkaTopics


class BacktestTaskService(BaseService):
    """
    回测任务服务

    管理回测任务的完整生命周期：
    - 创建任务
    - 执行任务
    - 查询结果
    - 删除任务
    """

    def __init__(self, crud_repo, analyzer_service=None, engine_service=None, portfolio_service=None):
        """
        初始化服务

        Args:
            crud_repo: BacktestTaskCRUD 实例
            analyzer_service: 分析服务（可选，用于获取净值数据等）
            engine_service: 引擎服务（可选，用于关联引擎）
            portfolio_service: 投资组合服务（可选，用于关联投资组合）
        """
        super().__init__(
            crud_repo=crud_repo,
            analyzer_service=analyzer_service,
            engine_service=engine_service,
            portfolio_service=portfolio_service
        )
        self._analyzer_service = analyzer_service
        self._engine_service = engine_service
        self._portfolio_service = portfolio_service
        GLOG.set_log_category("component")

    def get(self, run_id: str = None, engine_id: str = None, portfolio_id: str = None,
            status: str = None, task_id: str = None) -> ServiceResult:
        """
        获取回测任务

        Args:
            run_id: 运行会话ID
            engine_id: 引擎ID
            portfolio_id: 投资组合ID
            status: 任务状态
            task_id: 向后兼容参数（等同于 run_id）

        Returns:
            ServiceResult: 查询结果
        """
        try:
            filters = {"is_del": False}

            # 支持 run_id 或向后兼容的 task_id
            actual_run_id = run_id or task_id
            if actual_run_id:
                filters["run_id"] = actual_run_id
            if engine_id:
                filters["engine_id"] = engine_id
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id
            if status:
                filters["status"] = status

            result = self._crud_repo.find(filters=filters, as_dataframe=False)

            return ServiceResult.success(result, f"Successfully retrieved backtest tasks")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest tasks: {str(e)}")

    def get_by_id(self, backtest_id: str) -> ServiceResult:
        """
        通过 ID 获取单个任务（支持 uuid 或 run_id）

        Args:
            backtest_id: 任务标识（可以是 uuid 或 run_id）

        Returns:
            ServiceResult: 查询结果
        """
        try:
            # 先尝试用 uuid 查询
            result = self._crud_repo.get_by_uuid(backtest_id)
            if result is None:
                # 如果 uuid 查不到，尝试用 run_id 查询
                result = self._crud_repo.get_by_run_id(backtest_id)
            if result is None:
                return ServiceResult.error(f"Backtest task not found: {backtest_id}")
            return ServiceResult.success(result, f"Successfully retrieved backtest task")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest task: {str(e)}")

    def get_by_run_id(self, run_id: str) -> ServiceResult:
        """
        通过 run_id 获取单个任务

        Args:
            run_id: 运行会话ID

        Returns:
            ServiceResult: 查询结果
        """
        try:
            result = self._crud_repo.get_by_run_id(run_id)
            if result is None:
                return ServiceResult.error(f"Backtest task not found: {run_id}")
            return ServiceResult.success(result, f"Successfully retrieved backtest task")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest task: {str(e)}")

    # 向后兼容
    def get_by_task_id(self, task_id: str) -> ServiceResult:
        """向后兼容方法，调用 get_by_run_id"""
        return self.get_by_run_id(task_id)

    def list(self, page: int = 0, page_size: int = 20, engine_id: str = None,
             portfolio_id: str = None, status: str = None) -> ServiceResult:
        """
        获取回测任务列表

        Args:
            page: 页码
            page_size: 每页数量
            engine_id: 引擎ID筛选
            portfolio_id: 投资组合ID筛选
            status: 状态筛选

        Returns:
            ServiceResult: 列表结果
        """
        try:
            result = self._crud_repo.get_tasks_page_filtered(
                engine_id=engine_id,
                portfolio_id=portfolio_id,
                status=status,
                page=page,
                page_size=page_size
            )

            # 获取总数（应用相同的筛选条件）
            count_filters = {"is_del": False}
            if status:
                count_filters["status"] = status
            if engine_id:
                count_filters["engine_id"] = engine_id
            if portfolio_id:
                count_filters["portfolio_id"] = portfolio_id

            total = self._crud_repo.count(filters=count_filters)

            return ServiceResult.success({
                "data": result,
                "total": total,
                "page": page,
                "page_size": page_size
            }, f"Successfully retrieved backtest task list")

        except Exception as e:
            return ServiceResult.error(f"Failed to list backtest tasks: {str(e)}")

    @retry(max_try=3)
    def create(self, name: str = "", engine_id: str = "", portfolio_id: str = "",
               config_snapshot: dict = None, **kwargs) -> ServiceResult:
        """
        创建回测任务

        Args:
            name: 任务名称（可选，用户可读标识）
            engine_id: 所属引擎ID
            portfolio_id: 关联投资组合ID
            config_snapshot: 配置快照
            **kwargs: 其他参数

        Returns:
            ServiceResult: 创建结果
        """
        try:
            # 创建任务 (task_id 自动等于 uuid)
            task_data = {
                "name": name,
                "engine_id": engine_id,
                "portfolio_id": portfolio_id,
                "config_snapshot": json.dumps(config_snapshot or {}),
                **kwargs
            }

            task = self._crud_repo.create(**task_data)

            GLOG.INFO(f"Created backtest task: {task.uuid[:8]}...")

            return ServiceResult.success(task, f"Backtest task created successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to create backtest task: {e}")
            return ServiceResult.error(f"Failed to create backtest task: {str(e)}")

    @retry(max_try=3)
    def update(self, uuid: str, **updates) -> ServiceResult:
        """
        更新回测任务

        Args:
            uuid: 任务 UUID
            **updates: 更新字段

        Returns:
            ServiceResult: 更新结果
        """
        try:
            # 检查任务是否存在
            existing = self._crud_repo.get_by_uuid(uuid)
            if not existing:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 执行更新
            updated_count = self._crud_repo.modify(filters={"uuid": uuid}, updates=updates)

            if updated_count == 0:
                return ServiceResult.error(f"Failed to update backtest task: {uuid}")

            GLOG.INFO(f"Updated backtest task: {uuid[:8]}...")

            return ServiceResult.success({"uuid": uuid, "updated_fields": list(updates.keys())},
                                         f"Backtest task updated successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to update backtest task {uuid[:8]}...: {e}")
            return ServiceResult.error(f"Failed to update backtest task: {str(e)}")

    @retry(max_try=3)
    def update_status(self, uuid: str, status: str, error_message: str = "",
                      **result_fields) -> ServiceResult:
        """
        更新任务状态

        Args:
            uuid: 任务标识（可以是 uuid 或 run_id）
            status: 新状态 (created/pending/running/completed/failed/stopped)
            error_message: 错误信息
            **result_fields: 结果字段

        Returns:
            ServiceResult: 更新结果
        """
        try:
            valid_statuses = ["created", "pending", "running", "completed", "failed", "stopped"]
            if status not in valid_statuses:
                return ServiceResult.error(f"Invalid status: {status}")

            # 查找任务，支持 uuid 或 run_id
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_run_id(uuid)
            if not task:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 使用真实的 uuid 更新
            real_uuid = task.uuid
            updated_count = self._crud_repo.update_task_status(
                uuid=real_uuid,
                status=status,
                error_message=error_message,
                **result_fields
            )

            if updated_count == 0:
                return ServiceResult.error(f"Backtest task not found: {real_uuid}")

            GLOG.INFO(f"Updated task {real_uuid[:8]}... status to: {status}")

            return ServiceResult.success({"uuid": real_uuid, "run_id": task.run_id, "status": status},
                                         f"Task status updated to {status}")

        except Exception as e:
            GLOG.ERROR(f"Failed to update task status: {e}")
            return ServiceResult.error(f"Failed to update task status: {str(e)}")

    @retry(max_try=3)
    def delete(self, uuid: str) -> ServiceResult:
        """
        删除回测任务（软删除）

        Args:
            uuid: 任务 UUID

        Returns:
            ServiceResult: 删除结果
        """
        try:
            # 检查任务是否存在
            existing = self._crud_repo.get_by_uuid(uuid)
            if not existing:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 执行软删除
            self._crud_repo.soft_remove(filters={"uuid": uuid})

            GLOG.INFO(f"Deleted backtest task: {uuid[:8]}...")

            return ServiceResult.success({"uuid": uuid}, f"Backtest task deleted successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to delete backtest task {uuid[:8]}...: {e}")
            return ServiceResult.error(f"Failed to delete backtest task: {str(e)}")

    def get_statistics(self) -> ServiceResult:
        """
        获取回测任务统计信息

        Returns:
            ServiceResult: 统计结果
        """
        try:
            total = self._crud_repo.count(filters={"is_del": False})
            created = self._crud_repo.count(filters={"status": "created", "is_del": False})
            pending = self._crud_repo.count(filters={"status": "pending", "is_del": False})
            running = self._crud_repo.count(filters={"status": "running", "is_del": False})
            completed = self._crud_repo.count(filters={"status": "completed", "is_del": False})
            failed = self._crud_repo.count(filters={"status": "failed", "is_del": False})
            stopped = self._crud_repo.count(filters={"status": "stopped", "is_del": False})

            return ServiceResult.success({
                "total": total,
                "created": created,
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "stopped": stopped
            }, f"Statistics retrieved successfully")

        except Exception as e:
            return ServiceResult.error(f"Failed to get statistics: {str(e)}")

    def get_netvalue_data(self, task_id: str, portfolio_id: str = "") -> ServiceResult:
        """
        获取任务的净值曲线数据

        Args:
            task_id: 任务ID
            portfolio_id: 投资组合ID（可选）

        Returns:
            ServiceResult: 净值数据
        """
        try:
            from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

            # 使用汇总器获取净值数据
            aggregator = BacktestResultAggregator(
                analyzer_service=self._analyzer_service
            )

            result = aggregator.get_net_value_data(task_id, portfolio_id)
            return ServiceResult.success(result, "Net value data retrieved")

        except Exception as e:
            return ServiceResult.error(f"Failed to get net value data: {str(e)}")

    def compare(self, task_ids: List[str]) -> ServiceResult:
        """
        对比多个回测任务

        Args:
            task_ids: 任务ID列表

        Returns:
            ServiceResult: 对比结果
        """
        try:
            if not task_ids or len(task_ids) < 2:
                return ServiceResult.error("At least 2 tasks required for comparison")

            tasks = []
            for task_id in task_ids:
                task = self._crud_repo.get_by_uuid(task_id)
                if task:
                    tasks.append(task)

            if len(tasks) < 2:
                return ServiceResult.error("Not enough valid tasks found")

            # 构建对比数据
            comparison = {
                "task_ids": task_ids,
                "metrics": {}
            }

            # 提取指标
            metric_fields = ["total_pnl", "max_drawdown", "sharpe_ratio", "annual_return", "win_rate"]
            for field in metric_fields:
                comparison["metrics"][field] = {}
                for task in tasks:
                    value = getattr(task, field, "0")
                    comparison["metrics"][field][task.uuid] = value

            return ServiceResult.success(comparison, "Comparison completed")

        except Exception as e:
            GLOG.ERROR(f"Failed to compare tasks: {e}")
            return ServiceResult.error(f"Failed to compare tasks: {str(e)}")

    def exists(self, run_id: str = None, uuid: str = None, task_id: str = None) -> ServiceResult:
        """
        检查任务是否存在

        Args:
            run_id: 运行会话ID
            uuid: 任务 UUID
            task_id: 向后兼容参数（等同于 run_id）

        Returns:
            ServiceResult: 存在性检查结果
        """
        try:
            if uuid:
                exists = self._crud_repo.exists(filters={"uuid": uuid, "is_del": False})
            elif run_id or task_id:
                actual_run_id = run_id or task_id
                exists = self._crud_repo.exists(filters={"run_id": actual_run_id, "is_del": False})
            else:
                return ServiceResult.error("run_id or uuid is required")

            return ServiceResult.success({"exists": exists}, "Existence check completed")

        except Exception as e:
            return ServiceResult.error(f"Failed to check existence: {str(e)}")

    def update_progress(self, uuid: str, progress: float = None,
                        current_stage: str = None, current_date: str = None) -> ServiceResult:
        """
        更新任务进度（用于SSE实时推送）

        Args:
            uuid: 任务标识（可以是 uuid 或 run_id）
            progress: 进度百分比 0-100
            current_stage: 当前阶段 (DATA_PREPARING/ENGINE_BUILDING/RUNNING/FINALIZING)
            current_date: 当前处理的业务日期

        Returns:
            ServiceResult: 更新结果
        """
        try:
            updates = {}
            if progress is not None:
                updates["progress"] = int(min(100, max(0, progress)))
            if current_stage is not None:
                updates["current_stage"] = current_stage
            if current_date is not None:
                updates["current_date"] = current_date

            if not updates:
                return ServiceResult.error("No progress fields to update")

            # 查找任务，支持 uuid 或 run_id
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_run_id(uuid)
            if not task:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 使用真实的 uuid 更新
            real_uuid = task.uuid
            updated_count = self._crud_repo.modify(
                filters={"uuid": real_uuid},
                updates=updates
            )

            if updated_count is None or updated_count == 0:
                return ServiceResult.error(f"Backtest task not found: {real_uuid}")

            return ServiceResult.success({
                "uuid": real_uuid,
                "run_id": task.run_id,
                "progress": updates.get("progress"),
                "current_stage": updates.get("current_stage"),
                "current_date": updates.get("current_date")
            }, f"Task progress updated")

        except Exception as e:
            GLOG.ERROR(f"Failed to update task progress: {e}")
            return ServiceResult.error(f"Failed to update task progress: {str(e)}")

    def health_check(self) -> ServiceResult:
        """
        服务健康检查

        Returns:
            ServiceResult: 健康状态
        """
        try:
            total = self._crud_repo.count()

            return ServiceResult.success({
                "status": "healthy",
                "total_tasks": total
            }, "BacktestTaskService is healthy")

        except Exception as e:
            return ServiceResult.error(f"Health check failed: {str(e)}")

    # ===== 任务控制方法 =====

    def start_task(self, uuid: str, portfolio_uuid: str = None, name: str = None,
                   start_date: str = "", end_date: str = "",
                   initial_cash: float = 100000.0,
                   analyzers: list = None) -> ServiceResult:
        """
        启动回测任务（发送到Kafka队列）

        状态机规则：只能启动 completed/stopped/failed 状态的任务

        重新运行时：
        1. 删除该 run_id 的所有旧数据：
           - signals (信号)
           - orders (订单)
           - positions (持仓)
           - position_records (持仓记录)
           - analyzer_records (分析器记录)
           - order_records (订单状态变更历史)
           - transfer_records (转账记录 - ClickHouse)
           - transfers (转账 - MySQL)
           - signal_trackers (信号追踪器)
        2. run_id 保持不变
        3. 发送启动命令到 Kafka

        Args:
            uuid: 任务标识（可以是 uuid 或 run_id）
            portfolio_uuid: 投资组合UUID
            name: 任务名称
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            analyzers: 分析器列表

        Returns:
            ServiceResult: 启动结果
        """
        try:
            # 获取任务信息（支持 uuid 或 run_id）
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_run_id(uuid)
            if not task:
                return ServiceResult.error("Backtest task not found")

            # 状态机检查：只能启动已完成、已停止、失败的任务
            startable_states = ["completed", "stopped", "failed"]
            if task.status not in startable_states:
                return ServiceResult.error(
                    f"Cannot start task with status '{task.status}'. "
                    f"Task must be in one of: {', '.join(startable_states)}"
                )

            # ========== 重新运行：删除旧数据 ==========
            from ginkgo.data.containers import container
            run_id = task.run_id

            GLOG.INFO(f"Cleaning old data for run_id: {run_id[:8]}...")

            # 删除旧信号
            try:
                signal_crud = container.cruds.signal()
                signal_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old signals")
            except Exception as e:
                GLOG.WARN(f"Failed to delete signals: {e}")

            # 删除旧订单
            try:
                order_crud = container.cruds.order()
                order_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old orders")
            except Exception as e:
                GLOG.WARN(f"Failed to delete orders: {e}")

            # 删除旧持仓
            try:
                position_crud = container.cruds.position()
                position_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old positions")
            except Exception as e:
                GLOG.WARN(f"Failed to delete positions: {e}")

            # 删除旧持仓记录
            try:
                position_record_crud = container.cruds.position_record()
                position_record_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old position records")
            except Exception as e:
                GLOG.WARN(f"Failed to delete position records: {e}")

            # 删除旧分析器记录
            try:
                analyzer_crud = container.cruds.analyzer_record()
                analyzer_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old analyzer records")
            except Exception as e:
                GLOG.WARN(f"Failed to delete analyzer records: {e}")

            # 删除旧订单记录（订单状态变更历史）
            try:
                order_record_crud = container.cruds.order_record()
                order_record_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old order records")
            except Exception as e:
                GLOG.WARN(f"Failed to delete order records: {e}")

            # 删除旧转账记录
            try:
                transfer_record_crud = container.cruds.transfer_record()
                transfer_record_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old transfer records")
            except Exception as e:
                GLOG.WARN(f"Failed to delete transfer records: {e}")

            # 删除旧转账（MySQL）
            try:
                transfer_crud = container.cruds.transfer()
                transfer_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old transfers")
            except Exception as e:
                GLOG.WARN(f"Failed to delete transfers: {e}")

            # 删除旧信号追踪器
            try:
                signal_tracker_crud = container.cruds.signal_tracker()
                signal_tracker_crud.remove(filters={"run_id": run_id})
                GLOG.DEBUG("Deleted old signal trackers")
            except Exception as e:
                GLOG.WARN(f"Failed to delete signal trackers: {e}")

            # 发送启动命令到Kafka（run_id 保持不变）
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            real_uuid = task.uuid  # 用于更新状态

            # 如果没有提供日期，使用数据库中的日期
            if not start_date and task.backtest_start_date:
                start_date = task.backtest_start_date.strftime("%Y-%m-%d")
            if not end_date and task.backtest_end_date:
                end_date = task.backtest_end_date.strftime("%Y-%m-%d")

            # 先更新状态为 pending，确保 Worker 查询时能看到正确的状态
            status_result = self.update_status(real_uuid, status="pending")
            if not status_result.is_success():
                return ServiceResult.error(f"Failed to update task status to pending: {status_result.error}")

            GLOG.DEBUG(f"Updated task {real_uuid} status to pending")

            producer = GinkgoProducer()
            assignment = {
                "task_uuid": run_id,  # run_id 保持不变
                "portfolio_uuid": portfolio_uuid or task.portfolio_id,
                "name": name or task.name or f"backtest_{run_id[:8]}",
                "command": "start",
                "config": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "initial_cash": initial_cash,
                    "analyzers": analyzers or [],
                }
            }

            producer.send(KafkaTopics.BACKTEST_ASSIGNMENTS, assignment)
            producer.flush(timeout=2.0)
            producer.close()

            GLOG.INFO(f"Started backtest task with run_id: {run_id}")
            return ServiceResult.success({"uuid": real_uuid, "run_id": run_id}, "Backtest task started")

        except Exception as e:
            GLOG.ERROR(f"Failed to start backtest task {uuid}: {e}")
            return ServiceResult.error(f"Failed to start backtest task: {str(e)}")

    def stop_task(self, uuid: str) -> ServiceResult:
        """
        停止回测任务（发送停止命令到Kafka）

        状态机规则：只能停止 running 状态的任务

        Args:
            uuid: 任务标识（可以是 uuid 或 run_id）

        Returns:
            ServiceResult: 停止结果
        """
        try:
            # 获取任务信息（支持 uuid 或 run_id）
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_run_id(uuid)
            if not task:
                return ServiceResult.error("Backtest task not found")

            # 状态机检查：只能停止运行中的任务
            if task.status != "running":
                return ServiceResult.error(
                    f"Cannot stop task with status '{task.status}'. "
                    f"Only running tasks can be stopped."
                )

            # 发送停止命令到Kafka（使用 run_id 作为任务标识）
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            real_uuid = task.uuid  # 用于更新状态
            run_id = task.run_id   # 任务标识
            producer = GinkgoProducer()
            assignment = {
                "task_uuid": run_id,  # 使用 run_id
                "command": "stop",
            }

            producer.send(KafkaTopics.BACKTEST_ASSIGNMENTS, assignment)
            producer.flush(timeout=2.0)
            producer.close()

            # 更新任务状态为stopped
            self.update_status(real_uuid, status="stopped")

            GLOG.INFO(f"Stopped backtest task: {run_id[:8]}...")
            return ServiceResult.success({"uuid": real_uuid, "run_id": run_id}, "Backtest task stopped")

        except Exception as e:
            GLOG.ERROR(f"Failed to stop backtest task: {e}")
            return ServiceResult.error(f"Failed to stop backtest task: {str(e)}")

    def cancel_task(self, uuid: str) -> ServiceResult:
        """
        取消回测任务（发送取消命令到Kafka）

        状态机规则：只能取消 created/pending 状态的任务（尚未开始执行的任务）

        Args:
            uuid: 任务标识（可以是 uuid 或 run_id）

        Returns:
            ServiceResult: 取消结果
        """
        try:
            # 获取任务信息（支持 uuid 或 run_id）
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_run_id(uuid)
            if not task:
                return ServiceResult.error("Backtest task not found")

            # 状态机检查：只能取消待调度或排队中的任务
            cancelable_states = ["created", "pending"]
            if task.status not in cancelable_states:
                return ServiceResult.error(
                    f"Cannot cancel task with status '{task.status}'. "
                    f"Only tasks in {', '.join(cancelable_states)} can be cancelled."
                )

            # 发送取消命令到Kafka（使用 run_id 作为任务标识）
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            real_uuid = task.uuid  # 用于更新状态
            run_id = task.run_id   # 任务标识
            producer = GinkgoProducer()
            assignment = {
                "task_uuid": run_id,  # 使用 run_id
                "command": "cancel",
            }

            producer.send(KafkaTopics.BACKTEST_ASSIGNMENTS, assignment)
            producer.flush(timeout=2.0)
            producer.close()

            # 更新任务状态为stopped
            self.update_status(real_uuid, status="stopped")

            GLOG.INFO(f"Cancelled backtest task: {run_id[:8]}...")
            return ServiceResult.success({"uuid": real_uuid, "run_id": run_id}, "Backtest task cancelled")

        except Exception as e:
            GLOG.ERROR(f"Failed to cancel backtest task: {e}")
            return ServiceResult.error(f"Failed to cancel backtest task: {str(e)}")


# 向后兼容别名
RunRecordService = BacktestTaskService
