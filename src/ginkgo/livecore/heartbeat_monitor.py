# Upstream: LiveEngine (生命周期管理)
# Downstream: Redis (心跳存储)、BrokerInstanceCRUD (状态更新)、BrokerManager (Broker恢复)
# Role: HeartbeatMonitor 监控Broker实例健康状态检测超时并触发恢复


import time
import threading
from typing import List, Callable, Optional
from datetime import datetime, timedelta

from ginkgo.libs import GLOG
from ginkgo.data.containers import container
from ginkgo.data.models.model_broker_instance import MBrokerInstance, BrokerStateType


class HeartbeatMonitor:
    """
    Broker心跳监控器

    定期检查Broker实例的心跳时间：
    - 检测超时的Broker实例
    - 触发恢复流程
    - 更新心跳时间戳
    """

    def __init__(self, check_interval: int = 10, timeout_seconds: int = 30):
        """
        初始化心跳监控器

        Args:
            check_interval: 检查间隔（秒）
            timeout_seconds: 心跳超时时间（秒）
        """
        self._check_interval = check_interval
        self._timeout_seconds = timeout_seconds
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._on_timeout_callbacks: List[Callable[[str], None]] = []

    def add_timeout_callback(self, callback: Callable[[str], None]) -> None:
        """
        添加超时回调函数

        Args:
            callback: 回调函数，接收broker_uuid参数
        """
        self._on_timeout_callbacks.append(callback)

    def start_monitoring(self) -> bool:
        """
        启动监控

        Returns:
            bool: 启动是否成功
        """
        if self._running:
            GLOG.WARNING("Heartbeat monitor is already running")
            return True

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        GLOG.info(f"Heartbeat monitor started (interval={self._check_interval}s, timeout={self._timeout_seconds}s)")
        return True

    def _monitor_loop(self) -> None:
        """监控循环"""
        broker_crud = container.broker_instance()

        while self._running:
            try:
                # 检查所有活跃Broker
                active_brokers = broker_crud.get_active_brokers()
                timeout_brokers = broker_crud.check_timeout(self._timeout_seconds)

                # 更新正常Broker的心跳时间
                for broker in active_brokers:
                    if broker not in timeout_brokers:
                        try:
                            broker_crud.update_heartbeat(broker.uuid)
                        except Exception as e:
                            GLOG.ERROR(f"Failed to update heartbeat for {broker.uuid}: {e}")

                # 处理超时的Broker
                for broker in timeout_brokers:
                    GLOG.WARNING(f"Broker timeout detected: {broker.uuid} (portfolio: {broker.portfolio_id})")

                    # 更新状态为错误
                    try:
                        broker_crud.update_broker_instance_status(
                            broker.uuid,
                            "error",
                            error_message="Heartbeat timeout"
                        )
                    except Exception as e:
                        GLOG.ERROR(f"Failed to update broker state: {e}")

                    # 触发超时回调
                    for callback in self._on_timeout_callbacks:
                        try:
                            callback(broker.uuid)
                        except Exception as e:
                            GLOG.ERROR(f"Timeout callback error: {e}")

                # 等待下一次检查
                time.sleep(self._check_interval)

            except Exception as e:
                GLOG.ERROR(f"Error in monitor loop: {e}")
                time.sleep(self._check_interval)

    def stop_monitoring(self) -> bool:
        """
        停止监控

        Returns:
            bool: 停止是否成功
        """
        if not self._running:
            GLOG.WARNING("Heartbeat monitor is not running")
            return False

        self._running = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        GLOG.info("Heartbeat monitor stopped")
        return True

    def is_running(self) -> bool:
        """检查监控是否正在运行"""
        return self._running


# 全局单例
_heartbeat_monitor = None

def get_heartbeat_monitor() -> HeartbeatMonitor:
    """获取HeartbeatMonitor单例"""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor()
    return _heartbeat_monitor
