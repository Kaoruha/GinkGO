import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.structs import TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic

from ginkgo.libs.ginkgo_conf import GCONF


class GinkgoProducer(object):
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),  # 消息序列化
        )
        self._max_try = 5

    @property
    def max_try(self) -> int:
        return self._max_try

    def send(self, topic, msg):
        try:
            future = self.producer.send(topic, msg)
            future.get(timeout=10)
        except Exception as e:
            print(e)
        finally:
            self.producer.flush()


class GinkgoConsumer(object):
    def __init__(self, topic: str, group_id: str = ""):
        self.consumer = None
        if group_id == "":
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
                auto_offset_reset="earliest",  # 从最早的消息开始消费
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),  # 消息反序列化
                max_poll_interval_ms=1800000,
                max_poll_records=1,
            )
        else:
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
                group_id=group_id,
                auto_offset_reset="earliest",  # 从最早的消息开始消费
                # auto_offset_reset="latest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),  # 消息反序列化
                max_poll_interval_ms=1800000,
                max_poll_records=1,
            )

    def commit(self):
        self.consumer.commit()


def kafka_topic_set():
    # 创建 KafkaAdminClient 实例
    admin_client = KafkaAdminClient(
        bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
        client_id="admin",
    )

    # 创建一个新主题的配置
    topic_list = []
    topic_list.append(
        NewTopic(name="ginkgo_data_update", num_partitions=32, replication_factor=1)
    )
    topic_list.append(
        NewTopic(name="live_control", num_partitions=1, replication_factor=1)
    )
    topics = admin_client.list_topics()
    print("Kafka Topics:")
    print(topics)
    black_topic = ["__consumer_offsets"]
    for i in topics:
        name = str(i)
        admin_client.delete_topics(topics=[name], timeout_ms=30000)
        print(f"Delet Topic {name}")

    # 创建主题
    admin_client.create_topics(new_topics=topic_list, validate_only=False)
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
