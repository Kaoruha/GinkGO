"""#6736 KafkaService 消费 worker 退役后契约 smoke（#6685 diff coverage gate 采集）。

退役删了 _message_handlers/_consumer_threads/_stop_events 等本地状态字段后，3 个
查询/健康方法的**行为与返回契约发生变更**（非纯删），是本 PR 改动可执行行：
- get_topic_status：不再 copy+update handler/consumer 字段，直返 crud.get_topic_info
- get_queue_metrics(topics=None)：原 list(_message_handlers.keys()) → 现 []
- health_check：healthy 判定去掉消费者线程维度；返回 dict 删了 active_consumers /
  total_subscriptions / running_consumers 3 字段

同目录 test_kafka_consumer_retired.py 只验证"已删除"（hasattr 断言），不调方法体 →
diff coverage gate 红。本文件 mock crud（不连 Kafka）调起 3 方法体补覆盖信号，并锁定
退役后的新契约，纳入 gate 合集采集。
"""

import os
import sys

import pytest
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.kafka_service import KafkaService


@pytest.fixture
def kafka_service():
    with patch("ginkgo.libs.GLOG"):
        return KafkaService(kafka_crud=MagicMock())


@pytest.mark.unit
def test_get_topic_status_returns_crud_info(kafka_service):
    """get_topic_status 直返 crud.get_topic_info（退役后不再合成 handler/consumer 字段）。"""
    kafka_service._crud_repo.get_topic_info.return_value = {
        "topic": "ticks",
        "partitions": 3,
    }
    result = kafka_service.get_topic_status("ticks")
    assert result.success is True
    assert result.data == {"topic": "ticks", "partitions": 3}
    # 退役契约：返回 dict 不再含 handler/consumer 残留字段
    assert "has_handler" not in result.data
    assert "is_consuming" not in result.data


@pytest.mark.unit
def test_get_queue_metrics_none_topics_returns_empty(kafka_service):
    """topics=None 现走空集分支（无本地订阅状态），metrics["topics"] 为 {}。"""
    result = kafka_service.get_queue_metrics(None)
    assert result.success is True
    assert result.data["topics"] == {}
    # 退役契约：topics 为空时不查 crud lag（get_message_count 不应被触达）
    kafka_service._crud_repo.get_message_count.assert_not_called()


@pytest.mark.unit
def test_health_check_healthy_when_connected(kafka_service):
    """健康判定仅看 kafka 连接；connected=True → healthy，字段契约精简。"""
    kafka_service._crud_repo.get_kafka_status.return_value = {"connected": True}
    result = kafka_service.health_check()
    assert result.success is True
    assert result.data["status"] == "healthy"
    assert result.data["kafka_connection"] is True
    assert result.data["service"] == "KafkaService"
    # 退役契约：返回 dict 不再含消费者线程相关字段
    assert "active_consumers" not in result.data
    assert "total_subscriptions" not in result.data
    assert "running_consumers" not in result.data


@pytest.mark.unit
def test_health_check_unhealthy_when_disconnected(kafka_service):
    """connected=False → unhealthy（覆盖三元表达式 else 分支）。"""
    kafka_service._crud_repo.get_kafka_status.return_value = {"connected": False}
    result = kafka_service.health_check()
    assert result.success is True
    assert result.data["status"] == "unhealthy"
    assert result.data["kafka_connection"] is False
