# Worker 管理页下钻端点 — GET /workers/{worker_id}/tasks
# Upstream: api.system.get_worker_tasks
# Downstream: WebUI Worker 管理页行内展开（回测 worker 活跃任务）
# Role: 心跳 task_uuids → MySQL backtest_task 明细，供前端懒加载下钻。
import asyncio

from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


class TestWorkerTasksEndpoint:
    def test_returns_service_result(self):
        from api.system import get_worker_tasks
        payload = {"worker_id": "bw1", "found": True, "tasks": [{
            "task_id": "t-1", "name": "n", "status": "running",
            "progress": 42, "portfolio_id": "p-1"}]}

        with patch("api.system._get_system_service") as mock_svc:
            mock_svc.return_value.get_worker_tasks.return_value = payload
            resp = run_async(get_worker_tasks("bw1"))

        assert resp["data"] == payload

    def test_exception_returns_empty_not_500(self):
        """Service 抛错 → 空载荷（沿用本模块 ok 兜底模式），不 500。"""
        from api.system import get_worker_tasks

        with patch("api.system._get_system_service") as mock_svc:
            mock_svc.return_value.get_worker_tasks.side_effect = RuntimeError("boom")
            resp = run_async(get_worker_tasks("bw1"))

        assert resp["data"] == {"worker_id": "bw1", "found": False, "tasks": []}
