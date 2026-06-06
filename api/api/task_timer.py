# Upstream: Web UI (定时任务管理页面)
# Downstream: TaskTimerExecutionService (执行记录服务), system_service (任务状态)

"""
TaskTimer API

定时任务管理 API，提供执行历史查询和任务状态查看。
"""

from typing import Optional
from fastapi import APIRouter, Query
from datetime import datetime

from core.response import ok, paginated
from core.logging import logger

router = APIRouter()


def get_task_timer_execution_service():
    from ginkgo.data.containers import container
    return container.task_timer_execution_service()


@router.get("/executions")
async def get_executions(
    job_name: Optional[str] = Query(None, description="按任务名筛选"),
    status: Optional[str] = Query(None, description="按状态筛选: triggered/success/failed"),
    start_date: Optional[str] = Query(None, description="开始时间 (ISO 格式)"),
    end_date: Optional[str] = Query(None, description="结束时间 (ISO 格式)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """查询定时任务执行历史（分页）"""
    try:
        service = get_task_timer_execution_service()

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        result = service.get_history(
            job_name=job_name,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            page=page - 1,
            page_size=page_size,
        )

        if not result.is_success() or not result.data:
            return paginated(items=[], total=0, page=page, page_size=page_size)

        data = result.data
        items = data.get("data", [])
        total = data.get("total", 0)

        return paginated(items=items, total=total, page=page, page_size=page_size)

    except Exception as e:
        logger.error(f"Error getting task timer executions: {e}")
        return paginated(items=[], total=0, page=page, page_size=page_size)


@router.get("/executions/summary")
async def get_executions_summary():
    """获取定时任务执行统计摘要"""
    try:
        service = get_task_timer_execution_service()
        result = service.get_summary()

        if not result.is_success():
            return ok(data={"total": 0, "success": 0, "failed": 0, "triggered": 0, "by_job": {}})

        return ok(data=result.data)

    except Exception as e:
        logger.error(f"Error getting execution summary: {e}")
        return ok(data={"total": 0, "success": 0, "failed": 0, "triggered": 0, "by_job": {}})


@router.get("/jobs")
async def get_registered_jobs():
    """获取当前已注册的定时任务列表"""
    try:
        from ginkgo.core.services.system_service import SystemService
        system_service = SystemService()
        workers_status = system_service.get_workers_status()
        workers = workers_status.get("data", [])

        # 找到 TaskTimer worker
        task_timer_workers = [w for w in workers if w.get("type") == "task_timer"]

        # 从 Redis 心跳中读取 jobs_count
        jobs_info = []
        for w in task_timer_workers:
            jobs_info.append({
                "node_id": w.get("id", "unknown"),
                "jobs_count": w.get("jobs_count", 0) if "jobs_count" in w else 0,
                "last_heartbeat": w.get("last_heartbeat", ""),
                "status": w.get("status", "unknown"),
            })

        # 从默认配置中读取任务定义
        try:
            import os
            import yaml as yaml_lib
            config_path = os.path.expanduser("~/.ginkgo/task_timer.yml")
            if not os.path.exists(config_path):
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "src", "ginkgo", "config", "task_timer.yml"
                )

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml_lib.safe_load(f)
            else:
                config = {"scheduled_tasks": []}

            tasks = []
            for task in config.get("scheduled_tasks", []):
                tasks.append({
                    "name": task.get("name", ""),
                    "cron": task.get("cron", ""),
                    "command": task.get("command", ""),
                    "enabled": task.get("enabled", True),
                })
        except Exception:
            tasks = []

        return ok(data={"workers": jobs_info, "tasks": tasks})

    except Exception as e:
        logger.error(f"Error getting registered jobs: {e}")
        return ok(data={"workers": [], "tasks": []})
