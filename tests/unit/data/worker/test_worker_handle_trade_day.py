"""
DataWorker _handle_trade_day wiring 测试（#6488）

验证 worker 消费 trade_day 命令 → 调 container.trade_day_service().sync()。
这是 #6488 的"信号有消费者"闭环——发出去的 kafka 信号必须有 worker handler 消费，
否则是死信号（arch_paper_trading_control_commands_no_consumer 教训）。
镜像 _handle_stockinfo 测试结构。__new__ 跳过 DataWorker.__init__（避免连 kafka/mysql）。
"""

import sys
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.worker.worker import DataWorker


class TestHandleTradeDay:
    """_handle_trade_day wiring 测试"""

    @pytest.mark.unit
    def test_handle_trade_day_invokes_service_sync(self):
        """_handle_trade_day 调 trade_day_service().sync() 并返回 success（tracer bullet）"""
        worker = DataWorker.__new__(DataWorker)
        worker._node_id = "test-node"
        worker._lock = threading.Lock()
        worker._stats = {"errors": 0}

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error = None
        mock_service = MagicMock()
        mock_service.sync.return_value = mock_result

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.trade_day_service.return_value = mock_service
            ok = worker._handle_trade_day({"code": ""})

        assert ok is True
        mock_service.sync.assert_called_once()

    @pytest.mark.unit
    def test_dispatch_routes_trade_day_to_handler(self):
        """_process_command 路由 trade_day 命令到 _handle_trade_day"""
        worker = DataWorker.__new__(DataWorker)
        worker._node_id = "test-node"
        worker._lock = threading.Lock()
        worker._stats = {"errors": 0}

        with patch.object(worker, "_notify_task_start"), \
             patch.object(worker, "_handle_trade_day", return_value=True) as mock_h, \
             patch("ginkgo.data.containers.container"):
            ok = worker._process_command("trade_day", {"code": ""})

        assert ok is True
        mock_h.assert_called_once_with({"code": ""})
