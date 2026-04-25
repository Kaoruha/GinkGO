"""
Portfolio WebSocket处理器
"""

from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio

from websocket.manager import connection_manager
from middleware.auth import verify_token
from core.logging import logger


class PortfolioHandler:
    """Portfolio WebSocket处理器 - 推送Portfolio实时数据"""

    HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

    async def websocket_endpoint(self, websocket: WebSocket):
        """Portfolio数据推送端点

        token 通过 query param 传入: /ws/portfolio?token=xxx&portfolio_uuid=xxx
        """
        # 统一 token 校验（与中间件使用同一个 verify_token）
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

        # 如果指定了 portfolio，订阅该主题
        portfolio_uuid = websocket.query_params.get("portfolio_uuid")
        if portfolio_uuid:
            await connection_manager.subscribe(websocket, f"portfolio:{portfolio_uuid}")
            await websocket.send_json({
                "type": "subscribed",
                "topic": f"portfolio:{portfolio_uuid}",
                "message": f"Subscribed to {portfolio_uuid}",
            })

        # 启动心跳任务
        heartbeat_task = asyncio.create_task(self._heartbeat(websocket))

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
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
