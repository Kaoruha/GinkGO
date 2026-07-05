import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class _ServiceResult:
    def __init__(self, data=None, success=True, error=""):
        self.data = data
        self.success = success
        self.error = error

    def is_success(self):
        return self.success


def _load_telegram_module():
    sys.modules.pop("ginkgo.notifier.notifier_telegram", None)
    return importlib.import_module("ginkgo.notifier.notifier_telegram")


def _message(text):
    return SimpleNamespace(text=text, chat=SimpleNamespace(id=42))


@pytest.mark.unit
def test_compare_backtest_uses_task_service_compare(monkeypatch):
    telegram = _load_telegram_module()
    service = MagicMock()
    service.compare.return_value = _ServiceResult(
        data={
            "task_ids": ["task-a", "task-b"],
            "metrics": {"total_pnl": {"task-a": "10.5", "task-b": "12.0"}},
        }
    )
    container = MagicMock()
    container.backtest_task_service.return_value = service
    bot = MagicMock()

    monkeypatch.setattr(telegram, "container", container)
    monkeypatch.setattr(telegram, "bot", bot)

    telegram.compare_backtest(_message("/compare task-a task-b"))

    service.compare.assert_called_once_with(["task-a", "task-b"])
    sent = "\n".join(call.args[1] for call in bot.send_message.call_args_list)
    assert "total_pnl" in sent
    assert "task-a" in sent
    assert "10.5" in sent


@pytest.mark.unit
def test_res_backtest_uses_task_service_results(monkeypatch):
    telegram = _load_telegram_module()
    service = MagicMock()
    service.get_results.return_value = _ServiceResult(
        data={
            "task_id": "task-a",
            "portfolio_count": 1,
            "analyzers": ["SharpeRatio"],
            "total_records": 25,
            "time_range": {"start": "2025-01-01", "end": "2025-01-31"},
        }
    )
    container = MagicMock()
    container.backtest_task_service.return_value = service
    bot = MagicMock()

    monkeypatch.setattr(telegram, "container", container)
    monkeypatch.setattr(telegram, "bot", bot)

    telegram.res_backtest(_message("/res task-a"))

    service.get_results.assert_called_once_with("task-a")
    sent = "\n".join(call.args[1] for call in bot.send_message.call_args_list)
    assert "task-a" in sent
    assert "SharpeRatio" in sent
    assert "25" in sent


@pytest.mark.unit
def test_res_backtest_without_id_lists_backtest_tasks(monkeypatch):
    telegram = _load_telegram_module()
    task = SimpleNamespace(
        uuid="task-a",
        name="Demo Backtest",
        status="completed",
        total_pnl="10.5",
        start_at="2025-01-01",
        finish_at="2025-01-31",
    )
    service = MagicMock()
    service.list.return_value = _ServiceResult(data={"data": [task], "total": 1})
    container = MagicMock()
    container.backtest_task_service.return_value = service
    bot = MagicMock()

    monkeypatch.setattr(telegram, "container", container)
    monkeypatch.setattr(telegram, "bot", bot)

    telegram.res_backtest(_message("/res"))

    service.list.assert_called_once()
    sent = "\n".join(call.args[1] for call in bot.send_message.call_args_list)
    assert "Demo Backtest" in sent
    assert "task-a" in sent
