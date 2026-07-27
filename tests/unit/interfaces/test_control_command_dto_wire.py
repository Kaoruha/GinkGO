"""
ControlCommandDTO deploy/unload wire 契约回归(ADR-025 ②)。

防御 #4652 类静默失败: 生产侧迁 ControlCommandDTO 后, wire 的 command 字段经
Kafka 序列化(model_dump → serialize_value → json) 往返后必须仍是 "deploy"/"unload"
字面值 —— paper_trading_worker._handle_command 按字面 == "deploy"/== "unload" 分发,
command 漂移即命令被静默吞(deploy/unload 失效, 无报错)。

另验向后兼容: 旧 dataclass ControlCommand.to_dict() 发的 {command,params,timestamp}
仍能被 MessageMapper.decode(ControlCommandDTO) 解析(余 Optional 字段缺失走默认) ——
保证渐进部署(旧 producer / 新 consumer 不同步)不断消息。

纯内存, 无 Kafka/DB IO。
"""
import sys
import json
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.interfaces.dtos import ControlCommandDTO  # noqa: E402
from ginkgo.interfaces.mappers.message_mapper import MessageMapper  # noqa: E402
from ginkgo.data.drivers.ginkgo_kafka import serialize_value  # noqa: E402


def _round_trip(dto: ControlCommandDTO) -> ControlCommandDTO:
    """模拟真实 Kafka 往返: model_dump → value_serializer → consumer json.loads → decode。"""
    wire_bytes = serialize_value(dto.model_dump())  # 生产侧序列化(datetime→iso)
    raw = json.loads(wire_bytes.decode("utf-8"))  # 消费侧 value_deserializer
    return MessageMapper.decode(raw, ControlCommandDTO)


class TestDeployUnloadWireFidelity:
    """command 字面值 + params 经完整 wire 往返忠实保持(防 #4652)。"""

    @pytest.mark.unit
    @pytest.mark.parametrize("const,expected", [
        (ControlCommandDTO.Commands.DEPLOY, "deploy"),
        (ControlCommandDTO.Commands.UNLOAD, "unload"),
    ])
    def test_command_string_survives_wire_round_trip(self, const, expected):
        """DTO(DEPLOY/UNLOAD) 全链路往返后 command 仍是字面 deploy/unload。

        若 model_dump/serialize_value 损坏 command(如 timestamp 序列化炸 / 字段名漂移),
        decode 重建的 command != expected —— deploy/unload 会静默 miss(_handle_command
        无匹配分支即静默跳过)。本断言是迁移后 deploy 不失效的铁证。
        """
        dto = ControlCommandDTO(
            command=const,
            params={"portfolio_id": "p-abcdef-1234"},
            source="portfolio_cli",
        )
        decoded = _round_trip(dto)
        assert decoded.command == expected
        assert decoded.get_param("portfolio_id") == "p-abcdef-1234"

    @pytest.mark.unit
    def test_timestamp_serializes_without_error(self):
        """DTO.timestamp 是 datetime, 经 serialize_value(datetime→iso) 不得抛。

        serialize_value 的 _json_default 兜底(#6161) 是迁移可用的前提; 若失配,
        producer.send 会炸, deploy 链路断在生产侧。
        """
        dto = ControlCommandDTO(command=ControlCommandDTO.Commands.DEPLOY, params={})
        wire = serialize_value(dto.model_dump())  # 不抛即通过
        assert isinstance(wire, (bytes, bytearray))
        raw = json.loads(wire.decode("utf-8"))
        assert "timestamp" in raw  # datetime 已 iso 化落 wire


class TestLegacyWireBackwardCompat:
    """旧 producer(dataclass to_dict) → 新 consumer(decode DTO) 渐进部署不断消息。"""

    @pytest.mark.unit
    def test_legacy_minimal_wire_decodes_into_dto(self):
        """旧 wire {command, params, timestamp} 缺 source/trace_id 等, decode 走默认。

        场景: producer 尚未升级(仍发 3 字段) / consumer 已迁 decode —— 消息必须仍可解析,
        command/params 忠实。source 缺失 → Optional 默认 None(不报错)。
        """
        legacy_wire = {
            "command": "deploy",
            "params": {"portfolio_id": "legacy-pid"},
            "timestamp": "2026-07-28T10:00:00",
        }
        decoded = MessageMapper.decode(legacy_wire, ControlCommandDTO)
        assert decoded.command == "deploy"
        assert decoded.get_param("portfolio_id") == "legacy-pid"
        # 旧 wire 无 source, DTO 字段 default="task_timer" 兜底(语义不准但无功能影响:
        # 消费端不按 source 分发, 仅作 correlation 记录)。记录此回填行为防误判为 bug。
        assert decoded.source == "task_timer"

    @pytest.mark.unit
    def test_new_full_wire_decodes_cleanly(self):
        """新 producer 全字段 wire → decode 完整还原(含 trace_id 追踪字段)。"""
        dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.UNLOAD,
            params={"portfolio_id": "p1"},
            source="deployment_service",
            trace_id="trace-xyz",
        )
        decoded = _round_trip(dto)
        assert decoded.command == "unload"
        assert decoded.source == "deployment_service"
        assert decoded.trace_id == "trace-xyz"
