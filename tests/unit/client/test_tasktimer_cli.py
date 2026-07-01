# Upstream: tasktimer_cli(ginkgo tasktimer 命令)
# Downstream: 无
# Role: TaskTimer CLI 单元测试，聚焦心跳值解析稳健性（#4627）

"""
TaskTimer CLI 单元测试

覆盖心跳值解析稳健性（#4627）：
- parse_heartbeat_value: ISO 时间戳 / JSON dict / 无效值 三路降级
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from ginkgo.client import tasktimer_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


# ============================================================================
# parse_heartbeat_value — 心跳值稳健解析
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestParseHeartbeatValue:
    """parse_heartbeat_value 对各类心跳值优雅降级（#4627）"""

    def test_iso_timestamp_string(self):
        """ISO 时间戳字符串（写入端实际格式）→ 不崩，timestamp=原值，其余 N/A"""
        # 写入端 heartbeat_manager.py:194 / utils/heartbeat.py:125 写的就是这种值
        value = "2026-06-30T16:53:33.123456+00:00"
        result = tasktimer_cli.parse_heartbeat_value(value)
        assert result["timestamp"] == value
        assert result["host"] == "N/A"
        assert result["pid"] == "N/A"
        assert result["jobs_count"] == "N/A"

    def test_json_dict(self):
        """合法 JSON dict（兼容未来/老格式）→ 提取 timestamp/host/pid/jobs_count"""
        value = '{"timestamp": "2026-06-30T10:00:00Z", "host": "node-1", "pid": 12345, "jobs_count": 7}'
        result = tasktimer_cli.parse_heartbeat_value(value)
        assert result["timestamp"] == "2026-06-30T10:00:00Z"
        assert result["host"] == "node-1"
        assert result["pid"] == 12345
        assert result["jobs_count"] == 7

    def test_garbage_value(self):
        """完全无效的垃圾值 → 不崩，降级 timestamp=原值"""
        value = "not-a-json-at-all"
        result = tasktimer_cli.parse_heartbeat_value(value)
        assert result["timestamp"] == value
        assert result["host"] == "N/A"
        assert result["pid"] == "N/A"
        assert result["jobs_count"] == "N/A"

    def test_json_with_missing_fields(self):
        """JSON dict 缺字段 → 缺失字段降级为 N/A"""
        value = '{"timestamp": "2026-06-30T10:00:00Z"}'
        result = tasktimer_cli.parse_heartbeat_value(value)
        assert result["timestamp"] == "2026-06-30T10:00:00Z"
        assert result["host"] == "N/A"
        assert result["pid"] == "N/A"
        assert result["jobs_count"] == "N/A"

    def test_none_value(self):
        """None 值（Redis key 存在但值为空）→ 不崩"""
        result = tasktimer_cli.parse_heartbeat_value(None)
        assert result["timestamp"] is None
        assert result["host"] == "N/A"


# ============================================================================
# heartbeat 命令 — 端到端不崩（#4627 验收）
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestHeartbeatCommand:
    """heartbeat 命令对非 JSON 心跳值不崩、可读展示（#4627 端到端）"""

    def test_iso_timestamp_value_no_crash(self, cli_runner):
        """ISO 时间戳心跳值（写入端实际格式）：命令正常退出，展示 ALIVE，无 ERROR 噪声"""
        fake_redis = MagicMock()
        fake_redis.keys.return_value = ["heartbeat:node:abc123"]
        fake_redis.ttl.return_value = 30
        fake_redis.get.return_value = "2026-06-30T16:53:33.123456+00:00"

        with patch("redis.Redis", return_value=fake_redis):
            result = cli_runner.invoke(tasktimer_cli.app, ["heartbeat"])

        assert result.exit_code == 0
        # 节点 id 进入输出（key 解析正常）
        assert "abc123" in result.output
        # ALIVE 基于 TTL（30s 存活），不被解析失败污染
        assert "ALIVE" in result.output
        # 不再有解析错误噪声
        assert "Failed to parse" not in result.output

    def test_mixed_json_and_iso_values(self, cli_runner):
        """混合心跳值（一个 JSON 一个 ISO）：都不崩，各自正确展示"""
        fake_redis = MagicMock()
        fake_redis.keys.return_value = ["heartbeat:node:json-node", "heartbeat:node:iso-node"]
        # ttl/get 按 key 调用顺序返回：第一个 json-node 存活，第二个 iso-node 存活
        fake_redis.ttl.side_effect = [25, 25]
        fake_redis.get.side_effect = [
            '{"timestamp": "2026-06-30T10:00:00Z", "host": "h1", "pid": 111}',
            "2026-06-30T11:00:00+00:00",  # ISO 时间戳，非 JSON
        ]

        with patch("redis.Redis", return_value=fake_redis):
            result = cli_runner.invoke(tasktimer_cli.app, ["heartbeat"])

        assert result.exit_code == 0
        assert "json-node" in result.output
        assert "iso-node" in result.output
        assert "Failed to parse" not in result.output
