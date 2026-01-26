# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: GinkgoKafka Kafka驱动提供Kafka连接和消息队列操作支持流式处理支持交易系统功能支持相关功能






import json
from time import sleep
from typing import Optional
from kafka import KafkaProducer, KafkaConsumer
from kafka.structs import TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import NoBrokersAvailable, KafkaConnectionError

from ginkgo.libs.core.config import GCONF
from ginkgo.libs import GLOG
from ginkgo.libs.core.logger import GinkgoLogger
from ginkgo.libs.utils.common import time_logger, retry
from ginkgo.interfaces.kafka_topics import KafkaTopics

data_logger = GinkgoLogger("ginkgo_data", ["ginkgo_data.log"])


class GinkgoProducer(object):
    def __init__(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),  # 消息序列化
                request_timeout_ms=10000,  # 10秒连接超时
                metadata_max_age_ms=300000,  # 5分钟元数据更新间隔
                retries=3,  # 自动重试3次
                acks='all',  # 等待所有ISR副本确认（实盘交易可靠性要求）
                max_in_flight_requests_per_connection=1,  # 保证消息顺序，防止重试时乱序
            )
            self._max_try = 5
            self._connected = True
            GLOG.INFO(f"Kafka Producer connected to {GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}")
            data_logger.INFO(f"Kafka Producer connected successfully")
        except (NoBrokersAvailable, KafkaConnectionError) as e:
            self._connected = False
            self.producer = None
            GLOG.ERROR(f"Kafka Producer connection failed: {e}")
            data_logger.ERROR(f"Failed to connect to Kafka at {GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}: {e}")
        except Exception as e:
            self._connected = False
            self.producer = None
            GLOG.ERROR(f"Kafka Producer initialization error: {e}")
            data_logger.ERROR(f"Unexpected error initializing Kafka Producer: {e}")

    @property
    def is_connected(self) -> bool:
        """检查 Producer 是否已连接"""
        return self._connected

    @property
    def max_try(self) -> int:
        return self._max_try

    @time_logger(threshold=1.0)
    @retry(max_try=3)
    def send(self, topic, msg):
        """
        同步发送消息（等待确认）

        Args:
            topic: Kafka topic
            msg: 消息内容

        Returns:
            bool: 发送是否成功
        """
        if not self._connected or self.producer is None:
            GLOG.ERROR("Kafka Producer not connected, cannot send message")
            data_logger.ERROR("Send failed: Kafka Producer not connected")
            return False

        try:
            future = self.producer.send(topic, msg)
            result = future.get(timeout=10)
            # result 是 RecordMetadata 对象，不需要打印
            GLOG.DEBUG(f"Kafka send message. TOPIC: {topic}. {msg}")
            data_logger.INFO(f"Kafka send message. TOPIC: {topic}. {msg}")
            return True
        except (NoBrokersAvailable, KafkaConnectionError) as e:
            GLOG.ERROR(f"Kafka connection error during send: {e}")
            data_logger.ERROR(f"Kafka send failed (connection error): {e}")
            self._connected = False  # 标记为断开连接
            return False
        except Exception as e:
            GLOG.ERROR(f"Kafka send msg failed. {e}")
            data_logger.ERROR(f"Kafka send msg failed. {e}")
            return False
        finally:
            if self.producer:
                self.producer.flush()

    @time_logger(threshold=0.5)
    @retry(max_try=3)
    def send_async(self, topic, msg):
        """
        异步发送消息（不等待确认）

        这是真正的 fire-and-forget 模式，不会阻塞调用者。

        Args:
            topic: Kafka topic
            msg: 消息内容

        Returns:
            bool: 发送是否成功（仅表示消息已加入发送队列）
        """
        if not self._connected or self.producer is None:
            GLOG.ERROR("Kafka Producer not connected, cannot send message asynchronously")
            data_logger.ERROR("Async send failed: Kafka Producer not connected")
            return False

        try:
            self.producer.send(topic, msg)
            GLOG.DEBUG(f"Kafka async send message. TOPIC: {topic}")
            return True
        except (NoBrokersAvailable, KafkaConnectionError) as e:
            GLOG.ERROR(f"Kafka connection error during async send: {e}")
            data_logger.ERROR(f"Kafka async send failed (connection error): {e}")
            self._connected = False  # 标记为断开连接
            return False
        except Exception as e:
            GLOG.ERROR(f"Kafka async send failed. {e}")
            data_logger.ERROR(f"Kafka async send failed: {e}")
            return False

    @time_logger(threshold=0.3)
    def flush(self, timeout: Optional[float] = None):
        """
        刷新 Kafka Producer 缓冲区

        确保所有已发送的消息被传输到 Kafka 服务器。
        用于程序退出前确保消息不丢失。

        Args:
            timeout: 超时时间（秒），None 表示使用默认超时
        """
        try:
            self.producer.flush(timeout=timeout)
            GLOG.DEBUG(f"Kafka producer flushed (timeout={timeout})")
        except Exception as e:
            GLOG.ERROR(f"Kafka flush failed: {e}")

    def close(self, timeout: Optional[float] = None):
        """
        关闭 Kafka Producer 连接

        先 flush 确保所有消息发送完成，然后关闭连接。
        用于程序退出时优雅关闭。

        Args:
            timeout: 超时时间（秒），None 表示使用默认超时
        """
        if self.producer:
            try:
                # 先 flush 确保消息发送完成
                self.producer.flush(timeout=timeout)
                # 关闭 producer
                self.producer.close(timeout=timeout)
                self._connected = False
                GLOG.INFO("Kafka Producer closed")
                data_logger.INFO("Kafka Producer closed successfully")
            except Exception as e:
                GLOG.ERROR(f"Error closing Kafka Producer: {e}")
                data_logger.ERROR(f"Failed to close Kafka Producer: {e}")


class GinkgoConsumer(object):
    def __init__(self, topic: str, group_id: str = "", offset: str = "earliest"):
        self.consumer = None
        self._connected = False
        self._topic = topic

        try:
            if group_id == "":
                self.consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
                    auto_offset_reset=offset,  # 从最早的消息开始消费
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),  # 消息反序列化
                    max_poll_interval_ms=1800000,
                    max_poll_records=1,
                    request_timeout_ms=40000,  # 40秒连接超时 (必须大于 session_timeout_ms)
                    session_timeout_ms=30000,  # 30秒会话超时
                    heartbeat_interval_ms=3000,  # 3秒心跳间隔
                )
            else:
                self.consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
                    group_id=group_id,
                    auto_offset_reset=offset,  # 从最早的消息开始消费
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),  # 消息反序列化
                    max_poll_interval_ms=1800000,
                    max_poll_records=1,
                    request_timeout_ms=40000,  # 40秒连接超时 (必须大于 session_timeout_ms)
                    session_timeout_ms=30000,  # 30秒会话超时
                    heartbeat_interval_ms=3000,  # 3秒心跳间隔
                )
            self._connected = True
            GLOG.INFO(f"Kafka Consumer connected to topic '{topic}' (group_id={group_id or 'none'})")
            data_logger.INFO(f"Kafka Consumer connected successfully to topic: {topic}")
        except (NoBrokersAvailable, KafkaConnectionError) as e:
            self._connected = False
            self.consumer = None
            GLOG.ERROR(f"Kafka Consumer connection failed: {e}")
            data_logger.ERROR(f"Failed to connect to Kafka topic '{topic}': {e}")
        except Exception as e:
            self._connected = False
            self.consumer = None
            GLOG.ERROR(f"Kafka Consumer initialization error: {e}")
            data_logger.ERROR(f"Unexpected error initializing Kafka Consumer: {e}")

    @property
    def is_connected(self) -> bool:
        """检查 Consumer 是否已连接"""
        return self._connected

    @property
    def topic(self) -> str:
        """获取订阅的 topic"""
        return self._topic

    @time_logger(threshold=0.2)
    @retry(max_try=3)
    def commit(self):
        """提交当前 offset"""
        if self.consumer and self._connected:
            try:
                self.consumer.commit()
            except Exception as e:
                GLOG.ERROR(f"Kafka commit failed: {e}")
                data_logger.ERROR(f"Failed to commit Kafka offset: {e}")

    def close(self):
        """关闭 consumer 连接"""
        if self.consumer:
            try:
                self.consumer.close()
                self._connected = False
                GLOG.INFO(f"Kafka Consumer closed for topic '{self._topic}'")
                data_logger.INFO(f"Kafka Consumer closed: {self._topic}")
            except Exception as e:
                GLOG.ERROR(f"Error closing Kafka Consumer: {e}")
                data_logger.ERROR(f"Failed to close Kafka Consumer: {e}")


def kafka_topic_set():
    # 创建 KafkaAdminClient 实例
    admin_client = KafkaAdminClient(
        bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
        client_id="admin",
    )
    if admin_client is None:
        print("Can not connect to kafka now. Please try later.")
        return

    # 定义 topic 配置：分区数和副本数
    topic_config = {
        "ginkgo.data.update": (24, 1),
        "ginkgo.data.commands": (3, 1),  # 新增：数据采集命令专用
        "ginkgo.notifications": (3, 1),
        "ginkgo.live.market.data": (24, 1),
        "ginkgo.live.market.data.cn": (24, 1),
        "ginkgo.live.market.data.hk": (24, 1),
        "ginkgo.live.market.data.us": (24, 1),
        "ginkgo.live.market.data.futures": (24, 1),
        "ginkgo.live.interest.updates": (12, 1),
        "ginkgo.live.orders.submission": (24, 1),
        "ginkgo.live.orders.feedback": (12, 1),
        "ginkgo.live.control.commands": (3, 1),
        "ginkgo.schedule.updates": (3, 1),
        "ginkgo.live.schedule.updates": (3, 1),
        "ginkgo.live.system.events": (3, 1),
    }

    # 获取当前 Kafka 中所有的 topics
    existing_topics = set(str(t) for t in admin_client.list_topics())

    # 删除所有 topics（除了内部 topic）
    topics_to_delete = existing_topics.copy()
    topics_to_delete.discard("__consumer_offsets")  # 保留内部 topic

    if topics_to_delete:
        print(f"Deleting all {len(topics_to_delete)} topics for reset...")
        for topic in sorted(topics_to_delete):
            try:
                admin_client.delete_topics(topics=[topic], timeout_ms=30000)
                print(f"  ✓ Deleted topic: {topic}")
                sleep(0.5)
            except Exception as e:
                print(f"  ✗ Failed to delete topic {topic}: {e}")
        print()  # 空行分隔

    # 创建新 topics（逐个创建以避免部分失败导致整体失败）
    print(f"\nCreating {len(topic_config)} topics...")
    for topic_name, (partitions, replication) in topic_config.items():
        try:
            result = admin_client.create_topics(
                new_topics=[NewTopic(name=topic_name, num_partitions=partitions, replication_factor=replication)],
                validate_only=False
            )

            # 检查创建结果
            # result.topic_errors 可能是 dict 或 list
            topic_errors = result.topic_errors
            if isinstance(topic_errors, dict):
                for topic, future in topic_errors.items():
                    if future.error_code == 0:
                        print(f"  ✓ Created topic: {topic}")
                    elif future.error_code == 36:  # TopicAlreadyExistsError
                        print(f"  ⊙ Topic already exists: {topic}")
                    else:
                        print(f"  ✗ Failed to create topic {topic}: {future.error_message}")
            elif isinstance(topic_errors, list) and topic_errors:
                # 格式: [(topic_name, error_code, error_message), ...]
                for item in topic_errors:
                    if len(item) >= 2:
                        topic, error_code = item[0], item[1]
                        if error_code == 0:
                            print(f"  ✓ Created topic: {topic}")
                        elif error_code == 36:
                            print(f"  ⊙ Topic already exists: {topic}")
                        else:
                            error_msg = item[2] if len(item) > 2 else "Unknown error"
                            print(f"  ✗ Failed to create topic {topic}: {error_msg}")
            else:
                # 未知格式，尝试检查异常
                print(f"  ⚠ Topic {topic_name}: {topic_errors}")

        except Exception as e:
            error_msg = str(e)
            if "TopicAlreadyExistsError" in error_msg or "already exists" in error_msg.lower():
                print(f"  ⊙ Topic already exists: {topic_name}")
            else:
                print(f"  ✗ Failed to create topic {topic_name}: {e}")

    admin_client.close()


def kafka_topic_llen(topic: str):
    bootstrap_servers = f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"  # Kafka集群地址
    # 您想要查询的topic名称
    topic_name = str(topic)

    # 创建Kafka消费者实例
    consumer = KafkaConsumer(bootstrap_servers=bootstrap_servers)
    # 获取topic的所有分区
    partitions = consumer.partitions_for_topic(topic_name)
    # 初始化消息总数
    if partitions is None:
        return 0
    total_messages = 0

    # 遍历每个分区
    for partition in partitions:
        # 创建TopicPartition实例
        topic_partition = TopicPartition(topic=topic_name, partition=partition)
        # 分配分区给消费者
        consumer.assign([topic_partition])
        # 获取该分区的起始和结束offset
        start_offset = consumer.beginning_offsets([topic_partition])[topic_partition]
        end_offset = consumer.end_offsets([topic_partition])[topic_partition]
        # 计算该分区的消息总数
        # total_messages += end_offset - start_offset

        current_offset = consumer.position(topic_partition)
        total_messages += end_offset - current_offset

    # 打印消息总数
    print(f'The total number of messages in topic "{topic_name}" is: {total_messages}')
    return total_messages


def kafka_consumer_count(topic: str) -> int:
    bootstrap_servers = f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"  # Kafka集群地址
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
    )
    subscription = consumer.subscription()
    # 获取消费者数量
    consumer_count = len(subscription)
    return consumer_count


def get_unconsumed_message(topic: str) -> int:
    bootstrap_servers = f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"  # Kafka集群地址
    consumer = KafkaConsumer(bootstrap_servers=bootstrap_servers)
    partitions = consumer.partitions_for_topic(topic)
    if partitions is None:
        return 0

    total_message_count = 0

    # 遍历每个分区，获取分区中的消息数量并累加
    for partition in partitions:
        topic_partition = TopicPartition(topic=topic, partition=partition)
        consumer.assign([topic_partition])
        consumer.seek_to_beginning(topic_partition)
        beginning_offset = consumer.position(topic_partition)
        consumer.seek_to_end(topic_partition)
        end_offset = consumer.position(topic_partition)
        message_count = end_offset - beginning_offset
        total_message_count += message_count

    # 关闭消费者连接
    consumer.close()

    return total_message_count
