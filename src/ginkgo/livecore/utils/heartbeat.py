"""
统一心跳机制

为LiveCore各组件提供标准化的心跳实现：
- ExecutionNode (已有)
- Scheduler
- DataManager
- TaskTimer

心跳规格：
- Redis Key格式: heartbeat:component_type:component_id
- 心跳间隔: 10秒
- TTL: 30秒（超过3倍心跳间隔未更新认为离线）
- 心跳值: ISO 8601格式时间戳
"""

import time
import threading
from typing import Optional
from datetime import datetime
from abc import ABC, abstractmethod


class HeartbeatMixin(ABC):
    """
    心跳混入类

    为LiveCore组件提供统一的心跳机制

    使用方式:
        class MyComponent(HeartbeatMixin):
            def __init__(self):
                self.heartbeat_interval = 10  # 心跳间隔（秒）
                self.heartbeat_ttl = 30       # 心跳TTL（秒）
                self._start_heartbeat_thread()

            def _get_heartbeat_key(self) -> str:
                return f"heartbeat:mycomponent:{self.component_id}"

            def _get_redis_client(self):
                return self.redis_client
    """

    # 默认配置
    DEFAULT_HEARTBEAT_INTERVAL = 10  # 10秒心跳间隔
    DEFAULT_HEARTBEAT_TTL = 30       # 30秒TTL

    def __init__(self):
        """初始化心跳相关属性"""
        # 心跳线程
        self.heartbeat_thread: Optional[threading.Thread] = None

        # 心跳配置（子类可以覆盖）
        self.heartbeat_interval = self.DEFAULT_HEARTBEAT_INTERVAL
        self.heartbeat_ttl = self.DEFAULT_HEARTBEAT_TTL

    def _start_heartbeat_thread(self):
        """启动心跳上报线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            print(f"[WARN] Heartbeat thread already running for {self._get_component_name()}")
            return

        # 清理旧的心跳数据（防止重启后残留）
        self._cleanup_old_heartbeat_data()

        # 立即发送一次心跳
        self._send_heartbeat()

        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"heartbeat_{self._get_component_name()}"
        )
        self.heartbeat_thread.start()
        print(f"[INFO] Heartbeat thread started for {self._get_component_name()}")

    def _heartbeat_loop(self):
        """
        心跳上报循环

        每N秒发送一次心跳到Redis，心跳包含：
        - 组件ID
        - 当前时间戳
        - 组件状态（可选，子类可覆盖）
        """
        while self._is_running():
            try:
                # 发送心跳
                self._send_heartbeat()

                # 等待下一次心跳
                for _ in range(self.heartbeat_interval):
                    if not self._is_running():
                        break
                    time.sleep(1)

            except Exception as e:
                print(f"[ERROR] Error in heartbeat loop for {self._get_component_name()}: {e}")
                time.sleep(5)  # 出错后等待5秒再重试

        print(f"[INFO] Heartbeat loop stopped for {self._get_component_name()}")

    def _send_heartbeat(self):
        """
        发送心跳到Redis

        Redis Key: heartbeat:component_type:component_id
        Value: ISO 8601格式时间戳
        TTL: heartbeat_ttl
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                print(f"[WARN] Redis client not available for {self._get_component_name()} heartbeat")
                return

            heartbeat_key = self._get_heartbeat_key()
            heartbeat_value = datetime.now().isoformat()

            # 设置心跳并附带TTL
            redis_client.setex(
                heartbeat_key,
                self.heartbeat_ttl,
                heartbeat_value
            )

            print(f"[DEBUG] Heartbeat sent for {self._get_component_name()}")

        except Exception as e:
            print(f"[ERROR] Failed to send heartbeat for {self._get_component_name()}: {e}")

    def _cleanup_old_heartbeat_data(self):
        """
        清理旧的心跳数据

        在组件启动时调用，确保没有残留的过期数据
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            heartbeat_key = self._get_heartbeat_key()

            # 删除旧的心跳数据
            deleted = redis_client.delete(heartbeat_key)
            if deleted:
                print(f"[INFO] Cleaned up old heartbeat data for {self._get_component_name()}")

        except Exception as e:
            print(f"[WARN] Failed to cleanup old heartbeat data: {e}")

    # ========================================================================
    # 子类需要实现的抽象方法
    # ========================================================================

    @abstractmethod
    def _get_component_name(self) -> str:
        """
        获取组件名称

        Returns:
            str: 组件名称，如 "Scheduler", "DataManager", "TaskTimer"
        """
        pass

    @abstractmethod
    def _get_heartbeat_key(self) -> str:
        """
        获取心跳Redis Key

        Returns:
            str: Redis Key，格式为 heartbeat:component_type:component_id
                 如 "heartbeat:scheduler:scheduler_1"
        """
        pass

    @abstractmethod
    def _get_redis_client(self):
        """
        获取Redis客户端

        Returns:
            Redis客户端实例，如果没有则返回None
        """
        pass

    @abstractmethod
    def _is_running(self) -> bool:
        """
        检查组件是否在运行

        Returns:
            bool: True表示组件正在运行，False表示已停止
        """
        pass

    # ========================================================================
    # 可选的扩展方法
    # ========================================================================

    def _get_heartbeat_details(self) -> dict:
        """
        获取心跳详细信息（可选）

        子类可以覆盖此方法，提供额外的组件状态信息。
        这些信息可以写入另一个Redis Key用于监控。

        Returns:
            dict: 心跳详情，如 {"queue_size": 10, "cpu_usage": 50.0}
        """
        return {}
