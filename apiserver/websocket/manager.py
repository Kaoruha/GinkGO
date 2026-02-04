"""
WebSocket连接管理器
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Set
import asyncio
import json
import logging

from core.logging import setup_logging

logger = setup_logging("websocket")


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 存储所有活跃连接
        self.active_connections: List[WebSocket] = []

        # 按类型分组的连接 {topic: set(connections)}
        self.topic_subscriptions: Dict[str, Set[WebSocket]] = {}

        # 连接元数据 {websocket: {user_uuid, connected_at, topics}}
        self.connection_metadata: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, user_uuid: str = None):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)

        # 存储连接元数据
        self.connection_metadata[websocket] = {
            "user_uuid": user_uuid,
            "connected_at": asyncio.get_event_loop().time(),
            "topics": set()
        }

        logger.info(f"WebSocket connected: {user_uuid}, total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # 清理订阅
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            for topic in metadata["topics"]:
                self._unsubscribe(websocket, topic)
            del self.connection_metadata[websocket]

        logger.info(f"WebSocket disconnected, total: {len(self.active_connections)}")

    async def subscribe(self, websocket: WebSocket, topic: str):
        """订阅主题"""
        if websocket not in self.connection_metadata:
            return

        if topic not in self.topic_subscriptions:
            self.topic_subscriptions[topic] = set()

        self.topic_subscriptions[topic].add(websocket)
        self.connection_metadata[websocket]["topics"].add(topic)

        logger.info(f"WebSocket subscribed to {topic}")

    async def unsubscribe(self, websocket: WebSocket, topic: str):
        """取消订阅主题"""
        if websocket in self.connection_metadata:
            self._unsubscribe(websocket, topic)

    def _unsubscribe(self, websocket: WebSocket, topic: str):
        """内部取消订阅"""
        if topic in self.topic_subscriptions and websocket in self.topic_subscriptions[topic]:
            self.topic_subscriptions[topic].remove(websocket)

            # 如果没有订阅者了，删除主题
            if not self.topic_subscriptions[topic]:
                del self.topic_subscriptions[topic]

        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["topics"].discard(topic)

    async def broadcast(self, message: dict, topic: str = None):
        """广播消息

        Args:
            message: 要发送的消息
            topic: 主题，如果指定则只发送给订阅该主题的连接
        """
        message_str = json.dumps(message)

        # 确定目标连接
        if topic:
            target_connections = self.topic_subscriptions.get(topic, set())
        else:
            target_connections = self.active_connections

        # 发送消息
        disconnected = set()
        for connection in target_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send message: {e}")
                disconnected.add(connection)

        # 清理断开的连接
        for connection in disconnected:
            await self.disconnect(connection)

    async def send_personal(self, message: dict, websocket: WebSocket):
        """发送消息到特定连接"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)

    def get_subscriber_count(self, topic: str) -> int:
        """获取主题订阅者数量"""
        return len(self.topic_subscriptions.get(topic, set()))

    async def start(self):
        """启动连接管理器"""
        logger.info("WebSocket ConnectionManager started")

    async def stop(self):
        """停止连接管理器"""
        for connection in self.active_connections[:]:
            try:
                await connection.close()
            except Exception:
                pass
        self.active_connections.clear()
        self.topic_subscriptions.clear()
        self.connection_metadata.clear()
        logger.info("WebSocket ConnectionManager stopped")


# 全局连接管理器实例
connection_manager = ConnectionManager()
