# Issue #5878: Worker Management 切片 — GET /workers/{type} 分类 filter
# Upstream: api.system.get_workers_by_type (new endpoint)
# Downstream: WebUI Worker 管理页（/workers/backtest|data|execution|scheduler|timer）
# Role: 前端调 5 个分类端点，后端按 worker.type filter 聚合数据。

"""
#5878 Worker Management 切片测试。

前端调 ``GET /api/v1/system/workers/{backtest|data|execution|scheduler|timer}`` 5 个分类
端点均 404（后端仅有聚合 ``GET /workers``，#5878 body 列举）。``get_workers_status`` 已返回
带 ``type`` 字段（``backtest_worker``/``data_worker``/``execution_node``/``scheduler``/
``task_timer``，见 system_service.py:107-153）的 worker 列表，但无按 type filter 的子端点。

本切片补 ``GET /workers/{worker_type}``，复用聚合按 ``worker.type`` 归类。满足 AC 第 5 条
「Worker 管理端点返回各 Worker 真实状态」。不关闭 #5878（22+ 端点跨 7 模块，本切片仅
Worker Management 1 模块）。
"""
import asyncio

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    GCONF.set_debug(True)


def run_async(coro):
    return asyncio.run(coro)


class TestWorkersByType:
    """GET /workers/{worker_type} 按 worker.type filter（#5878）。"""

    def test_unknown_type_raises_404(self):
        """未知 type → HTTPException 404（防静默返回空，前端能区分 type 错误 vs 真无 worker）。"""
        from api.system import get_workers_by_type

        with pytest.raises(HTTPException) as exc:
            run_async(get_workers_by_type("unknown_type"))
        assert exc.value.status_code == 404

    def test_backtest_filters_backtest_worker(self):
        """backtest type → 只返回 backtest_worker（复用聚合 filter）。"""
        from api.system import get_workers_by_type

        mock_svc = MagicMock()
        mock_svc.get_workers_status.return_value = {
            "data": [
                {"id": "w1", "type": "backtest_worker", "status": "running"},
                {"id": "w2", "type": "data_worker", "status": "running"},
                {"id": "w3", "type": "backtest_worker", "status": "idle"},
            ],
            "components": {},
        }
        with patch("api.system._get_system_service", return_value=mock_svc):
            result = run_async(get_workers_by_type("backtest"))

        data = result["data"]
        assert data["type"] == "backtest_worker"
        assert data["count"] == 2
        assert all(w["type"] == "backtest_worker" for w in data["workers"])

    @pytest.mark.parametrize("path,target", [
        ("backtest", "backtest_worker"),
        ("data", "data_worker"),
        ("execution", "execution_node"),
        ("scheduler", "scheduler"),
        ("timer", "task_timer"),
    ])
    def test_each_path_maps_to_correct_worker_type(self, path, target):
        """5 个前端路径 → 对应后端 worker.type（#5878 body 列举的 5 端点全覆盖）。"""
        from api.system import get_workers_by_type

        mock_svc = MagicMock()
        mock_svc.get_workers_status.return_value = {
            "data": [{"id": "x", "type": target}],
            "components": {},
        }
        with patch("api.system._get_system_service", return_value=mock_svc):
            result = run_async(get_workers_by_type(path))

        data = result["data"]
        assert data["type"] == target
        assert data["count"] == 1

    def test_valid_type_with_no_matching_workers_returns_empty(self):
        """type 有效但聚合无该类型 worker → count=0 不崩（前端显示「无运行实例」）。"""
        from api.system import get_workers_by_type

        mock_svc = MagicMock()
        mock_svc.get_workers_status.return_value = {
            "data": [{"id": "x", "type": "data_worker"}],
            "components": {},
        }
        with patch("api.system._get_system_service", return_value=mock_svc):
            result = run_async(get_workers_by_type("backtest"))

        data = result["data"]
        assert data["type"] == "backtest_worker"
        assert data["count"] == 0
        assert data["workers"] == []

    def test_service_exception_degrades_to_empty_not_crash(self):
        """get_workers_status 抛异常 → 降级 count=0（端点不崩，与聚合 /workers 一致）。"""
        from api.system import get_workers_by_type

        mock_svc = MagicMock()
        mock_svc.get_workers_status.side_effect = RuntimeError("redis down")
        with patch("api.system._get_system_service", return_value=mock_svc):
            result = run_async(get_workers_by_type("backtest"))

        data = result["data"]
        assert data["type"] == "backtest_worker"
        assert data["count"] == 0
