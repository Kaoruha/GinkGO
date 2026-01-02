# Upstream: NotificationService (通知服务业务逻辑)
# Downstream: Kafka Producer/Consumer (Kafka客户端)
# Role: KafkaHealthChecker Kafka健康检查器检查Kafka服务可用性支持降级策略确保通知送达支持通知系统功能


"""
Kafka Health Checker

Kafka 健康检查器，用于检测 Kafka 服务可用性。
支持连接超时检查、Topic 存在性检查、Producer 初始化检查、Broker 可达性检查。

根据 FR-019a：当 Kafka 不可用时自动降级为同步发送模式。
"""

import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ginkgo.libs import GLOG


class KafkaHealthChecker:
    """
    Kafka 健康检查器

    检测 Kafka 服务是否可用，支持降级策略。
    """

    # Kafka 健康检查标准（FR-019a）
    CHECK_TIMEOUT = 10  # 连接超时 10 秒
    RETRY_THRESHOLD = 3  # Producer 初始化连续失败 3 次判定为不可用

    def __init__(self, kafka_crud=None):
        """
        初始化健康检查器

        Args:
            kafka_crud: KafkaCRUD 实例
        """
        if kafka_crud is None:
            from ginkgo.data.crud import KafkaCRUD
            kafka_crud = KafkaCRUD()

        self.kafka_crud = kafka_crud
        self._is_healthy = None  # None = 未检查, True = 健康, False = 不健康
        self._last_check_time: Optional[datetime] = None
        self._consecutive_failures = 0
        self._lock = threading.Lock()
        self._check_in_progress = False

    @property
    def is_healthy(self) -> bool:
        """
        Kafka 是否健康

        Returns:
            bool: True 表示健康，False 表示不健康
        """
        # 如果从未检查过，执行检查
        if self._is_healthy is None:
            self.check_health()
        return self._is_healthy

    def check_health(self, force: bool = False) -> Dict[str, Any]:
        """
        执行健康检查

        Args:
            force: 是否强制重新检查（忽略缓存）

        Returns:
            Dict: 健康检查结果
        """
        # 防止并发检查
        if self._check_in_progress and not force:
            return self._get_cached_result()

        with self._lock:
            if self._check_in_progress and not force:
                return self._get_cached_result()

            self._check_in_progress = True

        try:
            result = {
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {}
            }

            # 1. 连接超时检查（10秒）
            result["checks"]["connection"] = self._check_connection_timeout()

            # 2. Producer 初始化检查
            result["checks"]["producer"] = self._check_producer_init()

            # 3. Broker 可达性检查
            result["checks"]["broker"] = self._check_broker_reachable()

            # 4. Topic 存在性检查（可选，如果连接成功）
            if result["checks"]["connection"]["success"]:
                result["checks"]["topic"] = self._check_topic_exists()

            # 综合判断健康状态
            all_healthy = all(
                check.get("success", False)
                for check in result["checks"].values()
            )

            self._is_healthy = all_healthy
            self._last_check_time = datetime.utcnow()

            # 更新连续失败计数
            if not all_healthy:
                self._consecutive_failures += 1
            else:
                self._consecutive_failures = 0

            result["healthy"] = all_healthy
            result["consecutive_failures"] = self._consecutive_failures

            if not all_healthy:
                GLOG.WARN(f"Kafka health check failed: {result}")
            else:
                GLOG.DEBUG("Kafka health check passed")

            return result

        except Exception as e:
            GLOG.ERROR(f"Kafka health check error: {e}")
            self._is_healthy = False
            self._consecutive_failures += 1
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "healthy": False,
                "error": str(e),
                "consecutive_failures": self._consecutive_failures
            }

        finally:
            with self._lock:
                self._check_in_progress = False

    def should_degrade(self, quick_check: bool = True) -> bool:
        """
        是否应该降级为同步发送模式

        根据连续失败次数判断。

        Args:
            quick_check: 是否快速检查（使用缓存，不执行耗时检查）

        Returns:
            bool: True 表示应该降级
        """
        # 快速模式：如果有缓存结果直接使用，否则假设健康（避免阻塞）
        if quick_check:
            if self._is_healthy is None:
                # 首次调用，假设健康，让发送操作自己决定
                return False
        else:
            # 完整检查：如果从未检查过，先检查一次
            if self._is_healthy is None:
                self.check_health()

        # 检查是否超过重试阈值
        if self._consecutive_failures >= self.RETRY_THRESHOLD:
            GLOG.WARN(
                f"Kafka degradation threshold reached: "
                f"{self._consecutive_failures} consecutive failures"
            )
            return True

        # 直接返回健康状态取反
        return not self._is_healthy

    def _check_connection_timeout(self) -> Dict[str, Any]:
        """
        检查连接超时

        尝试在 10 秒内连接到 Kafka。
        超过 10 秒无响应视为不可用。

        Returns:
            Dict: 检查结果
        """
        try:
            start_time = time.time()

            # 使用线程实现超时控制
            def test_connection():
                try:
                    return self.kafka_crud._test_connection()
                except Exception:
                    return False

            # 在新线程中执行连接测试
            result = [None]

            def worker():
                result[0] = test_connection()

            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            thread.join(timeout=self.CHECK_TIMEOUT)

            elapsed = time.time() - start_time

            if thread.is_alive():
                # 线程仍在运行，说明超时了
                return {
                    "success": False,
                    "error": f"Connection timeout after {elapsed:.2f}s (exceeds {self.CHECK_TIMEOUT}s limit)",
                    "elapsed_seconds": elapsed
                }

            if result[0] is True:
                return {
                    "success": True,
                    "elapsed_seconds": elapsed
                }
            else:
                return {
                    "success": False,
                    "error": "Connection failed",
                    "elapsed_seconds": elapsed
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _check_producer_init(self) -> Dict[str, Any]:
        """
        检查 Producer 是否可以初始化

        Returns:
            Dict: 检查结果
        """
        try:
            # 检查 producer 是否存在
            if self.kafka_crud.producer is None:
                return {
                    "success": False,
                    "error": "Producer is None"
                }

            # 检查 producer 是否可用
            if hasattr(self.kafka_crud.producer, 'producer'):
                if self.kafka_crud.producer.producer is None:
                    return {
                        "success": False,
                        "error": "Producer.client is None"
                    }

            return {
                "success": True
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _check_broker_reachable(self) -> Dict[str, Any]:
        """
        检查 Broker 是否可达

        Returns:
            Dict: 检查结果
        """
        try:
            # 尝试获取 broker 信息
            if hasattr(self.kafka_crud.producer, 'producer'):
                producer = self.kafka_crud.producer.producer
                if producer is not None:
                    # 检查 bootstrap_servers
                    if hasattr(producer, 'config'):
                        bootstrap_servers = producer.config.get('bootstrap_servers', '')
                        if bootstrap_servers:
                            return {
                                "success": True,
                                "bootstrap_servers": bootstrap_servers
                            }

            return {
                "success": False,
                "error": "Cannot determine broker reachability"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _check_topic_exists(self) -> Dict[str, Any]:
        """
        检查 notifications topic 是否存在

        Returns:
            Dict: 检查结果
        """
        try:
            # 直接使用常量，不再依赖 MessageQueue
            topic = "notifications"

            topic_info = self.kafka_crud.get_topic_info(topic)

            if topic_info:
                return {
                    "success": True,
                    "topic": topic,
                    "exists": True
                }
            else:
                # Topic 不存在不是致命错误，会自动创建
                return {
                    "success": True,
                    "topic": topic,
                    "exists": False,
                    "note": "Topic will be created on first use"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _get_cached_result(self) -> Dict[str, Any]:
        """
        获取缓存的检查结果

        Returns:
            Dict: 缓存的结果
        """
        return {
            "timestamp": self._last_check_time.isoformat() if self._last_check_time else None,
            "cached": True,
            "healthy": self._is_healthy,
            "consecutive_failures": self._consecutive_failures
        }

    def get_health_summary(self) -> str:
        """
        获取健康状态摘要

        Returns:
            str: 健康状态描述
        """
        if self._is_healthy is None:
            return "Unknown (not checked)"

        if self._is_healthy:
            return f"Healthy (last checked: {self._last_check_time.strftime('%H:%M:%S')})"

        if self._consecutive_failures >= self.RETRY_THRESHOLD:
            return f"Degraded ({self._consecutive_failures} consecutive failures)"

        return f"Unhealthy ({self._consecutive_failures} consecutive failures)"


# ============================================================================
# 便捷函数
# ============================================================================

def is_kafka_available(kafka_crud=None) -> bool:
    """
    检查 Kafka 是否可用（便捷函数）

    Args:
        kafka_crud: KafkaCRUD 实例

    Returns:
        bool: Kafka 是否可用
    """
    checker = KafkaHealthChecker(kafka_crud)
    return checker.is_healthy


def should_degrade_to_sync(kafka_crud=None) -> bool:
    """
    是否应该降级为同步发送模式（便捷函数）

    Args:
        kafka_crud: KafkaCRUD 实例

    Returns:
        bool: 是否应该降级
    """
    checker = KafkaHealthChecker(kafka_crud)
    return checker.should_degrade()
