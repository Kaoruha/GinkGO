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


# ============================================================================
# status 命令 — 默认 node_id 错配时发现实际 TaskTimer heartbeat（#4890）
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestTaskTimerStatusCommand:
    """status 不应因默认 node_id 与容器实际 node_id 不同而直接误报 DEAD。"""

    def test_status_discovers_single_alive_tasktimer_when_default_key_missing(self, cli_runner):
        fake_redis = MagicMock()
        fake_redis.exists.return_value = 0
        fake_redis.ttl.side_effect = [-2, 30]
        fake_redis.keys.return_value = ["heartbeat:task_timer:tasktimer_host123"]
        fake_redis.get.return_value = (
            '{"timestamp": "2026-07-06T10:00:00Z", "host": "host123", "pid": 123, "jobs_count": 4}'
        )

        with patch("redis.Redis", return_value=fake_redis):
            result = cli_runner.invoke(tasktimer_cli.app, ["status"])

        assert result.exit_code == 0
        assert "tasktimer_host123" in result.output
        assert "ALIVE" in result.output
        assert "DEAD" not in result.output

    def test_status_lists_candidates_when_multiple_tasktimers_exist(self, cli_runner):
        fake_redis = MagicMock()
        fake_redis.exists.return_value = 0
        fake_redis.ttl.side_effect = [-2, 30, 28]
        fake_redis.keys.return_value = [
            "heartbeat:task_timer:tasktimer_a",
            "heartbeat:task_timer:tasktimer_b",
        ]

        with patch("redis.Redis", return_value=fake_redis):
            result = cli_runner.invoke(tasktimer_cli.app, ["status"])

        assert result.exit_code == 0
        assert "Multiple TaskTimer heartbeats found" in result.output
        assert "tasktimer_a" in result.output
        assert "tasktimer_b" in result.output
        assert "--node-id" in result.output
        assert "DEAD" not in result.output


# ============================================================================
# init 链路拷贝 task_timer.yml — #4723
#   ginkgo init → GCONF.generate_config_file 未安装 task_timer.yml，
#   用户首次 tasktimer validate 即报 INVALID。修复：与 config.yml/secure.yml
#   对称，幂等拷贝 src/ginkgo/config/task_timer.yml → 目标目录。
# ============================================================================


@pytest.fixture
def isolated_gconf(monkeypatch):
    """隔离 GCONF 单例状态 + 重定向 GINKGO_DIR 到临时目录，避免污染其他测试"""
    from ginkgo.libs.core.config import GCONF

    saved = {
        "_has_local_config": GCONF._has_local_config,
        "_has_local_secure": GCONF._has_local_secure,
    }
    yield GCONF
    # 恢复单例状态，防 _has_local_* 残留污染后续测试
    GCONF._has_local_config = saved["_has_local_config"]
    GCONF._has_local_secure = saved["_has_local_secure"]


@pytest.mark.unit
@pytest.mark.cli
class TestTaskTimerInitConfig:
    """ginkgo init 链路（GCONF.generate_config_file）拷贝 task_timer.yml 模板 (#4723)"""

    def test_init_installs_task_timer_template(self, tmp_path, isolated_gconf):
        """generate_config_file 后目标目录存在 task_timer.yml（从 src 模板拷贝）"""
        isolated_gconf.generate_config_file(str(tmp_path))
        installed = tmp_path / "task_timer.yml"
        assert installed.exists(), "task_timer.yml 未被 init 链路拷贝"
        assert installed.is_file()

    def test_init_does_not_overwrite_existing_task_timer(self, tmp_path, isolated_gconf):
        """已存在 task_timer.yml（用户自定义）→ init 链路不覆盖，保留用户配置"""
        custom = tmp_path / "task_timer.yml"
        custom.write_text("user-customized: true\n")
        isolated_gconf.generate_config_file(str(tmp_path))
        assert custom.read_text() == "user-customized: true\n", "init 覆盖了用户自定义 task_timer.yml"

    def test_installed_task_timer_passes_validate(self, tmp_path, isolated_gconf):
        """init 拷贝的 task_timer.yml 能通过 TaskTimer.validate_config (#4723 验收2)"""
        from ginkgo.livecore.task_timer import TaskTimer
        isolated_gconf.generate_config_file(str(tmp_path))
        installed = str(tmp_path / "task_timer.yml")
        timer = TaskTimer(config_path=installed)
        assert timer.validate_config() is True, "拷贝的模板未通过 validate_config"


@pytest.mark.unit
@pytest.mark.cli
class TestTaskTimerValidateCommand:
    """tasktimer validate 友好处理缺失配置文件 (#5185)"""

    def test_missing_config_prints_creation_hint_not_raw_exit_code(self, tmp_path, cli_runner):
        missing = tmp_path / "missing-task_timer.yml"

        result = cli_runner.invoke(tasktimer_cli.app, ["validate", "--config", str(missing)])

        assert result.exit_code != 0
        assert "Configuration file not found" in result.output
        assert "ginkgo init" in result.output
        assert "task_timer.yml" in result.output
        assert "Error validating config: 1" not in result.output
