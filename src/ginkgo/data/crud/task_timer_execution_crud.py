# Upstream: TaskTimerExecutionService (执行记录业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力), MTaskTimerExecution (MySQL执行记录模型)
# Role: TaskTimerExecutionCRUD 定时任务执行记录CRUD，提供触发记录、完成更新、历史查询

"""
TaskTimer Execution Record CRUD Operations

定时任务执行记录的增删改查操作，支持执行历史追踪和统计。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MTaskTimerExecution
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class TaskTimerExecutionCRUD(BaseCRUD[MTaskTimerExecution]):
    """
    定时任务执行记录 CRUD

    支持：
    - 记录任务触发 (INSERT triggered)
    - 更新执行结果 (UPDATE success/failed)
    - 按条件查询执行历史
    """

    _model_class = MTaskTimerExecution

    def __init__(self):
        super().__init__(MTaskTimerExecution)

    def _get_field_config(self) -> dict:
        return {}

    def _create_from_params(self, **kwargs) -> MTaskTimerExecution:
        model = MTaskTimerExecution()
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        return model

    def record_trigger(
        self,
        job_name: str,
        command: str,
        node_id: str,
        cron_expr: str = "",
        params: Optional[Dict] = None,
    ) -> Optional[MTaskTimerExecution]:
        """
        记录任务触发，创建 triggered 记录

        Returns:
            创建的记录（含 uuid），失败返回 None
        """
        try:
            model = MTaskTimerExecution()
            model.job_name = job_name
            model.command = command
            model.node_id = node_id
            model.cron_expr = cron_expr
            model.status = "triggered"
            model.triggered_at = datetime.now()
            model.params = params
            self.add(model)
            return model
        except Exception as e:
            GLOG.ERROR(f"Failed to record trigger for {job_name}: {e}")
            return None

    def complete_record(
        self,
        uuid: str,
        status: str,
        duration_ms: int = 0,
        error_message: Optional[str] = None,
        result: Optional[Dict] = None,
    ) -> bool:
        """
        更新执行记录为完成状态

        Args:
            uuid: 执行记录 ID
            status: success / failed
            duration_ms: 耗时毫秒
            error_message: 失败原因
            result: 执行结果 JSON

        Returns:
            是否更新成功
        """
        try:
            self.modify(
                filters={"uuid": uuid},
                updates={
                    "status": status,
                    "completed_at": datetime.now(),
                    "duration_ms": duration_ms,
                    "error_message": error_message,
                    "result": result,
                },
            )
            return True
        except Exception as e:
            GLOG.ERROR(f"Failed to complete record {uuid}: {e}")
            return False

    def find_by_job_name(
        self, job_name: str, page: int = 0, page_size: int = 20
    ) -> ModelList:
        """按任务名查询执行历史"""
        return self.find(
            filters={"job_name": job_name},
            order_by="triggered_at",
            desc_order=True,
            page=page,
            page_size=page_size,
        )

    def find_by_time_range(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> ModelList:
        """按时间范围查询"""
        filters: Dict[str, Any] = {}
        if start:
            filters["triggered_at__gte"] = start
        if end:
            filters["triggered_at__lte"] = end
        return self.find(
            filters=filters,
            order_by="triggered_at",
            desc_order=True,
            page=page,
            page_size=page_size,
        )

    def count_by_status(self, status: str) -> int:
        """按状态统计数量"""
        return self.count(filters={"status": status})

    def get_summary(self) -> Dict[str, Any]:
        """
        获取执行统计摘要

        Returns:
            {"total": N, "success": N, "failed": N, "triggered": N, "by_job": {...}}
        """
        total = self.count(filters={})
        success = self.count(filters={"status": "success"})
        failed = self.count(filters={"status": "failed"})
        triggered = self.count(filters={"status": "triggered"})

        # 按任务名分组统计（取最近 1000 条）
        recent = self.find(
            filters={},
            order_by="triggered_at",
            desc_order=True,
            page=0,
            page_size=1000,
        )
        by_job: Dict[str, Dict[str, int]] = {}
        for record in recent:
            name = record.job_name
            if name not in by_job:
                by_job[name] = {"total": 0, "success": 0, "failed": 0}
            by_job[name]["total"] += 1
            if record.status == "success":
                by_job[name]["success"] += 1
            elif record.status == "failed":
                by_job[name]["failed"] += 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "triggered": triggered,
            "by_job": by_job,
        }
