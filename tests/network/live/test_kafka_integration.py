# Upstream: 无（单元测试）
# Downstream: 无（单元测试）
# Role: Kafka集成测试，验证Producer和Consumer可以正确发送接收消息


"""
Kafka集成测试

验证GinkgoProducer和GinkgoConsumer可以正确发送和接收消息，包括：
1. 基本Producer/Consumer通信
2. ControlCommand序列化/反序列化
3. 实盘交易相关topics通信
4. 端到端消息流

运行要求：
- Kafka服务必须运行在localhost:9092
- 需要先运行kafka_topic_set()创建topics
"""

import json
import pytest
import time
from datetime import datetime

from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer, GinkgoConsumer
from ginkgo.messages.control_command import ControlCommand


@pytest.mark.network
class TestKafkaProducerConsumerE2E:
    """Kafka Producer和Consumer端到端通信测试"""

    def test_producer_consumer_basic_communication(self):
        """测试基本的Producer和Consumer通信"""
        topic = "ginkgo.live.market.data"
        # 使用唯一的测试标识符
        test_uuid = "test_basic_comm_unique"
        test_message = {
            "code": "000001.SZ",
            "timestamp": "2026-01-04T10:00:00",
            "price": 10.5,
            "volume": 1000,
            "test_uuid": test_uuid
        }

        # 创建Producer
        producer = GinkgoProducer()
        assert producer.is_connected, "Producer should be connected"

        # 发送消息
        success = producer.send(topic, test_message)
        assert success, "Message should be sent successfully"

        producer.flush()

        # 创建Consumer接收消息
        consumer = GinkgoConsumer(topic, group_id="test_group_basic_unique")
        assert consumer.is_connected, "Consumer should be connected"
        assert consumer.topic == topic

        # 接收消息（KafkaConsumer是可迭代对象）
        for message in consumer.consumer:
            received_message = message.value
            # 只处理我们发送的消息
            if received_message.get("test_uuid") == test_uuid:
                assert received_message["code"] == "000001.SZ"
                assert received_message["price"] == 10.5
                assert received_message["volume"] == 1000
                break  # 只接收一条消息

        # 清理
        consumer.close()
        producer.producer.close()

    def test_control_command_serialization(self):
        """测试ControlCommand序列化/反序列化通过Kafka"""
        topic = "ginkgo.live.control.commands"

        # 创建ControlCommand
        cmd_uuid = "test_control_cmd_unique"
        cmd = ControlCommand(
            command_type="portfolio.create",
            target_id="portfolio_001",
            params={"strategy_id": "strategy_001", "initial_cash": 100000},
            timestamp=datetime.now(),
            portfolio_id="portfolio_001",
            message_id=f"msg_{cmd_uuid}"
        )

        # 序列化为JSON
        cmd_json = cmd.to_json()
        cmd_dict = json.loads(cmd_json)

        # 创建Producer并发送
        producer = GinkgoProducer()
        assert producer.is_connected

        success = producer.send(topic, cmd_dict)
        assert success, "ControlCommand should be sent successfully"
        producer.flush()

        # 创建Consumer接收
        consumer = GinkgoConsumer(topic, group_id="test_group_control_unique")
        assert consumer.is_connected

        # 接收并反序列化
        for message in consumer.consumer:
            received_dict = message.value
            # 只处理我们发送的命令
            if received_dict.get("message_id") == f"msg_{cmd_uuid}":
                received_cmd = ControlCommand.from_dict(received_dict)

                # 验证所有字段
                assert received_cmd.command_type == "portfolio.create"
                assert received_cmd.target_id == "portfolio_001"
                # params可能为None，需要先检查
                assert received_cmd.params is not None
                assert received_cmd.params.get("strategy_id") == "strategy_001"
                assert received_cmd.params.get("initial_cash") == 100000
                assert received_cmd.portfolio_id == "portfolio_001"
                assert received_cmd.message_id == f"msg_{cmd_uuid}"
                assert received_cmd.timestamp is not None
                break

        # 清理
        consumer.close()
        producer.producer.close()

    def test_control_command_all_command_types(self):
        """测试所有ControlCommand命令类型"""
        topic = "ginkgo.live.control.commands"

        command_types = [
            ("portfolio.create", "portfolio_001"),
            ("portfolio.delete", "portfolio_002"),
            ("portfolio.reload", "portfolio_003"),
            ("portfolio.start", "portfolio_004"),
            ("portfolio.stop", "portfolio_005"),
            ("engine.start", "engine_001"),
            ("engine.stop", "engine_002"),
        ]

        producer = GinkgoProducer()
        assert producer.is_connected

        # 发送所有类型的命令
        for cmd_type, target_id in command_types:
            cmd = ControlCommand(
                command_type=cmd_type,
                target_id=target_id,
                message_id=f"msg_{cmd_type}_{target_id}"
            )
            cmd_dict = cmd.to_dict()
            success = producer.send(topic, cmd_dict)
            assert success, f"Command type {cmd_type} should be sent successfully"

        producer.flush()

        # 验证所有命令都被接收
        consumer = GinkgoConsumer(topic, group_id="test_group_all_commands")
        assert consumer.is_connected

        received_commands = set()
        for message in consumer.consumer:
            received_cmd = ControlCommand.from_dict(message.value)
            received_commands.add(received_cmd.command_type)

            if len(received_commands) >= len(command_types):
                break

        # 验证所有命令类型都被接收
        expected_commands = {cmd_type for cmd_type, _ in command_types}
        assert received_commands == expected_commands, f"Expected {expected_commands}, got {received_commands}"

        # 清理
        consumer.close()
        producer.producer.close()

    def test_producer_async_send(self):
        """测试Producer异步发送"""
        topic = "ginkgo.live.market.data"
        # 使用唯一的测试标识符
        test_uuid = "test_async_send_unique"
        test_message = {"code": "000002.SZ", "price": 20.5, "volume": 2000, "test_uuid": test_uuid}

        producer = GinkgoProducer()
        assert producer.is_connected

        # 异步发送
        success = producer.send_async(topic, test_message)
        assert success, "Async send should succeed"

        # 等待消息到达
        time.sleep(1)

        # 验证消息到达
        consumer = GinkgoConsumer(topic, group_id="test_group_async_unique")
        assert consumer.is_connected

        message_received = False
        for message in consumer.consumer:
            received_message = message.value
            # 只处理我们发送的消息
            if received_message.get("test_uuid") == test_uuid:
                assert received_message["code"] == "000002.SZ"
                assert received_message["price"] == 20.5
                message_received = True
                break

        assert message_received, "Message should be received"

        # 清理
        consumer.close()
        producer.producer.close()

    def test_multiple_messages_batch(self):
        """测试批量发送多条消息"""
        topic = "ginkgo.live.market.data"
        # 使用唯一的测试批次标识
        batch_uuid = "test_batch_unique"

        messages = [
            {"code": "000001.SZ", "price": 10.0, "volume": 1000, "index": 0, "batch_uuid": batch_uuid},
            {"code": "000002.SZ", "price": 20.0, "volume": 2000, "index": 1, "batch_uuid": batch_uuid},
            {"code": "000003.SZ", "price": 30.0, "volume": 3000, "index": 2, "batch_uuid": batch_uuid},
            {"code": "000004.SZ", "price": 40.0, "volume": 4000, "index": 3, "batch_uuid": batch_uuid},
            {"code": "000005.SZ", "price": 50.0, "volume": 5000, "index": 4, "batch_uuid": batch_uuid},
        ]

        producer = GinkgoProducer()
        assert producer.is_connected

        # 批量发送
        for msg in messages:
            success = producer.send(topic, msg)
            assert success, f"Message {msg['index']} should be sent successfully"

        producer.flush()

        # 接收所有消息
        consumer = GinkgoConsumer(topic, group_id="test_group_batch_unique")
        assert consumer.is_connected

        received_messages = {}
        for message in consumer.consumer:
            received_msg = message.value
            # 只处理我们发送的消息
            if received_msg.get("batch_uuid") == batch_uuid:
                index = received_msg["index"]
                received_messages[index] = received_msg

                # 接收到所有消息后停止
                if len(received_messages) >= len(messages):
                    break

        # 验证所有消息都被正确接收
        assert len(received_messages) == len(messages), f"Expected {len(messages)} messages, got {len(received_messages)}"

        for expected_msg in messages:
            index = expected_msg["index"]
            received_msg = received_messages[index]
            assert received_msg["code"] == expected_msg["code"]
            assert received_msg["price"] == expected_msg["price"]
            assert received_msg["volume"] == expected_msg["volume"]

        # 清理
        consumer.close()
        producer.producer.close()

    def test_consumer_with_offset_earliest(self):
        """测试Consumer从最早的消息开始消费"""
        topic = "ginkgo.live.market.data"

        # 先发送一条消息
        producer = GinkgoProducer()
        test_message = {"code": "000001.SZ", "price": 10.5, "volume": 1000, "test": "offset"}
        producer.send(topic, test_message)
        producer.flush()

        # 创建Consumer，从earliest开始消费
        consumer = GinkgoConsumer(topic, group_id="test_group_offset", offset="earliest")
        assert consumer.is_connected

        # 应该能接收到之前发送的消息
        message_received = False
        for message in consumer.consumer:
            received_msg = message.value
            if received_msg.get("test") == "offset":
                assert received_msg["code"] == "000001.SZ"
                message_received = True
                break

        assert message_received, "Should receive message sent before consumer creation"

        # 清理
        consumer.close()
        producer.producer.close()


@pytest.mark.network
class TestKafkaConnectionManagement:
    """Kafka连接管理测试"""

    def test_producer_connection_status(self):
        """测试Producer连接状态检查"""
        producer = GinkgoProducer()
        # 如果Kafka未运行，连接会失败
        # 此时is_connected应该返回False
        assert isinstance(producer.is_connected, bool)
        if not producer.is_connected:
            print("WARNING: Kafka is not running, skipping connection test")
            return

        assert producer.is_connected is True

        # 关闭后重新创建
        if producer.producer:
            producer.producer.close()

    def test_consumer_connection_status(self):
        """测试Consumer连接状态检查"""
        topic = "ginkgo.live.control.commands"
        consumer = GinkgoConsumer(topic, group_id="test_group_connection")

        # 如果Kafka未运行，连接会失败
        if not consumer.is_connected:
            print("WARNING: Kafka is not running, skipping connection test")
            return

        assert consumer.is_connected is True
        assert consumer.topic == topic

        consumer.close()
        assert consumer.is_connected is False

    def test_consumer_commit(self):
        """测试Consumer手动提交offset"""
        topic = "ginkgo.live.market.data"

        # 发送消息
        producer = GinkgoProducer()
        if not producer.is_connected:
            print("WARNING: Kafka is not running, skipping commit test")
            return

        test_message = {"code": "000001.SZ", "price": 10.5, "volume": 1000, "test": "commit"}
        producer.send(topic, test_message)
        producer.flush()

        # 消费并提交
        consumer = GinkgoConsumer(topic, group_id="test_group_commit")
        assert consumer.is_connected

        for message in consumer.consumer:
            # 接收到消息
            received_msg = message.value
            if received_msg.get("test") == "commit":
                # 手动提交offset
                consumer.commit()
                break

        # 清理
        consumer.close()
        producer.producer.close()


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v", "-s"])
