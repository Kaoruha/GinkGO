import json
from kafka import KafkaProducer
from kafka import KafkaConsumer

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
        self.producer.send(topic, msg)
        self.producer.flush()


class GinkgoConsumer(object):
    def __init__(self, topic):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],  # Kafka集群地址
            auto_offset_reset="earliest",  # 从最早的消息开始消费
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),  # 消息反序列化
        )
