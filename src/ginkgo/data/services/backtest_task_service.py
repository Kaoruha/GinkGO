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

from ginkgo.libs import cache_with_expiration, retry, time_logger, GLOG
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.base_service import BaseService, ServiceResult


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

    @time_logger
    @retry(max_try=3)
    def get(self, task_id: str = None, engine_id: str = None, portfolio_id: str = None,
            status: str = None) -> ServiceResult:
        """
        获取回测任务

        Args:
            task_id: 任务会话ID
            engine_id: 引擎ID
            portfolio_id: 投资组合ID
            status: 任务状态

        Returns:
            ServiceResult: 查询结果
        """
        try:
            filters = {"is_del": False}

            if task_id:
                filters["task_id"] = task_id
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

    @time_logger
    @retry(max_try=3)
    def get_by_id(self, uuid: str) -> ServiceResult:
        """
        通过 UUID 获取单个任务

        Args:
            uuid: 任务 UUID

        Returns:
            ServiceResult: 查询结果
        """
        try:
            result = self._crud_repo.get_by_uuid(uuid)
            if result is None:
                return ServiceResult.error(f"Backtest task not found: {uuid}")
            return ServiceResult.success(result, f"Successfully retrieved backtest task")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest task: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def get_by_task_id(self, task_id: str) -> ServiceResult:
        """
        通过 task_id 获取单个任务

        Args:
            task_id: 任务会话ID

        Returns:
            ServiceResult: 查询结果
        """
        try:
            result = self._crud_repo.get_task_by_task_id(task_id)
            if result is None:
                return ServiceResult.error(f"Backtest task not found: {task_id}")
            return ServiceResult.success(result, f"Successfully retrieved backtest task")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest task: {str(e)}")

    @time_logger
    @retry(max_try=3)
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

            # 获取总数
            total = self._crud_repo.count(filters={"is_del": False})

            return ServiceResult.success({
                "data": result,
                "total": total,
                "page": page,
                "page_size": page_size
            }, f"Successfully retrieved backtest task list")

        except Exception as e:
            return ServiceResult.error(f"Failed to list backtest tasks: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def create(self, task_id: str, engine_id: str = "", portfolio_id: str = "",
               config_snapshot: dict = None, **kwargs) -> ServiceResult:
        """
        创建回测任务

        Args:
            task_id: 任务会话ID
            engine_id: 所属引擎ID
            portfolio_id: 关联投资组合ID
            config_snapshot: 配置快照
            **kwargs: 其他参数

        Returns:
            ServiceResult: 创建结果
        """
        try:
            if not task_id:
                return ServiceResult.error("task_id is required")

            # 检查 task_id 是否已存在
            existing = self._crud_repo.get_task_by_task_id(task_id)
            if existing:
                return ServiceResult.error(f"Task with task_id '{task_id}' already exists")

            # 创建任务
            task_data = {
                "task_id": task_id,
                "engine_id": engine_id,
                "portfolio_id": portfolio_id,
                "start_time": datetime.now(),
                "status": "running",
                "config_snapshot": json.dumps(config_snapshot or {}),
                **kwargs
            }

            task = self._crud_repo.create(**task_data)

            GLOG.INFO(f"Created backtest task: {task_id}")

            return ServiceResult.success(task, f"Backtest task created successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to create backtest task: {e}")
            return ServiceResult.error(f"Failed to create backtest task: {str(e)}")

    @time_logger
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

            GLOG.INFO(f"Updated backtest task: {uuid}")

            return ServiceResult.success({"uuid": uuid, "updated_fields": list(updates.keys())},
                                         f"Backtest task updated successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to update backtest task {uuid}: {e}")
            return ServiceResult.error(f"Failed to update backtest task: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update_status(self, task_id: str, status: str, error_message: str = "",
                      **result_fields) -> ServiceResult:
        """
        更新任务状态

        Args:
            task_id: 任务会话ID
            status: 新状态 (running/completed/failed/stopped)
            error_message: 错误信息
            **result_fields: 结果字段

        Returns:
            ServiceResult: 更新结果
        """
        try:
            valid_statuses = ["running", "completed", "failed", "stopped"]
            if status not in valid_statuses:
                return ServiceResult.error(f"Invalid status: {status}")

            updated_count = self._crud_repo.update_task_status(
                task_id=task_id,
                status=status,
                error_message=error_message,
                **result_fields
            )

            if updated_count == 0:
                return ServiceResult.error(f"Backtest task not found: {task_id}")

            GLOG.INFO(f"Updated task {task_id} status to: {status}")

            return ServiceResult.success({"task_id": task_id, "status": status},
                                         f"Task status updated to {status}")

        except Exception as e:
            GLOG.ERROR(f"Failed to update task status: {e}")
            return ServiceResult.error(f"Failed to update task status: {str(e)}")

    @time_logger
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

            GLOG.INFO(f"Deleted backtest task: {uuid}")

            return ServiceResult.success({"uuid": uuid}, f"Backtest task deleted successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to delete backtest task {uuid}: {e}")
            return ServiceResult.error(f"Failed to delete backtest task: {str(e)}")

    @time_logger
    def get_statistics(self) -> ServiceResult:
        """
        获取回测任务统计信息

        Returns:
            ServiceResult: 统计结果
        """
        try:
            total = self._crud_repo.count(filters={"is_del": False})
            running = self._crud_repo.count(filters={"status": "running", "is_del": False})
            completed = self._crud_repo.count(filters={"status": "completed", "is_del": False})
            failed = self._crud_repo.count(filters={"status": "failed", "is_del": False})

            return ServiceResult.success({
                "total": total,
                "running": running,
                "completed": completed,
                "failed": failed
            }, f"Statistics retrieved successfully")

        except Exception as e:
            return ServiceResult.error(f"Failed to get statistics: {str(e)}")

    @time_logger
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

    @time_logger
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

    @time_logger
    def exists(self, task_id: str = None, uuid: str = None) -> ServiceResult:
        """
        检查任务是否存在

        Args:
            task_id: 任务会话ID
            uuid: 任务 UUID

        Returns:
            ServiceResult: 存在性检查结果
        """
        try:
            if uuid:
                exists = self._crud_repo.exists(filters={"uuid": uuid, "is_del": False})
            elif task_id:
                exists = self._crud_repo.exists(filters={"task_id": task_id, "is_del": False})
            else:
                return ServiceResult.error("task_id or uuid is required")

            return ServiceResult.success({"exists": exists}, "Existence check completed")

        except Exception as e:
            return ServiceResult.error(f"Failed to check existence: {str(e)}")

    @time_logger
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


# 向后兼容别名
RunRecordService = BacktestTaskService
