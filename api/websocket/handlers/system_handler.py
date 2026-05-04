"""
系统状态WebSocket处理器
"""

from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio

from websocket.manager import connection_manager
from middleware.auth import verify_token
from core.logging import logger


class SystemHandler:
    """系统状态WebSocket处理器 - 推送系统运行状态"""

    HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

    async def websocket_endpoint(self, websocket: WebSocket):
        """系统状态推送端点

        token 通过 query param 传入: /ws/system?token=xxx
        """
        # 统一 token 校验
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Missing token")
            return

        try:
            payload = verify_token(token)
            user_uuid = payload.get("user_uuid")
        except Exception:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return

        # 连接
        await connection_manager.connect(websocket, user_uuid)
        await connection_manager.subscribe(websocket, "system:status")

        await websocket.send_json({
            "type": "connected",
            "message": "Connected to system status feed",
            "topics": ["system:status"],
        })

        # 启动心跳任务
        heartbeat_task = asyncio.create_task(self._heartbeat(websocket))

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await self._handle_message(websocket, message, user_uuid)
        except WebSocketDisconnect:
            logger.info(f"System WebSocket disconnected: {user_uuid}")
        except Exception as e:
            logger.error(f"System WebSocket error: {e}")
        finally:
            heartbeat_task.cancel()
            await connection_manager.disconnect(websocket)

    async def _handle_message(self, websocket: WebSocket, message: dict, user_uuid: str):
        """处理客户端消息"""
        msg_type = message.get("type")

        if msg_type == "ping":
            await websocket.send_json({"type": "pong"})

        elif msg_type == "subscribe":
            topic = message.get("topic")
            if topic:
                await connection_manager.subscribe(websocket, topic)
                await websocket.send_json({"type": "subscribed", "topic": topic})

        elif msg_type == "unsubscribe":
            topic = message.get("topic")
            if topic:
                await connection_manager.unsubscribe(websocket, topic)
                await websocket.send_json({"type": "unsubscribed", "topic": topic})

        elif msg_type == "get_status":
            await self._send_system_status(websocket)

    async def _send_system_status(self, websocket: WebSocket):
        """发送当前系统状态"""
        await websocket.send_json({
            "type": "system_status",
            "data": {
                "status": "ONLINE",
                "connections": connection_manager.get_connection_count(),
                "timestamp": asyncio.get_event_loop().time(),
            },
        })

    async def _heartbeat(self, websocket: WebSocket):
        """发送心跳"""
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                await websocket.send_json({
                    "type": "heartbeat",
                    "connections": connection_manager.get_connection_count(),
                })
        except asyncio.CancelledError:
            pass


# 全局处理器实例
system_handler = SystemHandler()
