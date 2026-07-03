"""#4960: data sync --daemon 分支被 quiet_function_timing 包裹的接线验证。

机制层（quiet_function_timing 静默逐调用 timing + 汇总）的契约由
tests/unit/libs/test_time_logger_quiet_mode_4960.py 覆盖。本文件只验证 CLI 接线：
- daemon 成功 → exit 0 + 业务消息走 stdout + kafka 信号已发
- daemon 失败 → 非 force 时 typer.Exit(1)（quiet 上下文不得吞异常）

不连真 Kafka；不在此重复验证 stderr 汇总（CliRunner 与 capfd 对 Rich Console
的 fd 捕获不兼容，机制层已覆盖）。
"""
import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client.data_cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    from ginkgo.libs.core.config import GinkgoConfig

    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance
    yield
    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance


class TestSyncDaemonQuietWiring:
    """#4960: daemon 分支 quiet_function_timing 接线不破坏既有契约。"""

    @pytest.mark.unit
    def test_daemon_day_all_success_routes_to_kafka_and_exits_zero(self):
        """sync day --daemon（全代码）→ send_bar_all_signal() + exit 0 + 业务消息。"""
        mock_kafka = MagicMock()
        mock_kafka.send_bar_all_signal.return_value = True

        with patch(
            "ginkgo.data.containers.container.kafka_service",
            return_value=mock_kafka,
        ):
            result = runner.invoke(app, ["sync", "day", "--daemon"])

        assert result.exit_code == 0, f"stdout: {result.stdout}"
        mock_kafka.send_bar_all_signal.assert_called_once_with(full=False, force=False)
        # 业务消息走 stdout（quiet_function_timing 不污染 stdout，#6465 契约）
        assert "successfully queued" in result.stdout

    @pytest.mark.unit
    def test_daemon_day_all_failure_exits_nonzero(self):
        """daemon 入队失败 + 非 force → typer.Exit(1)；quiet 上下文不得吞掉。"""
        mock_kafka = MagicMock()
        mock_kafka.send_bar_all_signal.return_value = False

        with patch(
            "ginkgo.data.containers.container.kafka_service",
            return_value=mock_kafka,
        ):
            result = runner.invoke(app, ["sync", "day", "--daemon"])

        assert result.exit_code == 1, f"expected exit 1, got {result.exit_code}; stdout: {result.stdout}"
