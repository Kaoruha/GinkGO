"""
KafkaService集成测试

测试Kafka消息队列服务的核心功能和接口
使用真实的Kafka服务进行集成测试
"""

import unittest
import time
import json
import uuid
import threading
from datetime import datetime
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.structs import TopicPartition

from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.data.crud.kafka_crud import KafkaCRUD


class TestKafkaService(unittest.TestCase):
    """KafkaService集成测试类"""

    @classmethod
    def setUpClass(cls):
        """整个测试类开始前的设置"""
        cls.test_topics = []
        cls.admin_client = None

        try:
            # 创建Admin客户端用于管理主题
            cls.admin_client = KafkaAdminClient(
                bootstrap_servers=['localhost:9092'],
                client_id='test_admin'
            )
        except Exception as e:
            print(f"警告: 无法连接Kafka AdminClient: {e}")

    @classmethod
    def tearDownClass(cls):
        """整个测试类结束后的清理"""
        if cls.admin_client:
            try:
                # 获取所有主题，找出测试主题并清理
                all_topics = list(cls.admin_client.list_topics())
                test_patterns = ['dynamic_', 'concurrent_test_', 'format_test_', 'subscription_test_', 'live_topic_']

                test_topics_to_clean = []
                for topic in all_topics:
                    for pattern in test_patterns:
                        if pattern in topic:
                            test_topics_to_clean.append(topic)
                            break

                if test_topics_to_clean:
                    # 分批清理测试主题
                    batch_size = 20
                    for i in range(0, len(test_topics_to_clean), batch_size):
                        batch = test_topics_to_clean[i:i + batch_size]
                        try:
                            cls.admin_client.delete_topics(batch, timeout_ms=15000)
                            print(f"已清理测试主题批次 {i//batch_size + 1}: {len(batch)}个主题")
                        except Exception as e:
                            print(f"清理主题批次失败: {e}")

                # 清理类级别记录的主题
                if cls.test_topics:
                    try:
                        cls.admin_client.delete_topics(cls.test_topics, timeout_ms=10000)
                        print(f"已清理类级别测试主题: {cls.test_topics}")
                    except Exception as e:
                        print(f"清理类级别主题时出错: {e}")

            except Exception as e:
                print(f"清理过程出错: {e}")
            finally:
                try:
                    cls.admin_client.close()
                except:
                    pass

    def setUp(self):
        """每个测试方法执行前的设置"""
        # 使用真实的KafkaService
        self.kafka_service = KafkaService()
        self.test_topic = f"test_topic_{uuid.uuid4().hex[:8]}"
        self.test_topics_created = []

    def tearDown(self):
        """每个测试方法执行后的清理"""
        # 清理当前测试创建的主题
        if self.admin_client and self.test_topics_created:
            try:
                self.admin_client.delete_topics(self.test_topics_created, timeout_ms=10000)
                print(f"已清理测试主题: {self.test_topics_created}")
            except Exception as e:
                print(f"清理测试主题时出错: {e}")

        # 等待一小段时间确保资源释放
        time.sleep(0.1)

    def _create_test_topic(self, topic_name: str):
        """创建测试主题的辅助方法"""
        if self.admin_client and topic_name not in self.test_topics_created:
            try:
                topic_list = [NewTopic(name=topic_name, num_partitions=3, replication_factor=1)]
                self.admin_client.create_topics(topic_list, validate_only=False)
                self.test_topics_created.append(topic_name)
                # 添加到类级别的主题列表用于最终清理
                self.__class__.test_topics.append(topic_name)
                time.sleep(1)  # 等待主题创建完成
            except Exception as e:
                print(f"创建测试主题失败 {topic_name}: {e}")

    # ==================== 初始化测试 ====================

    def test_init_with_provided_crud(self):
        """测试使用提供的KafkaCRUD初始化"""
        kafka_crud = KafkaCRUD()
        service = KafkaService(kafka_crud=kafka_crud)

        self.assertEqual(service._crud_repo, kafka_crud)
        self.assertEqual(service.service_name, "KafkaService")
        self.assertEqual(service.kafka, kafka_crud)

    def test_init_with_auto_crud_creation(self):
        """测试自动创建KafkaCRUD"""
        service = KafkaService()

        self.assertIsInstance(service._crud_repo, KafkaCRUD)
        self.assertIsNotNone(service._crud_repo)
        self.assertEqual(service.service_name, "KafkaService")

    # ==================== 标准接口测试 ====================

    def test_get_all_topics(self):
        """测试获取所有主题信息"""
        # 创建测试主题
        self._create_test_topic(self.test_topic)

        result = self.kafka_service.get()

        self.assertTrue(result.success)
        self.assertIsInstance(result.data, dict)
        self.assertIn('topics', result.data)
        self.assertIn('count', result.data)
        # 应该至少包含我们创建的测试主题
        self.assertGreaterEqual(result.data['count'], 1)

    def test_validate_valid_topic(self):
        """测试验证有效主题"""
        topic = "valid_topic"
        result = self.kafka_service.validate(topic=topic)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Kafka数据验证通过")

    def test_validate_empty_topic(self):
        """测试验证空主题"""
        result = self.kafka_service.validate(topic="")

        self.assertFalse(result.success)
        self.assertIn("不能为空", result.error)

    def test_validate_invalid_topic_type(self):
        """测试验证无效主题类型"""
        result = self.kafka_service.validate(topic=123)

        self.assertFalse(result.success)
        self.assertIn("必须是字符串", result.error)

    # ==================== 消息队列操作测试 ====================

    def test_publish_message(self):
        """测试发布消息"""
        # 创建测试主题
        self._create_test_topic(self.test_topic)

        message = {"event": "price_update", "symbol": "AAPL", "price": 150.0}

        result = self.kafka_service.publish_message(self.test_topic, message)

        self.assertTrue(result)

    def test_publish_message_with_key(self):
        """测试带键发布消息"""
        # 创建测试主题
        self._create_test_topic(self.test_topic)

        message = "test message"
        key = "test_key"

        result = self.kafka_service.publish_message(self.test_topic, message, key=key)

        self.assertTrue(result)

    def test_count_all_topics(self):
        """测试统计所有主题数量"""
        # 创建测试主题
        self._create_test_topic(self.test_topic)

        result = self.kafka_service.count()

        self.assertTrue(result.success)
        self.assertIsInstance(result.data, dict)
        self.assertIn('topic_count', result.data)
        # 应该至少包含我们创建的测试主题
        self.assertGreaterEqual(result.data['topic_count'], 1)

    # ==================== 未消费消息查询测试 ====================

    def test_get_unconsumed_messages_count(self):
        """测试查询未消费消息数量"""
        # 创建测试主题
        self._create_test_topic(self.test_topic)

        # 发送一些测试消息
        for i in range(3):
            message = f"test_message_{i}"
            self.kafka_service.publish_message(self.test_topic, message)

        # 等待消息发送完成
        time.sleep(1)

        result = self.kafka_service.get_unconsumed_messages_count(self.test_topic)

        self.assertTrue(result.success)
        self.assertIsInstance(result.data, dict)
        self.assertIn('topic', result.data)
        self.assertIn('group_id', result.data)
        self.assertIn('total_messages', result.data)
        self.assertIn('unconsumed_messages', result.data)

    def test_get_unconsumed_messages_count_no_topic(self):
        """测试查询不存在主题的未消费消息"""
        topic = "nonexistent_topic_test"
        result = self.kafka_service.get_unconsumed_messages_count(topic)

        self.assertFalse(result.success)
        self.assertIn("不存在", result.error)

    def test_get_consumer_group_lag(self):
        """测试消费者组延迟查询"""
        # 创建测试主题
        self._create_test_topic(self.test_topic)

        # 发送一些测试消息
        for i in range(2):
            message = f"lag_test_message_{i}"
            self.kafka_service.publish_message(self.test_topic, message)

        # 等待消息发送完成
        time.sleep(1)

        result = self.kafka_service.get_consumer_group_lag(self.test_topic)

        self.assertTrue(result.success)
        self.assertIsInstance(result.data, dict)
        self.assertIn('topic', result.data)
        self.assertIn('group_id', result.data)
        self.assertIn('unconsumed_messages', result.data)
        self.assertIn('lag_level', result.data)

    def test_calculate_lag_level_by_count(self):
        """测试基于消息数量的延迟级别计算"""
        # 测试各种延迟级别
        self.assertEqual(self.kafka_service._calculate_lag_level(0), "无延迟")
        self.assertEqual(self.kafka_service._calculate_lag_level(50), "低延迟")
        self.assertEqual(self.kafka_service._calculate_lag_level(500), "中等延迟")
        self.assertEqual(self.kafka_service._calculate_lag_level(1500), "高延迟")

    def test_calculate_lag_level_by_time(self):
        """测试基于时间的延迟级别计算"""
        # 模拟不同时间延迟
        self.assertEqual(self.kafka_service._calculate_lag_level(100, 0.5), "无延迟")
        self.assertEqual(self.kafka_service._calculate_lag_level(100, 5), "低延迟")
        self.assertEqual(self.kafka_service._calculate_lag_level(100, 30), "中等延迟")
        self.assertEqual(self.kafka_service._calculate_lag_level(100, 120), "高延迟")

    def test_get_queue_metrics(self):
        """测试队列指标获取"""
        # 创建测试主题
        self._create_test_topic(self.test_topic)

        result = self.kafka_service.get_queue_metrics([self.test_topic])

        self.assertIsInstance(result, dict)
        self.assertIn("timestamp", result)
        self.assertIn("topics", result)

        if self.test_topic in result["topics"]:
            topic_info = result["topics"][self.test_topic]
            self.assertIn("unconsumed_messages", topic_info)
            self.assertIn("consumer_lag", topic_info)

    # ==================== 动态主题管理测试 ====================

    def test_dynamic_topic_creation_and_publishing(self):
        """测试动态主题创建和消息发布"""
        dynamic_topics = []
        messages_published = 0

        try:
            # 动态创建3个主题并发布消息
            for i in range(3):
                dynamic_topic = f"dynamic_test_topic_{i}_{uuid.uuid4().hex[:8]}"
                dynamic_topics.append(dynamic_topic)

                # 发布消息到动态主题（Kafka应该自动创建主题）
                test_message = {
                    "event": "dynamic_creation",
                    "sequence": i + 1,
                    "data": f"dynamic_message_{i + 1}",
                    "timestamp": datetime.now().isoformat()
                }

                result = self.kafka_service.publish_message(dynamic_topic, test_message)
                self.assertTrue(result, f"发布到动态主题{dynamic_topic}应该成功")
                messages_published += 1

                # 等待消息发送完成
                time.sleep(0.5)

            # 验证主题存在
            all_topics_result = self.kafka_service.get()
            self.assertTrue(all_topics_result.success)

            all_topics = all_topics_result.data["topics"]

            # 验证动态主题是否在列表中
            found_topics = 0
            for topic in dynamic_topics:
                if topic in all_topics:
                    found_topics += 1

            self.assertEqual(found_topics, len(dynamic_topics),
                           "所有动态创建的主题都应该存在")

            # 验证每个主题都有消息
            for topic in dynamic_topics:
                count_result = self.kafka_service.count(topic=topic)
                self.assertTrue(count_result.success)
                self.assertGreater(count_result.data["message_count"], 0,
                                  f"主题{topic}应该有消息")

        finally:
            # 清理动态创建的主题
            cleanup_errors = []
            for topic in dynamic_topics:
                try:
                    self.kafka_service.stop_consuming(topic)
                    self.kafka_service.unsubscribe_topic(topic)

                    if self.admin_client:
                        # 尝试删除主题
                        self.admin_client.delete_topics([topic], timeout_ms=15000)
                except Exception as e:
                    cleanup_errors.append(f"清理主题{topic}失败: {e}")
                    # 记录错误但不中断测试

            if cleanup_errors:
                # 打印清理错误但不让测试失败
                print(f"清理警告: {'; '.join(cleanup_errors[:3])}")  # 只显示前3个错误

    def test_dynamic_subscription_and_consumption(self):
        """测试动态订阅和消息消费"""
        dynamic_topic = f"dynamic_subscription_test_{uuid.uuid4().hex[:8]}"
        received_messages = []
        consumption_started = threading.Event()

        # 定义消息处理器
        def message_handler(message_data):
            nonlocal received_messages
            try:
                received_messages.append(message_data)
                consumption_started.set()

                data = message_data.get("value", {})
                expected_data = data.get("test_data", "")

                # 验证消息格式
                self.assertIn("test_data", data)
                self.assertIn("sequence", data)

                return True
            except Exception as e:
                print(f"消息处理错误: {e}")
                return False

        try:
            # 订阅动态主题（主题可能还不存在）
            subscription_success = self.kafka_service.subscribe_topic(
                topic=dynamic_topic,
                handler=message_handler,
                group_id="dynamic_test_group",
                auto_start=True
            )
            self.assertTrue(subscription_success, "订阅动态主题应该成功")

            # 等待订阅准备就绪
            time.sleep(1)

            # 发送测试消息到动态主题
            test_messages = []
            for i in range(3):
                test_message = {
                    "test_data": f"dynamic_subscription_test_{i + 1}",
                    "sequence": i + 1,
                    "timestamp": datetime.now().isoformat()
                }
                test_messages.append(test_message)

                result = self.kafka_service.publish_message(dynamic_topic, test_message)
                self.assertTrue(result, f"发送消息{i + 1}到动态主题应该成功")

                # 等待消息处理
                time.sleep(1)

            # 等待所有消息被消费
            max_wait_time = 10  # 最大等待10秒
            wait_interval = 0.5
            elapsed_time = 0

            while len(received_messages) < len(test_messages) and elapsed_time < max_wait_time:
                time.sleep(wait_interval)
                elapsed_time += wait_interval

            # 验证消息消费结果
            self.assertEqual(len(received_messages), len(test_messages),
                           f"应该收到{len(test_messages)}条消息，实际收到{len(received_messages)}条")

            # 验证消息内容
            for i, received_msg in enumerate(received_messages):
                received_data = received_msg.get("value", {})
                expected_data = test_messages[i]

                self.assertEqual(received_data.get("test_data"),
                               expected_data.get("test_data"))
                self.assertEqual(received_data.get("sequence"),
                               expected_data.get("sequence"))

        finally:
            # 清理资源
            try:
                self.kafka_service.stop_consuming(dynamic_topic)
                self.kafka_service.unsubscribe_topic(dynamic_topic)
                if self.admin_client:
                    self.admin_client.delete_topics([dynamic_topic], timeout_ms=10000)
            except Exception:
                pass

    def test_multiple_dynamic_topics_concurrent_consumption(self):
        """测试多个动态主题并发消费"""
        dynamic_topics = []
        message_handlers = {}
        received_counts = {}
        num_topics = 3
        messages_per_topic = 2

        try:
            # 创建多个动态主题和对应的处理器
            for i in range(num_topics):
                topic = f"concurrent_test_topic_{i}_{uuid.uuid4().hex[:6]}"
                dynamic_topics.append(topic)
                received_counts[topic] = 0

                # 为每个主题创建专用处理器
                def make_handler(topic_index):
                    def handler(message_data):
                        nonlocal received_counts
                        topic_name = f"concurrent_test_topic_{topic_index}_{dynamic_topics[topic_index].split('_')[-1]}"
                        received_counts[topic_name] += 1
                        return True
                    return handler

                handler = make_handler(i)
                message_handlers[topic] = handler

                # 订阅主题
                subscription_success = self.kafka_service.subscribe_topic(
                    topic=topic,
                    handler=handler,
                    group_id=f"concurrent_group_{i}",
                    auto_start=True
                )
                self.assertTrue(subscription_success, f"订阅主题{topic}应该成功")

            # 等待订阅准备完成
            time.sleep(2)

            # 向每个主题发送多条消息
            for i, topic in enumerate(dynamic_topics):
                for j in range(messages_per_topic):
                    message = {
                        "topic_index": i,
                        "message_index": j,
                        "data": f"message_topic_{i}_msg_{j}",
                        "timestamp": datetime.now().isoformat()
                    }

                    result = self.kafka_service.publish_message(topic, message)
                    self.assertTrue(result, f"发送消息到主题{topic}应该成功")

            # 等待消息消费完成
            max_wait_time = 15
            wait_interval = 1
            elapsed_time = 0

            # 检查是否所有消息都被消费
            expected_total = num_topics * messages_per_topic
            actual_total = sum(received_counts.values())

            while actual_total < expected_total and elapsed_time < max_wait_time:
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                actual_total = sum(received_counts.values())

            # 验证消费结果
            self.assertEqual(actual_total, expected_total,
                           f"应该总共收到{expected_total}条消息，实际收到{actual_total}条")

            # 验证每个主题都收到了正确数量的消息
            for topic in dynamic_topics:
                self.assertEqual(received_counts[topic], messages_per_topic,
                               f"主题{topic}应该收到{messages_per_topic}条消息")

        finally:
            # 清理所有资源
            for topic in dynamic_topics:
                try:
                    self.kafka_service.stop_consuming(topic)
                    self.kafka_service.unsubscribe_topic(topic)
                    if self.admin_client:
                        self.admin_client.delete_topics([topic], timeout_ms=10000)
                except Exception:
                    pass

    def test_dynamic_topic_with_different_message_formats(self):
        """测试动态主题支持不同消息格式"""
        dynamic_topic = f"format_test_topic_{uuid.uuid4().hex[:8]}"
        received_messages = []

        def format_test_handler(message_data):
            nonlocal received_messages
            received_messages.append(message_data)
            return True

        try:
            # 订阅动态主题
            subscription_success = self.kafka_service.subscribe_topic(
                topic=dynamic_topic,
                handler=format_test_handler,
                group_id="format_test_group",
                auto_start=True
            )
            self.assertTrue(subscription_success)

            time.sleep(1)  # 等待订阅准备完成

            # 测试不同格式的消息
            test_messages = [
                # 字符串格式
                "simple_string_message",

                # JSON对象格式
                {"event": "json_test", "data": "json_value", "number": 123},

                # 复杂嵌套格式
                {
                    "event_type": "complex_event",
                    "payload": {
                        "user": {"id": 1, "name": "test_user"},
                        "actions": ["action1", "action2"],
                        "metadata": {"timestamp": datetime.now().isoformat()}
                    }
                },

                # 数组格式
                [1, 2, 3, "array_value", {"nested": "object"}],

                # 数值格式
                42.5
            ]

            # 发送不同格式的消息
            for i, message in enumerate(test_messages):
                result = self.kafka_service.publish_message(dynamic_topic, message)
                self.assertTrue(result, f"发送{i+1}号消息到动态主题应该成功")
                time.sleep(0.5)

            # 等待消息消费
            time.sleep(5)

            # 验证消息接收
            self.assertEqual(len(received_messages), len(test_messages),
                           f"应该收到{len(test_messages)}条消息，实际收到{len(received_messages)}条")

            # 验证消息格式保持不变
            for i, received_msg in enumerate(received_messages):
                original_msg = test_messages[i]
                received_value = received_msg.get("value")

                # 验证消息内容一致（注意：JSON序列化可能会有类型转换）
                if isinstance(original_msg, str):
                    self.assertIsInstance(received_value, dict)
                    self.assertIn("content", received_value)
                elif isinstance(original_msg, (dict, list)):
                    # 对于复杂对象，检查关键结构
                    self.assertIsNotNone(received_value)
                elif isinstance(original_msg, (int, float)):
                    # 数值类型会被包装成字典格式
                    if isinstance(received_value, dict):
                        self.assertEqual(received_value.get("content"), original_msg)
                    else:
                        self.assertEqual(received_value, original_msg)

        finally:
            # 清理资源
            try:
                self.kafka_service.stop_consuming(dynamic_topic)
                self.kafka_service.unsubscribe_topic(dynamic_topic)
                if self.admin_client:
                    self.admin_client.delete_topics([dynamic_topic], timeout_ms=10000)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()