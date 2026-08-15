"""服务端推送事件信封与广播入口（全局薄事件通道）。

设计要点（详见 ADR-046）:
- 只推薄事件（谁变了 + 少量展示字段），数据一致性由前端按需 REST 拉取保证
- status 统一小写 DB/REST 词汇；worker 上报的大写 state 经 STATUS_MAP 归一
- 不做全局 seq，断线窗口由前端"重连补齐"（重连后对活跃实体幂等刷新）兜底
- backtest/deployment/worker 事件全员广播（实体无 user 归属，单用户项目可接受）；
  通知按 user 定向（broadcast_to_user），无匹配连接时回退全员
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from websocket.manager import connection_manager

# worker 上报的大写 state 枚举 → 规范小写（与 MBacktestTask.status/REST 一致）。
# DATA_PREPARING/ENGINE_BUILDING 无对应 DB 状态（DB 仅写 progress 不写 state），归入 running。
STATUS_MAP = {
    "PENDING": "pending",
    "DATA_PREPARING": "running",
    "ENGINE_BUILDING": "running",
    "RUNNING": "running",
    "COMPLETED": "completed",
    "FAILED": "failed",
    "CANCELLED": "stopped",
}


def canonical_status(state: Optional[str], default: str = "running") -> str:
    """把任意来源的 state 归一为小写规范词；未知值小写透传。"""
    if not state:
        return default
    return STATUS_MAP.get(state.upper(), str(state).lower())


def build_event(
    event: str,
    entity: str,
    id: str,
    status: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> dict:
    """构造统一事件信封。status 仅在有语义时携带（如 notification 省略）。"""
    msg = {
        "type": "event",
        "event": event,
        "entity": entity,
        "id": id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if status is not None:
        msg["status"] = status
    msg["data"] = data or {}
    return msg


async def broadcast_event(
    event: str,
    entity: str,
    id: str,
    status: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """全员广播一个事件（无连接时是廉价 no-op）。"""
    await connection_manager.broadcast(build_event(event, entity, id, status, data))


async def broadcast_event_to_users(
    user_uuids: Optional[List[str]],
    event: str,
    entity: str,
    id: str,
    status: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """按 user 定向广播；无匹配连接时回退全员（单用户项目可接受）。"""
    await connection_manager.broadcast_to_user(
        user_uuids or [],
        build_event(event, entity, id, status, data),
        fallback_all=True,
    )
