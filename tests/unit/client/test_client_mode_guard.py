"""client 模式危险操作拦截单测 (ADR-024 §6)。

验证 ``assert_command_allowed_in_client``：
- local 模式放行一切；
- client 模式对 DDL / schema 类（``init``）抛 ``SystemExit(1)`` 并提示去 server 执行；
- client 模式对非危险命令（``status`` / ``backtest``）放行。

GCONF.MODE 经 ``GINKGO_MODE`` env 控制（config.py ``_get_config`` env 优先于文件），
``monkeypatch.setenv`` 即可切模式，env 每次 ``os.environ.get`` 现读无缓存。
"""
import pytest


def _guard():
    from ginkgo.client.client_mode import assert_command_allowed_in_client
    return assert_command_allowed_in_client


def test_local_mode_allows_init(monkeypatch):
    """local 模式：建表命令（init）放行，不抛。"""
    monkeypatch.setenv("GINKGO_MODE", "local")
    _guard()("init")  # 不抛即通过


def test_client_mode_blocks_init(monkeypatch):
    """client 模式：init（DDL）被拒，SystemExit(1) + 提示去 server。"""
    monkeypatch.setenv("GINKGO_MODE", "client")
    with pytest.raises(SystemExit) as ei:
        _guard()("init")
    assert ei.value.code == 1


def test_client_mode_allows_non_forbidden(monkeypatch):
    """client 模式：非危险命令（status / backtest）放行。"""
    monkeypatch.setenv("GINKGO_MODE", "client")
    g = _guard()
    g("status")
    g("backtest")
    g("portfolio")


def test_guard_idempotent_outside_client(monkeypatch):
    """未设 GINKGO_MODE（默认 local）：即便命令在 forbidden 集，也放行（门只对 client 生效）。"""
    monkeypatch.delenv("GINKGO_MODE", raising=False)
    _guard()("init")  # 默认 local，放行
