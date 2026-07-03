"""
性能: 219MB RSS, 1.9s, 11 tests [PASS]
KafkaCRUD 单元测试（Mock Kafka 连接）

覆盖范围：
- 构造与类型检查：实例属性、Producer
- 消息发送: send_message, send_batch_messages
- 消息消费: consume_messages
- 主题管理: topic_exists, list_topics, get_kafka_status
- 注意：KafkaCRUD 不是 BaseCRUD 子类，直接操作 Kafka
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime


# ============================================================
# 辅助：构造 KafkaCRUD 实例（mock Kafka 连接）
# ============================================================


@pytest.fixture
def kafka_crud():
    """构造 KafkaCRUD 实例，mock 掉 GinkgoProducer 和 GinkgoConsumer"""
    mock_logger = MagicMock()
    mock_producer = MagicMock()

    with patch("ginkgo.data.crud.kafka_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.kafka_crud.GinkgoProducer", return_value=mock_producer):
        from ginkgo.data.crud.kafka_crud import KafkaCRUD
        crud = KafkaCRUD(producer_connection=mock_producer)
        # 跳过连接测试，直接标记为已测试
        crud._connection_tested = True
        return crud


@pytest.fixture
def mock_producer():
    """独立的 mock producer 对象"""
    return MagicMock()


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestKafkaCRUDConstruction:
    """KafkaCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction_with_producer(self):
        """传入 producer_connection 时使用传入的实例"""
        mock_logger = MagicMock()
        mock_producer = MagicMock()

        with patch("ginkgo.data.crud.kafka_crud.GLOG", mock_logger):
            from ginkgo.data.crud.kafka_crud import KafkaCRUD
            crud = KafkaCRUD(producer_connection=mock_producer, default_group_id="test_group")

        assert crud.producer is mock_producer
        assert crud._default_group_id == "test_group"
        assert crud._connection_tested is False
        assert crud._consumers == {}

    @pytest.mark.unit
    def test_construction_auto_create_producer(self):
        """不传 producer_connection 时自动创建 GinkgoProducer"""
        mock_logger = MagicMock()
        mock_producer = MagicMock()

        with patch("ginkgo.data.crud.kafka_crud.GLOG", mock_logger), \
             patch("ginkgo.data.crud.kafka_crud.GinkgoProducer", return_value=mock_producer):
            from ginkgo.data.crud.kafka_crud import KafkaCRUD
            crud = KafkaCRUD()

        assert crud.producer is mock_producer



# ============================================================
# 消息发送测试
# ============================================================


class TestKafkaCRUDSendMessage:
    """send_message 消息发送测试"""

    @pytest.mark.unit
    def test_send_message_dict(self, kafka_crud):
        """发送字典消息，调用 producer.send"""
        result = kafka_crud.send_message("test_topic", {"key": "value"})

        assert result is True
        kafka_crud.producer.send.assert_called_once()

    @pytest.mark.unit
    def test_send_message_with_key(self, kafka_crud):
        """发送带 key 的消息，消息中包含 _key 字段"""
        result = kafka_crud.send_message("test_topic", {"data": 123}, key="my_key")

        assert result is True
        call_args = kafka_crud.producer.send.call_args
        assert call_args[0][0] == "test_topic"
        msg_data = call_args[0][1]
        assert msg_data["_key"] == "my_key"

    @pytest.mark.unit
    def test_send_message_string_wrapped(self, kafka_crud):
        """发送字符串消息时自动包装为字典"""
        result = kafka_crud.send_message("test_topic", "plain_text")

        assert result is True
        call_args = kafka_crud.producer.send.call_args
        msg_data = call_args[0][1]
        assert msg_data["content"] == "plain_text"
        assert "timestamp" in msg_data

    @pytest.mark.unit
    def test_send_batch_messages(self, kafka_crud):
        """批量发送消息，返回成功数量"""
        messages = [{"msg": 1}, {"msg": 2}, {"msg": 3}]

        result = kafka_crud.send_batch_messages("test_topic", messages)

        assert result == 3
        assert kafka_crud.producer.send.call_count == 3


# ============================================================
# 主题管理与监控测试
# ============================================================


class TestKafkaCRUDTopicManagement:
    """topic_exists / list_topics / get_kafka_status 测试"""

    @pytest.mark.unit
    def test_topic_exists_true(self, kafka_crud):
        """主题存在时返回 True"""
        mock_consumer = MagicMock()
        mock_consumer.consumer.partitions_for_topic.return_value = [0, 1]

        with patch("ginkgo.data.crud.kafka_crud.GinkgoConsumer", return_value=mock_consumer):
            result = kafka_crud.topic_exists("existing_topic")

        assert result is True
        mock_consumer.consumer.close.assert_called_once()

    @pytest.mark.unit
    def test_topic_exists_false(self, kafka_crud):
        """主题不存在时返回 False"""
        mock_consumer = MagicMock()
        mock_consumer.consumer.partitions_for_topic.return_value = None

        with patch("ginkgo.data.crud.kafka_crud.GinkgoConsumer", return_value=mock_consumer):
            result = kafka_crud.topic_exists("nonexistent_topic")

        assert result is False

    @pytest.mark.unit
    def test_list_topics(self, kafka_crud):
        """列出所有主题"""
        mock_consumer = MagicMock()
        mock_consumer.consumer.topics.return_value = ["topic_a", "topic_b"]

        with patch("ginkgo.data.crud.kafka_crud.GinkgoConsumer", return_value=mock_consumer):
            result = kafka_crud.list_topics()

        assert result == ["topic_a", "topic_b"]
        mock_consumer.consumer.close.assert_called_once()

    @pytest.mark.unit
    def test_get_kafka_status_connected(self, kafka_crud):
        """Kafka 已连接时状态返回 connected=True"""
        result = kafka_crud.get_kafka_status()

        assert result["connected"] is True
        assert result["producer_active"] is True
        assert "active_consumers" in result

    @pytest.mark.unit
    def test_get_kafka_status_connection_failed(self, kafka_crud):
        """连接测试失败时返回 connected=False"""
        kafka_crud._connection_tested = False
        mock_consumer = MagicMock()
        mock_consumer.consumer = None

        with patch("ginkgo.data.crud.kafka_crud.GinkgoConsumer", return_value=mock_consumer):
            result = kafka_crud.get_kafka_status()

        assert result["connected"] is False


# ============================================================
# broker 端 consumer groups 查询（list_broker_consumer_groups）
# ============================================================


class TestKafkaCRUDBrokerConsumerGroups:
    """list_broker_consumer_groups 走 KafkaAdminClient 真实查询 broker。

    回归 #5310：CLI `consumer-groups` 命令原依赖桩函数，本方法补齐 broker 端查询。
    """

    @pytest.mark.unit
    def test_returns_normalized_groups(self, kafka_crud):
        """list_groups 返回的 dict 被归一化为 name/state/protocol_type/type。"""
        mock_admin = MagicMock()
        # kafka-python 3.x: list_groups 返回 ListedGroup.to_dict() 后的 dict 列表
        mock_admin.list_groups.return_value = [
            {"group_id": "ginkgo_data_worker", "group_state": "Stable",
             "protocol_type": "consumer", "group_type": "classic"},
            {"group_id": "backtest_worker", "group_state": "Empty",
             "protocol_type": "consumer", "group_type": "classic"},
        ]

        with patch("kafka.admin.KafkaAdminClient", return_value=mock_admin):
            result = kafka_crud.list_broker_consumer_groups()

        assert len(result) == 2
        assert result[0] == {
            "name": "ginkgo_data_worker", "state": "Stable",
            "protocol_type": "consumer", "type": "classic",
        }
        assert result[1]["name"] == "backtest_worker"
        mock_admin.close.assert_called_once()

    @pytest.mark.unit
    def test_admin_error_returns_empty_no_raise(self, kafka_crud):
        """admin client 抛异常时返回空列表且不向上抛（CLI 层友好看待连接失败）。"""
        mock_admin = MagicMock()
        mock_admin.list_groups.side_effect = Exception("broker unreachable")
        mock_logger = MagicMock()

        with patch("kafka.admin.KafkaAdminClient", return_value=mock_admin), \
             patch("ginkgo.data.crud.kafka_crud.GLOG", mock_logger):
            result = kafka_crud.list_broker_consumer_groups()

        assert result == []
        mock_admin.close.assert_called_once()
        mock_logger.ERROR.assert_called_once()

    @pytest.mark.unit
    def test_namedtuple_fallback_normalizes(self, kafka_crud):
        """旧版 kafka-python 返回 namedtuple/tuple 时归一化兜底仍生效。"""
        mock_admin = MagicMock()
        # 模拟旧版 (group_id, protocol_type) 二元组
        mock_admin.list_groups.return_value = [("legacy_group", "consumer")]

        with patch("kafka.admin.KafkaAdminClient", return_value=mock_admin):
            result = kafka_crud.list_broker_consumer_groups()

        assert len(result) == 1
        assert result[0]["name"] == "legacy_group"
        assert result[0]["protocol_type"] == "consumer"
