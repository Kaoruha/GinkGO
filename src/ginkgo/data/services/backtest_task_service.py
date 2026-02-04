# Upstream: API Server (回测任务管理API)、BacktestWorker (回测任务执行)
# Downstream: BaseService (继承提供服务基础能力)、BacktestTaskCRUD (回测任务CRUD)
# Role: BacktestTaskService回测任务管理服务提供任务CRUD和状态管理功能支持交易系统功能和组件集成提供完整业务支持


"""
Backtest Task Management Service

This service handles the business logic for managing backtest tasks,
including task creation, status tracking, progress updates, and result management.
"""

import json
from typing import List, Union, Any, Optional, Dict
import pandas as pd
from datetime import datetime

from ginkgo.libs import cache_with_expiration, retry, time_logger, GLOG
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.base_service import BaseService, ServiceResult


class BacktestTaskService(BaseService):
    """
    Backtest Task Management Service

    提供回测任务的完整业务逻辑：
    - 创建任务并初始化配置
    - 查询任务（支持状态、投资组合过滤）
    - 更新任务状态、进度、结果
    - 分配 Worker 并启动任务
    - 取消和删除任务
    """

    def __init__(self, crud_repo):
        """
        Initialize the service with its dependencies.

        Args:
            crud_repo: BacktestTask CRUD repository
        """
        super().__init__(crud_repo=crud_repo)

    # Standard interface methods
    @time_logger
    @retry(max_try=3)
    def get(self, uuid: str = None, state: str = None, portfolio_uuid: str = None) -> ServiceResult:
        """
        Get backtest task data

        Args:
            uuid: Task UUID
            state: Task state (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
            portfolio_uuid: Portfolio UUID

        Returns:
            ServiceResult: Query result with ModelList data
        """
        try:
            # Build filter conditions
            filters = {}
            if uuid:
                filters['uuid'] = uuid
            if state:
                filters['state'] = state
            if portfolio_uuid:
                filters['portfolio_uuid'] = portfolio_uuid

            # Execute query - always return ModelList
            result = self._crud_repo.find(filters=filters, as_dataframe=False)

            return ServiceResult.success(result, f"Successfully retrieved backtest task data")

        except Exception as e:
            GLOG.ERROR(f"Failed to get backtest task data: {str(e)}")
            return ServiceResult.error(f"Failed to get backtest task data: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def count(self, state: str = None, portfolio_uuid: str = None) -> ServiceResult:
        """
        Count backtest tasks

        Args:
            state: Task state filter
            portfolio_uuid: Portfolio UUID filter

        Returns:
            ServiceResult: Count result
        """
        try:
            filters = {}
            if state:
                filters['state'] = state
            if portfolio_uuid:
                filters['portfolio_uuid'] = portfolio_uuid

            count = self._crud_repo.count(filters=filters)

            return ServiceResult.success({"count": count}, f"Total backtest tasks: {count}")

        except Exception as e:
            return ServiceResult.error(f"Failed to count backtest tasks: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def create(
        self,
        name: str,
        portfolio_uuid: str,
        portfolio_name: str = None,
        config: dict = None,
        **kwargs
    ) -> ServiceResult:
        """
        Create a new backtest task

        Args:
            name: Task name
            portfolio_uuid: Portfolio UUID
            portfolio_name: Portfolio name (optional)
            config: Task configuration dictionary
            **kwargs: Additional task parameters

        Returns:
            ServiceResult: Created task
        """
        try:
            # Input validation
            if not name or not name.strip():
                return ServiceResult.error("任务名称不能为空")

            # Check if portfolio_uuid is provided
            if not portfolio_uuid:
                return ServiceResult.error("投资组合UUID不能为空")

            # Prepare task data
            task_data = {
                "name": name.strip(),
                "portfolio_uuid": portfolio_uuid,
                "portfolio_name": portfolio_name or "Unknown Portfolio",
                "state": "PENDING",
                "progress": 0.0,
                "config": json.dumps(config) if config else None,
                "created_at": datetime.utcnow(),
                **kwargs
            }

            # Create task
            task_record = self._crud_repo.create(**task_data)

            # Convert to dict for response
            task_info = {
                "uuid": task_record.uuid,
                "name": task_record.name,
                "portfolio_uuid": task_record.portfolio_uuid,
                "portfolio_name": task_record.portfolio_name,
                "state": task_record.state,
                "progress": task_record.progress,
                "created_at": task_record.created_at.isoformat() if task_record.created_at else None,
            }

            GLOG.INFO(f"成功创建回测任务 '{name}'")

            return ServiceResult.success(
                data={"task_info": task_info},
                message=f"回测任务创建成功"
            )

        except Exception as e:
            GLOG.ERROR(f"创建回测任务失败 '{name}': {e}")
            return ServiceResult.error(f"创建回测任务失败: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update_state(
        self,
        uuid: str,
        state: str,
        worker_id: str = None,
        error: str = None
    ) -> ServiceResult:
        """
        Update task state

        Args:
            uuid: Task UUID
            state: New state (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
            worker_id: Worker ID (optional)
            error: Error message (optional)

        Returns:
            ServiceResult: Update result
        """
        try:
            # Validate state
            valid_states = ["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
            if state not in valid_states:
                return ServiceResult.error(f"Invalid state: {state}. Must be one of {valid_states}")

            # Update state
            self._crud_repo.update_state(uuid, state, error)

            # Assign worker if provided
            if worker_id:
                self._crud_repo.assign_worker(uuid, worker_id)

            return ServiceResult.success(
                {"uuid": uuid, "state": state},
                f"Task state updated to {state}"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to update task state: {str(e)}")
            return ServiceResult.error(f"Failed to update task state: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update_progress(self, uuid: str, progress: float) -> ServiceResult:
        """
        Update task progress

        Args:
            uuid: Task UUID
            progress: Progress value (0-100)

        Returns:
            ServiceResult: Update result
        """
        try:
            if not 0 <= progress <= 100:
                return ServiceResult.error(f"Invalid progress value: {progress}. Must be between 0 and 100")

            self._crud_repo.update_progress(uuid, progress)

            return ServiceResult.success(
                {"uuid": uuid, "progress": progress},
                f"Task progress updated to {progress}%"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to update task progress: {str(e)}")
            return ServiceResult.error(f"Failed to update task progress: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def update_result(self, uuid: str, result: dict) -> ServiceResult:
        """
        Update task result

        Args:
            uuid: Task UUID
            result: Result dictionary

        Returns:
            ServiceResult: Update result
        """
        try:
            self._crud_repo.update_result(uuid, result)

            return ServiceResult.success(
                {"uuid": uuid},
                "Task result updated successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to update task result: {str(e)}")
            return ServiceResult.error(f"Failed to update task result: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def start_task(self, uuid: str, worker_id: str) -> ServiceResult:
        """
        Start a backtest task (assign worker and update state to RUNNING)

        Args:
            uuid: Task UUID
            worker_id: Worker ID

        Returns:
            ServiceResult: Start result
        """
        try:
            self._crud_repo.assign_worker(uuid, worker_id)

            return ServiceResult.success(
                {"uuid": uuid, "worker_id": worker_id, "state": "RUNNING"},
                f"Task started on worker {worker_id}"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to start task: {str(e)}")
            return ServiceResult.error(f"Failed to start task: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def complete_task(self, uuid: str, result: dict = None) -> ServiceResult:
        """
        Mark a task as completed

        Args:
            uuid: Task UUID
            result: Optional result dictionary

        Returns:
            ServiceResult: Complete result
        """
        try:
            # Update state to COMPLETED
            self._crud_repo.update_state(uuid, "COMPLETED")

            # Update result if provided
            if result:
                self._crud_repo.update_result(uuid, result)
                self._crud_repo.modify({"uuid": uuid}, {"progress": 100.0})

            return ServiceResult.success(
                {"uuid": uuid, "state": "COMPLETED"},
                "Task completed successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to complete task: {str(e)}")
            return ServiceResult.error(f"Failed to complete task: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def fail_task(self, uuid: str, error: str) -> ServiceResult:
        """
        Mark a task as failed

        Args:
            uuid: Task UUID
            error: Error message

        Returns:
            ServiceResult: Fail result
        """
        try:
            self._crud_repo.update_state(uuid, "FAILED", error)

            return ServiceResult.success(
                {"uuid": uuid, "state": "FAILED", "error": error},
                f"Task marked as failed: {error}"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to fail task: {str(e)}")
            return ServiceResult.error(f"Failed to fail task: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def cancel_task(self, uuid: str) -> ServiceResult:
        """
        Cancel a backtest task

        Args:
            uuid: Task UUID

        Returns:
            ServiceResult: Cancel result
        """
        try:
            self._crud_repo.update_state(uuid, "CANCELLED")

            return ServiceResult.success(
                {"uuid": uuid, "state": "CANCELLED"},
                "Task cancelled successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to cancel task: {str(e)}")
            return ServiceResult.error(f"Failed to cancel task: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def delete(self, uuid: str) -> ServiceResult:
        """
        Delete a backtest task

        Args:
            uuid: Task UUID

        Returns:
            ServiceResult: Delete result
        """
        try:
            self._crud_repo.delete_by_uuid(uuid)

            return ServiceResult.success(
                {"uuid": uuid},
                f"Task {uuid} deleted successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to delete task: {str(e)}")
            return ServiceResult.error(f"Failed to delete task: {str(e)}")

    @time_logger
    @retry(max_try=3)
    def get_active_tasks(self) -> ServiceResult:
        """
        Get all active (PENDING or RUNNING) tasks

        Returns:
            ServiceResult: Active tasks list
        """
        try:
            result = self._crud_repo.get_active_tasks(as_dataframe=False)

            # Convert ModelList to list of dicts
            tasks_list = []
            if hasattr(result, '__iter__'):
                for task in result:
                    task_dict = {
                        "uuid": task.uuid,
                        "name": task.name,
                        "portfolio_uuid": task.portfolio_uuid,
                        "portfolio_name": task.portfolio_name,
                        "state": task.state,
                        "progress": task.progress,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                    }
                    tasks_list.append(task_dict)

            return ServiceResult.success(
                data={"tasks": tasks_list, "count": len(tasks_list)},
                message=f"获取到 {len(tasks_list)} 个活跃任务"
            )

        except Exception as e:
            GLOG.ERROR(f"获取活跃任务失败: {str(e)}")
            return ServiceResult.error(f"获取活跃任务失败: {str(e)}")
