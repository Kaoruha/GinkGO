"""
Portfolio WebSocket处理器
"""

from fastapi import WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import asyncio

from websocket.manager import connection_manager
from core.logging import logger
from middleware.auth import decode_token, JWTError


class PortfolioHandler:
    """Portfolio WebSocket处理器 - 推送Portfolio实时数据"""

    HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        token: Optional[str] = Query(None),
        portfolio_uuid: Optional[str] = Query(None)
    ):
        """Portfolio数据推送端点

        Args:
            websocket: WebSocket连接
            token: JWT认证令牌
            portfolio_uuid: Portfolio UUID（可选，订阅特定Portfolio）
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

        # 如果指定了portfolio，订阅该主题
        if portfolio_uuid:
            await connection_manager.subscribe(websocket, f"portfolio:{portfolio_uuid}")
            await websocket.send_json({
                "type": "subscribed",
                "topic": f"portfolio:{portfolio_uuid}",
                "message": f"Subscribed to {portfolio_uuid}"
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
            logger.info(f"WebSocket disconnected: {user_uuid}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
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

        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _heartbeat(self, websocket: WebSocket):
        """发送心跳"""
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                await websocket.send_json({"type": "heartbeat"})
        except asyncio.CancelledError:
            pass


# 全局处理器实例
portfolio_handler = PortfolioHandler()
