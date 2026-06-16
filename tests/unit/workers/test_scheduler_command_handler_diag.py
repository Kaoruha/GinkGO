# Upstream: SchedulerCommandHandler.handle_schedule_update 的 except 诊断
# Downstream: 排查 schedule 命令消费异常（#6154 str 双重编码 / #6157 NoneType tombstone）
# Role: 守护 catch 块暴露 command_data 类型与值，不被静默吞掉

"""
SchedulerCommandHandler 诊断日志测试（#6154/#6157）。

背景：handle_schedule_update 的 except 只打 {e}（异常消息），丢失了 command_data
的类型与原始值。当 GinkgoConsumer 消费到 str（双重编码，#6154）或 None（tombstone，
#6157）时，报 'str'/'NoneType' object has no attribute 'get'，却无法定位消息来源。
本测试守护 catch 块暴露 type + repr（截断防爆），便于未来定位。

注：Ginkgo logging 经 rich handler 输出到 stdout，不走标准 root 传播，caplog 捕获不到；
故用 patch.object(logger, 'error') 拦截调用参数，测 catch 块构造的诊断消息本身。
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
class TestHandleScheduleUpdateDiagnostics:
    """catch 块诊断日志（#6154/#6157）：暴露被静默吞掉的消息类型与值。"""

    def _capture_error(self, value):
        """喂 msg.value=value，patch logger.error 捕获诊断消息文本。"""
        h = SchedulerCommandHandler(node=MagicMock())
        msg = MagicMock()
        msg.value = value
        with patch.object(_sch_mod.logger, "error") as mock_error:
            h.handle_schedule_update(msg)
        return " ".join(c.args[0] for c in mock_error.call_args_list if c.args)

    def test_str_command_data_logs_type_and_value(self):
        """str（双重编码）消息 → 日志暴露 type=str + 原始值（#6154）。"""
        out = self._capture_error('{"command": "portfolio.migrate"}')
        assert "type=str" in out
        assert "portfolio.migrate" in out  # 原始值片段

    def test_none_command_data_logs_type_none(self):
        """None（tombstone）消息 → 日志暴露 type=NoneType（#6157）。"""
        out = self._capture_error(None)
        assert "type=NoneType" in out

    def test_large_value_truncated(self):
        """超大消息 → repr 截断，防日志爆炸。"""
        out = self._capture_error("x" * 5000)
        assert "type=str" in out
        assert "truncated" in out
