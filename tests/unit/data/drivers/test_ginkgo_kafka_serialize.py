# Upstream: GinkgoProducer.value_serializer 序列化行为
# Downstream: GinkgoProducer.send (生产 Kafka 消息)
# Role: 守护序列化层对 datetime/Decimal 等非 JSON 原生类型兜底，防 TypeError 被静默吞掉

"""
GinkgoProducer 序列化单元测试（#6161）。

背景：ScheduleUpdateDTO 等含 datetime 字段，model_dump() 保留原生 datetime，
GinkgoProducer.value_serializer 的 json.dumps 抛 TypeError 被 send 的 except
静默吞掉（ginkgo_kafka.py:94）→ 消息从不写入 topic，schedule 命令链路断裂。
本测试守护序列化层对非 JSON 原生类型兜底，保证往返恢复 dict。
"""
import json
from datetime import datetime
from decimal import Decimal


class TestSerializeValueJsonSafe:
    """serialize_value 必须把含非 JSON 原生类型（datetime/Decimal）的 dict
    序列化为 JSON-safe bytes，json.loads 往返恢复为 dict（#6161）。"""

    def test_datetime_serialized_to_iso_str(self):
        from ginkgo.data.drivers.ginkgo_kafka import serialize_value
        ts = datetime(2026, 6, 15, 10, 0, 0)
        out = serialize_value({"command": "portfolio.migrate", "timestamp": ts})
        back = json.loads(out.decode("utf-8"))
        assert back["command"] == "portfolio.migrate"
        assert back["timestamp"] == "2026-06-15T10:00:00"  # ISO 字符串
        assert isinstance(back["timestamp"], str)

    def test_decimal_serialized_to_str(self):
        from ginkgo.data.drivers.ginkgo_kafka import serialize_value
        out = serialize_value({"price": Decimal("10.5")})
        back = json.loads(out.decode("utf-8"))
        assert back["price"] == "10.5"

    def test_plain_dict_roundtrip(self):
        from ginkgo.data.drivers.ginkgo_kafka import serialize_value
        out = serialize_value({"a": 1, "b": "x"})
        assert json.loads(out) == {"a": 1, "b": "x"}

    def test_schedule_update_dto_payload_serializes(self):
        """端到端复现 bug：ScheduleUpdateDTO.model_dump()（含 datetime）经
        serialize_value 不再抛 TypeError，往返 dict，command 可 .get（#6161）。"""
        from ginkgo.data.drivers.ginkgo_kafka import serialize_value
        from ginkgo.interfaces.dtos.schedule_update_dto import ScheduleUpdateDTO
        dto = ScheduleUpdateDTO(command="node.pause", node_id="n1")
        out = serialize_value(dto.model_dump())  # 修复前抛 TypeError
        back = json.loads(out.decode("utf-8"))
        assert back["command"] == "node.pause"
        assert isinstance(back["timestamp"], str)


class TestValueSerializerNotBareLambda:
    """守护：GinkgoProducer.value_serializer 不应是抛 TypeError 的裸 json.dumps（防回归 #6161）。"""

    def test_serialize_value_with_default_used(self):
        import inspect
        from ginkgo.data.drivers import ginkgo_kafka
        src = inspect.getsource(ginkgo_kafka)
        assert "serialize_value" in src, "value_serializer 应引用 serialize_value 模块函数"
        assert "default=" in src, "序列化必须带 default 兜底处理非 JSON 原生类型"
