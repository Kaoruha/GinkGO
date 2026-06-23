# Upstream: Scheduler（持有 CommandHandler 实例，每 ~5s 调 check_commands）
# Downstream: Kafka 断连时 command_consumer.consumer 为 None，poll 抛 AttributeError
# Role: #5316 守护 check_commands 的连接守卫，断连不刷 error log、不碰 poll

"""
CommandHandler.check_commands 连接守卫测试（#5316）。

背景：GinkgoConsumer 在 Kafka 连接失败时把内部 self.consumer 置 None
（ginkgo_kafka.py:202/237/242），但包装对象本身仍存在。check_commands 原守卫
`if not command_consumer` 只查包装非 None，放行后 `consumer.poll()` 抛
AttributeError，被 except 吞成每 ~5s 一条 error log，命令永不消费。

修复：守卫补 `is_connected` 检查（对齐 notification_worker:155 /
backtest_worker/node.py:385 / data/worker/worker.py:349 既有模式），
用 getattr 防属性缺失。
"""
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest

from ginkgo.livecore.scheduler.command_handler import CommandHandler
import ginkgo.livecore.scheduler.command_handler as _cmd_mod


def _make_handler() -> CommandHandler:
    """构造 CommandHandler，8 个依赖全 MagicMock（check_commands 不触达它们）。"""
    return CommandHandler(*[MagicMock() for _ in range(8)])


@pytest.mark.unit
class TestCheckCommandsConsumerGuard:
    """#5316：Kafka 断连（内部 consumer=None）时不刷 error log、不碰 poll。"""

    def test_disconnected_consumer_no_error_log(self):
        """内部 consumer=None + is_connected=False → 守卫拦住，无 error log（#5316 核心）。"""
        handler = _make_handler()
        cmd_consumer = MagicMock()
        cmd_consumer.consumer = None  # Kafka 断连：GinkgoConsumer 置内部 consumer=None
        cmd_consumer.is_connected = False
        with patch.object(_cmd_mod.logger, "error") as mock_error:
            handler.check_commands(cmd_consumer)
        mock_error.assert_not_called()

    def test_disconnected_consumer_does_not_poll(self):
        """is_connected=False → 守卫拦住，不调 poll（断连信号而非 consumer=None）。"""
        handler = _make_handler()
        cmd_consumer = MagicMock()
        cmd_consumer.is_connected = False  # 断连信号：consumer 可访问但不该被碰
        handler.check_commands(cmd_consumer)
        cmd_consumer.consumer.poll.assert_not_called()

    def test_healthy_consumer_still_polls(self):
        """正常连接（is_connected=True, consumer 非空）仍 poll（回归，防守卫过严）。"""
        handler = _make_handler()
        cmd_consumer = MagicMock()
        cmd_consumer.is_connected = True
        cmd_consumer.consumer.poll.return_value = {}  # 无消息
        handler.check_commands(cmd_consumer)
        cmd_consumer.consumer.poll.assert_called_once_with(timeout_ms=1000)

    def test_none_wrapper_returns_early(self):
        """command_consumer 为 None（未初始化）直接返回，不抛（既有守卫回归）。"""
        handler = _make_handler()
        handler.check_commands(None)  # 不应抛 AttributeError

    def test_missing_is_connected_attr_falls_back_to_skip(self):
        """消费者对象无 is_connected 属性 → getattr 默认 False，安全跳过（防御性）。"""
        handler = _make_handler()
        cmd_consumer = MagicMock()
        del cmd_consumer.is_connected  # 模拟属性不存在
        cmd_consumer.consumer = MagicMock()
        with patch.object(_cmd_mod.logger, "error") as mock_error:
            handler.check_commands(cmd_consumer)
        mock_error.assert_not_called()
