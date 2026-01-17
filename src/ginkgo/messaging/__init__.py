# Upstream: Kafka驱动层
# Downstream: LiveCore (DataManager, TaskTimer)
# Role: 消息中间件统一接口 - 封装Kafka Producer和Consumer

from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer, GinkgoConsumer

__all__ = ["GinkgoProducer", "GinkgoConsumer"]
