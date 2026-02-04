"""
系统状态WebSocket处理器
"""

from fastapi import WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import asyncio

from websocket.manager import connection_manager
from core.logging import logger
from middleware.auth import decode_token, JWTError


class SystemHandler:
    """系统状态WebSocket处理器 - 推送系统运行状态"""

    HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        token: Optional[str] = Query(None)
    ):
        """系统状态推送端点

        Args:
            websocket: WebSocket连接
            token: JWT认证令牌
        """
        # 验证token
        user_uuid = None
        if token:
            try:
                payload = decode_token(token)
                user_uuid = payload.get("user_uuid")
            except JWTError as e:
                logger.warning(f"WebSocket auth failed: {e}")
                await websocket.close(code=1008, reason="Authentication failed")
                return

        # 连接
        await connection_manager.connect(websocket, user_uuid)

        # 订阅系统状态主题
        await connection_manager.subscribe(websocket, "system:status")

        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to system status feed",
            "topics": ["system:status"]
        })

        # 启动心跳任务
        heartbeat_task = asyncio.create_task(self._heartbeat(websocket))

        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理不同类型的消息
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
            # 响应心跳
            await websocket.send_json({"type": "pong"})

        elif msg_type == "subscribe":
            # 订阅主题
            topic = message.get("topic")
            if topic:
                await connection_manager.subscribe(websocket, topic)
                await websocket.send_json({
                    "type": "subscribed",
                    "topic": topic
                })

        elif msg_type == "unsubscribe":
            # 取消订阅
            topic = message.get("topic")
            if topic:
                await connection_manager.unsubscribe(websocket, topic)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "topic": topic
                })

        elif msg_type == "get_status":
            # 请求当前系统状态
            await self._send_system_status(websocket)

        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _send_system_status(self, websocket: WebSocket):
        """发送当前系统状态"""
        # TODO: 实际获取系统状态
        await websocket.send_json({
            "type": "system_status",
            "data": {
                "status": "ONLINE",
                "connections": connection_manager.get_connection_count(),
                "timestamp": asyncio.get_event_loop().time()
            }
        })

    async def _heartbeat(self, websocket: WebSocket):
        """发送心跳"""
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                await websocket.send_json({
                    "type": "heartbeat",
                    "connections": connection_manager.get_connection_count()
                })
        except asyncio.CancelledError:
            pass


# 全局处理器实例
system_handler = SystemHandler()
