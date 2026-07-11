# Upstream: SchedulerCommandHandler.handle_schedule_update 审计日志
# Downstream: 运维侧按 logger 名采集 schedule 命令审计流
# Role: 守护 #5555 AC3——所有控制命令补结构化审计行 + 执行者身份

"""
SchedulerCommandHandler 审计日志测试（#5555）。

背景：handle_schedule_update 对 schedule.updates Kafka 命令零鉴权（#5555）。
当前项目不做命令签名 / Kafka ACL（自用、功能优先），仅满足 AC 第三条
「Log all control commands with source info」：为所有控制命令补结构化审计日志，
含来源（source_node）与执行者身份（executed_by=本节点 node_id）。

注：审计走独立 logger `ginkgo.audit.schedule_command`，与现有调试 trace 分离，
便于运维侧按 logger 名单独采集审计流。本测试不验证鉴权（明确不存在）。

Ginkgo logging 经 rich handler 输出到 stdout，不走标准 root 传播，caplog 捕获不到；
故沿用 diag 测试套路——patch.object 拦截 audit_logger.info 调用参数。
"""
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest

from ginkgo.workers.execution_node.scheduler_command_handler import SchedulerCommandHandler
import ginkgo.workers.execution_node.scheduler_command_handler as _sch_mod


@pytest.mark.unit
class TestScheduleCommandAuditLog:
    """审计日志（#5555 AC3）：所有 schedule 命令补结构化审计行 + 执行者身份。"""

    def _dispatch(self, command_data, node_id="node-prod-01"):
        """
        喂一条命令，patch 审计 logger 捕获审计行文本。

        Returns:
            审计行文本（info 调用首参拼接）；若 audit_logger.info 未被调用则 None。
        """
        node = MagicMock()
        node.node_id = node_id
        h = SchedulerCommandHandler(node=node)
        msg = MagicMock()
        msg.value = command_data
        with patch.object(_sch_mod, "audit_logger") as mock_audit:
            h.handle_schedule_update(msg)
        if not mock_audit.info.called:
            return None
        return " ".join(str(c.args[0]) for c in mock_audit.info.call_args_list if c.args)

    def test_shutdown_command_emits_audit_line(self):
        """node.shutdown 命令 → 审计 logger emit 一条带 AUDIT 标记的结构化行。"""
        line = self._dispatch({
            "command": "node.shutdown",
            "source_node": "scheduler-01",
            "timestamp": "2026-07-05T10:00:00",
        })
        assert line is not None, "audit_logger.info 未被调用"
        assert "node.shutdown" in line
        assert "AUDIT" in line

    def test_audit_line_includes_executing_node_id(self):
        """审计行含执行者身份 executed_by=本节点 node_id（关键来源信息）。"""
        line = self._dispatch(
            {"command": "node.pause", "source_node": "scheduler-01"},
            node_id="node-exec-42",
        )
        assert line is not None
        assert "executed_by=node-exec-42" in line

    def test_audit_line_covers_unknown_command(self):
        """未知命令（不在路由表）也被审计——「所有控制命令」全覆盖。"""
        line = self._dispatch({
            "command": "evil.die",
            "source_node": "rogue-producer",
            "timestamp": "2026-07-05T10:00:00",
        })
        assert line is not None, "未知命令也必须审计"
        assert "evil.die" in line
        assert "source_node=rogue-producer" in line

    @pytest.mark.parametrize("payload, expected_type", [
        ('{"command": "node.shutdown"}', "str"),   # 双重编码（#6154 生产场景）
        (None, "NoneType"),                         # tombstone（#6157 生产场景）
    ])
    def test_malformed_payload_emits_audit_warning(self, payload, expected_type):
        """
        非-dict payload 不能绕过审计采集（#5555 review 指出的盲点）。

        原实现 audit_logger.info 位于 command_data.get() 之后，非-dict 在 .get()
        立即抛 AttributeError 跳到 except，审计行永不触发——攻击者可发非-dict
        规避采集。畸形 payload 恰是安全审计最该捕获的输入，故走 warning 分支：
        schedule_command_malformed + type/repr 兜底 + executed_by 执行者身份。
        """
        node = MagicMock()
        node.node_id = "node-prod-01"
        h = SchedulerCommandHandler(node=node)
        msg = MagicMock()
        msg.value = payload
        with patch.object(_sch_mod, "audit_logger") as mock_audit:
            h.handle_schedule_update(msg)
        # 非-dict 必须触发 warning（不能因 .get() 抛而绕过审计）
        assert mock_audit.warning.called, (
            f"非-dict payload (type={expected_type}) 必须触发 audit_logger.warning，"
            "审计不能被畸形 payload 绕过"
        )
        line = " ".join(
            str(c.args[0]) for c in mock_audit.warning.call_args_list if c.args
        )
        assert "AUDIT" in line
        assert "schedule_command_malformed" in line
        assert f"type={expected_type}" in line
        # 畸形审计仍含执行者身份（与正常审计对称）
        assert "executed_by=node-prod-01" in line
        # dict 路径的 info 不应触发（非-dict 专属 warning 分支）
        assert not mock_audit.info.called
