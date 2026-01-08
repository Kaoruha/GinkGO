# Upstream: API Gateway, CLI, Data模块 (发布消息)
# Downstream: ExecutionNode, LiveEngine (订阅并处理消息)
# Role: Ginkgo消息模块，定义用于Kafka/消息传输的数据结构


"""
Ginkgo消息模块

定义用于Kafka消息传输的数据结构，与事件驱动引擎的Event分离：
- ControlCommand: 控制命令消息
- 未来可扩展：MarketDataMessage, OrderMessage等

与events/的区别：
- events/: 用于事件驱动引擎的事件（继承EventBase）
- messages/: 用于Kafka/消息传输的数据结构（轻量级DTO）
"""

from ginkgo.messages.control_command import ControlCommand

__all__ = ["ControlCommand"]
