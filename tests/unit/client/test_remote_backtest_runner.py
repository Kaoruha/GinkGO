"""RemoteBacktestRunner 单测 (ADR-024)。

纯单测：注入按调用序列返回伪造响应的 fake client，验证提交+轮询的状态机
（pending→running→completed），以及 failed/stopped/timeout 各分支，不触 HTTP/DB。
"""
import pytest

from ginkgo.client.remote.services import RemoteBacktestRunner


class _ScriptedClient:
    """按调用顺序消费伪造响应的 client，**强制 method 与脚本 kind 匹配**。

    record 形如 ``("POST", <data>)`` / ``("GET", <data>)`` / ``("raise", <Exc>)``。
    位置严格按 run() 的真实调用顺序：先 POST submit，后若干 GET 轮询（completed 尾部
    再一个 GET results）。
    """

    def __init__(self, script):
        self._script = list(script)
        self.calls = []  # (method, path)

    def _next(self, method, path):
        self.calls.append((method, path))
        if not self._script:
            raise AssertionError(f"脚本耗尽：{method} {path}（已调用 {self.calls}）")
        kind, payload = self._script.pop(0)
        if kind == "raise":
            raise payload
        if kind != method:
            raise AssertionError(
                f"调用顺序错配：期望 {kind}，实际 {method} {path}（剩余 {self._script}）"
            )
        return payload

    def post(self, path, **kw):
        return self._next("POST", path)

    def get(self, path, **kw):
        return self._next("GET", path)


def _detail(status, **extra):
    d = {"name": "t1", "status": status}
    d.update(extra)
    return d


def test_run_polls_to_completed_and_pulls_results():
    fc = _ScriptedClient([
        ("POST", {"uuid": "u1", "state": "PENDING"}),
        ("GET", _detail("pending")),
        ("GET", _detail("running", progress=40)),
        ("GET", _detail("running", progress=80)),
        ("GET", _detail("completed", annual_return=0.12, sharpe_ratio=1.5, total_orders=7)),
        ("GET", {"summary": "ok"}),
    ])
    runner = RemoteBacktestRunner(client=fc, poll_interval=0)
    seen = []
    state, detail, results = runner.run("u1", on_progress=lambda s, d: seen.append(s))
    assert state == "completed"
    assert detail["status"] == "completed"
    assert results == {"summary": "ok"}
    # 进度回调在每个状态变化时触发（running 仅在首次出现时记一次，80% 不重复）
    assert seen == ["pending", "running", "completed"]
    assert ("POST", "/backtest/u1/start") in fc.calls


def test_run_failed_does_not_pull_results():
    fc = _ScriptedClient([
        ("POST", {"state": "PENDING"}),
        ("GET", _detail("running")),
        ("GET", _detail("failed", error_message="boom")),
    ])
    runner = RemoteBacktestRunner(client=fc, poll_interval=0)
    state, detail, results = runner.run("u1")
    assert state == "failed"
    assert detail["error_message"] == "boom"
    # failed 终态不拉 results
    assert results is None
    assert all("results" not in c[1] for c in fc.calls)


def test_run_stopped_is_terminal():
    fc = _ScriptedClient([
        ("POST", {"state": "PENDING"}),
        ("GET", _detail("running")),
        ("GET", _detail("stopped")),
    ])
    runner = RemoteBacktestRunner(client=fc, poll_interval=0)
    state, _d, _r = runner.run("u1")
    assert state == "stopped"


def test_timeout_returns_current_non_terminal_state():
    # poll_interval=0 + timeout=0：首轮 get_status 返 running（非终态），sleep 后即超时返回
    # 额外留一条 GET 兜底：若首轮 monotonic 恰为 0 未触发，次轮同样返 running，不耗尽脚本
    fc = _ScriptedClient([
        ("POST", {"state": "PENDING"}),
        ("GET", _detail("running")),
        ("GET", _detail("running")),
    ])
    runner = RemoteBacktestRunner(client=fc, poll_interval=0)
    state, detail, _r = runner.run("u1", timeout=0)
    assert state == "running"
    assert detail["status"] == "running"


def test_submit_error_propagates():
    fc = _ScriptedClient([("raise", RuntimeError("server 500"))])
    runner = RemoteBacktestRunner(client=fc, poll_interval=0)
    with pytest.raises(RuntimeError):
        runner.run("u1")


def test_status_of_normalizes_state_alias_and_case():
    assert RemoteBacktestRunner._status_of({"status": "RUNNING"}) == "running"
    # 兼容 start ack 的 state 字段
    assert RemoteBacktestRunner._status_of({"state": "PENDING"}) == "pending"
    assert RemoteBacktestRunner._status_of(None) is None
    assert RemoteBacktestRunner._status_of({}) == ""
