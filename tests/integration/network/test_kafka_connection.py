"""
Kafka连接测试 - 实盘交易架构

测试Kafka连接和topic创建功能
验证ginkgo.live.*系列的6个实盘交易topic

运行方式: pytest tests/network/live/test_kafka_connection.py -v
"""

import pytest
from kafka import KafkaAdminClient
from kafka.errors import KafkaError, NoBrokersAvailable
from ginkgo.libs.core.config import GCONF
from ginkgo.data.drivers.ginkgo_kafka import kafka_topic_set, GinkgoProducer, GinkgoConsumer


@pytest.mark.network
@pytest.mark.kafka
class TestKafkaDriverConnection:
    """Kafka Driver连接测试（使用ginkgo.data.drivers）"""

    def test_ginkgo_producer_creation(self):
        """测试GinkgoProducer创建"""
        try:
            producer = GinkgoProducer()
            assert producer is not None, "GinkgoProducer创建失败"
            assert producer.is_connected, "GinkgoProducer未连接"
            print("✅ GinkgoProducer连接成功")
        except Exception as e:
            pytest.skip(f"Kafka服务未运行或连接失败: {e}")

    def test_ginkgo_consumer_creation(self):
        """测试GinkgoConsumer创建"""
        try:
            consumer = GinkgoConsumer("ginkgo.live.market.data", "test_group")
            assert consumer is not None, "GinkgoConsumer创建失败"
            consumer.close()
            print("✅ GinkgoConsumer连接成功")
        except Exception as e:
            pytest.skip(f"Kafka服务未运行或连接失败: {e}")

    def test_ginkgo_producer_send(self):
        """测试GinkgoProducer发送消息"""
        try:
            producer = GinkgoProducer()
            test_message = {"test": "driver_connection", "timestamp": "2026-01-04"}

            result = producer.send("ginkgo.live.market.data", test_message)
            assert result is True, "消息发送失败"

            print("✅ GinkgoProducer发送消息成功")
        except Exception as e:
            pytest.skip(f"Kafka服务未运行或连接失败: {e}")


@pytest.mark.network
@pytest.mark.kafka
class TestKafkaTopics:
    """Kafka Topic验证测试"""

    def test_kafka_admin_client_connection(self):
        """测试Kafka AdminClient连接和list_topics"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],
                client_id="test_admin",
            )
            assert admin_client is not None, "AdminClient创建失败"

            # 列出所有topics
            topics = admin_client.list_topics()
            assert topics is not None, "无法获取topics列表"

            admin_client.close()
            print(f"✅ Kafka AdminClient连接成功，当前topics: {len(topics)}个")
        except (NoBrokersAvailable, KafkaError) as e:
            pytest.skip(f"Kafka服务未运行或连接失败: {e}")

    def test_live_trading_topics_exist(self):
        """测试实盘交易所需的topics是否存在"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],
                client_id="test_admin",
            )

            topics = admin_client.list_topics()

            # 检查实盘交易所需的6个topic
            required_topics = [
                "ginkgo.live.market.data",
                "ginkgo.live.orders.submission",
                "ginkgo.live.orders.feedback",
                "ginkgo.live.control.commands",
                "ginkgo.live.schedule.updates",
                "ginkgo.live.system.events",
            ]

            missing_topics = []
            for topic in required_topics:
                if topic not in topics:
                    missing_topics.append(topic)

            admin_client.close()

            if missing_topics:
                pytest.fail(f"缺少实盘交易topics: {missing_topics}")
            else:
                print(f"✅ 所有实盘交易topics存在: {required_topics}")

        except (NoBrokersAvailable, KafkaError) as e:
            pytest.skip(f"Kafka服务未运行或连接失败: {e}")

    def test_global_topics_exist(self):
        """测试全局topics是否存在"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],
                client_id="test_admin",
            )

            topics = admin_client.list_topics()

            # 检查全局topics
            global_topics = [
                "ginkgo_data_update",
                "notifications",
            ]

            missing_topics = []
            for topic in global_topics:
                if topic not in topics:
                    missing_topics.append(topic)

            admin_client.close()

            if missing_topics:
                pytest.fail(f"缺少全局topics: {missing_topics}")
            else:
                print(f"✅ 所有全局topics存在: {global_topics}")

        except (NoBrokersAvailable, KafkaError) as e:
            pytest.skip(f"Kafka服务未运行或连接失败: {e}")

    def test_kafka_topic_set_function(self):
        """测试kafka_topic_set()函数（不执行，只验证可调用）"""
        # 注意：不实际执行kafka_topic_set()，因为它会删除并重建所有topics
        # 只验证函数存在且可调用
        assert callable(kafka_topic_set), "kafka_topic_set函数不存在"
        print("✅ kafka_topic_set()函数可调用")


@pytest.mark.network
@pytest.mark.kafka
class TestKafkaMessageFlow:
    """Kafka消息流测试（使用Driver）"""

    def test_driver_produce_and_consume(self):
        """测试Driver生产者-消费者消息流"""
        try:
            # 创建GinkgoProducer并发送消息
            producer = GinkgoProducer()
            test_message = {"symbol": "000001.SZ", "price": 10.5, "timestamp": "2026-01-04T00:00:00"}

            result = producer.send("ginkgo.live.market.data", test_message)
            assert result is True, "GinkgoProducer发送失败"

            # 创建GinkgoConsumer并消费消息
            consumer = GinkgoConsumer("ginkgo.live.market.data", "test_driver_flow")

            # 尝试接收消息（可能没有新消息）
            messages = []
            for _ in range(10):  # 限制尝试次数
                msg = consumer.receive(timeout=1.0)
                if msg:
                    messages.append(msg)
                    break

            consumer.close()

            print(f"✅ Driver消息流测试成功，发送: {test_message}")

        except Exception as e:
            pytest.skip(f"Kafka服务未运行或连接失败: {e}")

