# Upstream: TaskTimer (定时任务触发记录), API (执行历史查询)
# Downstream: BaseService (继承), TaskTimerExecutionCRUD (数据访问)
# Role: 定时任务执行记录业务服务，提供记录触发、完成更新、历史查询、统计摘要

"""
TaskTimer Execution Record Service

定时任务执行记录的业务服务层，封装 CRUD 操作并提供业务语义接口。
"""

from typing import Optional, Dict, Any
from datetime import datetime

from ginkgo.data.services.base_service import BaseService, ServiceResult


class TaskTimerExecutionService(BaseService):
    """
    定时任务执行记录服务

    提供：
    - record_trigger: 记录任务触发
    - complete_record: 更新执行结果
    - get_history: 分页查询执行历史
    - get_summary: 获取统计摘要
    """

    def record_trigger(
        self,
        job_name: str,
        command: str,
        node_id: str,
        cron_expr: str = "",
        params: Optional[Dict] = None,
    ) -> ServiceResult:
        """
        记录任务触发

        Args:
            job_name: 任务名称
            command: 命令类型
            node_id: 节点标识
            cron_expr: cron 表达式
            params: 任务参数

        Returns:
            ServiceResult: 包含创建的记录
        """
        try:
            record = self._crud_repo.record_trigger(
                job_name=job_name,
                command=command,
                node_id=node_id,
                cron_expr=cron_expr,
                params=params,
            )
            if record:
                return ServiceResult.success(
                    data={"uuid": record.uuid, "status": record.status},
                    message=f"Trigger recorded for {job_name}",
                )
            return ServiceResult.error("Failed to record trigger")
        except Exception as e:
            return ServiceResult.error(f"Failed to record trigger: {str(e)}")

    def complete_record(
        self,
        uuid: str,
        status: str,
        duration_ms: int = 0,
        error_message: Optional[str] = None,
        result: Optional[Dict] = None,
    ) -> ServiceResult:
        """
        更新执行记录为完成状态

        Args:
            uuid: 执行记录 ID
            status: success / failed
            duration_ms: 耗时毫秒
            error_message: 失败原因
            result: 执行结果

        Returns:
            ServiceResult
        """
        try:
            success = self._crud_repo.complete_record(
                uuid=uuid,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                result=result,
            )
            if success:
                return ServiceResult.success(
                    data={"uuid": uuid, "status": status},
                    message=f"Record updated to {status}",
                )
            return ServiceResult.error("Failed to complete record")
        except Exception as e:
            return ServiceResult.error(f"Failed to complete record: {str(e)}")

    def get_history(
        self,
        job_name: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> ServiceResult:
        """
        分页查询执行历史

        Args:
            job_name: 按任务名筛选
            status: 按状态筛选
            start_date: 开始时间
            end_date: 结束时间
            page: 页码（从 0 开始）
            page_size: 每页数量

        Returns:
            ServiceResult: {"data": [...], "total": N, "page": N, "page_size": N}
        """
        try:
            filters: Dict[str, Any] = {}
            if job_name:
                filters["job_name"] = job_name
            if status:
                filters["status"] = status
            if start_date:
                filters["triggered_at__gte"] = start_date
            if end_date:
                filters["triggered_at__lte"] = end_date

            items = self._crud_repo.find(
                filters=filters,
                order_by="triggered_at",
                desc_order=True,
                page=page,
                page_size=page_size,
            )
            total = self._crud_repo.count(filters=filters)

            data = []
            for item in items:
                data.append({
                    "uuid": item.uuid,
                    "job_name": item.job_name,
                    "command": item.command,
                    "node_id": item.node_id,
                    "cron_expr": item.cron_expr,
                    "status": item.status,
                    "triggered_at": item.triggered_at.isoformat() if item.triggered_at else None,
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                    "duration_ms": item.duration_ms,
                    "error_message": item.error_message,
                    "params": item.params,
                    "result": item.result,
                })

            return ServiceResult.success(
                data={"data": data, "total": total, "page": page, "page_size": page_size},
                message=f"Found {total} execution records",
            )
        except Exception as e:
            return ServiceResult.error(f"Failed to get history: {str(e)}")

    def get_summary(self) -> ServiceResult:
        """
        获取执行统计摘要

        Returns:
            ServiceResult: {"total", "success", "failed", "triggered", "by_job": {...}}
        """
        try:
            summary = self._crud_repo.get_summary()
            return ServiceResult.success(data=summary)
        except Exception as e:
            return ServiceResult.error(f"Failed to get summary: {str(e)}")
