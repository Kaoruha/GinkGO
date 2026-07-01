"""#6488: data sync trade_day CLI 路由测试。

验证 CLI 入口正确路由 trade_day：daemon 模式发 kafka 信号，同步模式调
trade_day_service.sync()。镜像 stockinfo 分支（全量同步，无 code 参数）。
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


def _ok_result():
    r = MagicMock()
    r.is_success.return_value = True
    r.message = "Trade calendar sync completed"
    return r


class TestSyncTradeDay:
    """#6488: data sync trade_day 双模式路由"""

    @pytest.mark.unit
    def test_daemon_mode_sends_kafka_signal(self):
        """sync trade_day --daemon → kafka_service.send_trade_day_signal()"""
        mock_kafka = MagicMock()
        mock_kafka.send_trade_day_signal.return_value = True

        with patch("ginkgo.data.containers.container.kafka_service", return_value=mock_kafka):
            result = runner.invoke(app, ["sync", "trade_day", "--daemon"])

        assert result.exit_code == 0, f"stdout: {result.stdout}"
        mock_kafka.send_trade_day_signal.assert_called_once()

    @pytest.mark.unit
    def test_sync_mode_calls_service_sync(self):
        """sync trade_day（同步模式）→ trade_day_service.sync()"""
        mock_svc = MagicMock()
        mock_svc.sync.return_value = _ok_result()

        with patch("ginkgo.data.containers.container.trade_day_service", return_value=mock_svc):
            result = runner.invoke(app, ["sync", "trade_day"])

        assert result.exit_code == 0, f"stdout: {result.stdout}"
        mock_svc.sync.assert_called_once()
