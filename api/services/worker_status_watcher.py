"""Worker Status Watcher

周期快照 diff Redis worker 存活状态，变化经 WS 广播 worker.changed（ADR-046）。

无独立事件源（心跳只是 Redis TTL key），用服务端 10s 轮询换 N 个前端各自轮询；
心跳 TTL 30s，死 worker 在 ~10-40s 内翻 offline。首轮只播种快照不广播
（初始状态由 REST 提供，避免 API 重启风暴）。
"""

import asyncio
from typing import Dict, List, Optional

from core.logging import logger
from websocket.events import broadcast_event


def _snapshot_sync() -> Dict[str, dict]:
    """同步读 worker 快照（Redis I/O，watch loop 经 executor 调用）。

    走 SystemService（API → Service 分层）；行形状
    {id, type, status(小写), task_count, last_heartbeat}。
    """
    from ginkgo.core.services.system_service import SystemService

    data = SystemService().get_workers_status().get("data", [])
    return {w["id"]: w for w in data if w.get("id")}


def _diff(prev: Dict[str, dict], cur: Dict[str, dict]) -> List[dict]:
    """纯函数：两快照差 → 变更列表（新增/状态变化/消失→offline）。"""
    out: List[dict] = []
    for wid, row in cur.items():
        if wid not in prev:
            out.append({"id": wid, "status": row.get("status", "unknown"),
                        "data": {"type": row.get("type"), "previous_status": None}})
        elif prev[wid].get("status") != row.get("status"):
            out.append({"id": wid, "status": row.get("status", "unknown"),
                        "data": {"type": row.get("type"),
                                 "previous_status": prev[wid].get("status")}})
    for wid, row in prev.items():
        if wid not in cur:
            out.append({"id": wid, "status": "offline",
                        "data": {"type": row.get("type"),
                                 "previous_status": row.get("status")}})
    return out


class WorkerStatusWatcher:
    """worker 存活状态监视器：10s 快照 diff → WS worker.changed 事件"""

    INTERVAL = 10.0

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_snapshot: Optional[Dict[str, dict]] = None  # None = 首轮播种中

    async def start(self):
        if self._running:
            logger.warning("WorkerStatusWatcher already running")
            return

        self._running = True
        self._last_snapshot = None
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("WorkerStatusWatcher started")

    async def stop(self):
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("WorkerStatusWatcher stopped")

    async def _watch_loop(self):
        while self._running:
            try:
                snapshot = await asyncio.get_event_loop().run_in_executor(
                    None, _snapshot_sync)

                if self._last_snapshot is not None:
                    for change in _diff(self._last_snapshot, snapshot):
                        await broadcast_event(
                            "worker.changed", "worker",
                            change["id"], change["status"], change["data"],
                        )
                # 首轮（含重启后重置）只播种，不广播
                self._last_snapshot = snapshot

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WorkerStatusWatcher error: {e}")

            await asyncio.sleep(self.INTERVAL)


# 全局单例
_worker_status_watcher: Optional[WorkerStatusWatcher] = None


def get_worker_status_watcher() -> WorkerStatusWatcher:
    """获取 WorkerStatusWatcher 单例"""
    global _worker_status_watcher
    if _worker_status_watcher is None:
        _worker_status_watcher = WorkerStatusWatcher()
    return _worker_status_watcher
