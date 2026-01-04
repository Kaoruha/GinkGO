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
                acks=1,  # 等待leader确认
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
            print(result)
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

    # 创建一个新主题的配置
    topic_list = []

    # === 全局Topics (回测、通知等) ===
    topic_list.append(NewTopic(name="ginkgo_data_update", num_partitions=24, replication_factor=1))
    topic_list.append(NewTopic(name="notifications", num_partitions=3, replication_factor=1))

    # === 实盘交易架构Topics (007-live-trading-architecture) ===

    # 市场数据Topic (所有市场：A股、港股、美股、期货，通过消息中的market字段区分)
    topic_list.append(NewTopic(name="ginkgo.live.market.data", num_partitions=24, replication_factor=1))

    # 订单Topics (高并发，需要更多分区)
    topic_list.append(NewTopic(name="ginkgo.live.orders.submission", num_partitions=24, replication_factor=1))  # 订单提交
    topic_list.append(NewTopic(name="ginkgo.live.orders.feedback", num_partitions=12, replication_factor=1))  # 订单回报

    # 控制和调度Topics (低流量，少量分区)
    topic_list.append(NewTopic(name="ginkgo.live.control.commands", num_partitions=3, replication_factor=1))  # 控制命令
    topic_list.append(NewTopic(name="ginkgo.live.schedule.updates", num_partitions=3, replication_factor=1))  # 调度更新
    topic_list.append(NewTopic(name="ginkgo.live.system.events", num_partitions=3, replication_factor=1))  # 系统事件

    topics = admin_client.list_topics()
    print("Kafka Topics:")
    print(topics)
    # black_topic = ["__consumer_offsets"]
    black_topic = []
    for i in topics:
        name = str(i)
        if name in black_topic:
            continue
        admin_client.delete_topics(topics=[name], timeout_ms=30000)
        print(f"Delet Topic {name}")
        sleep(1)
    topics = admin_client.list_topics()

    # 创建主题
    try:
        print("Try create topics.")
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
    except Exception as e:
        print(e)
    finally:
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
