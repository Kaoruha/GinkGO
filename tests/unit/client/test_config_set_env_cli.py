# Upstream: client/config_cli.py, client/engine_cli.py, client/core_cli.py
# Downstream: -
# Role: ADR-026 CLI 闸门回归：set env 写 .env+触发 compose；set debug 不再触发；回测拒跑生产

"""ADR-026 CLI 闸门回归测试。

覆盖：
- `config set env DEVELOPMENT`：写 .env（GINKGO_ENV + host）+ 触发 docker compose 重启
- `config set debug on`：不再写 .env / 不再触发 compose（解耦 regression）
- `engine run` / `backtest run` / `core test`：PRODUCTION env 下拒跑（防误连生产写数据）
"""

import os
import pytest
import typer
from ginkgo.libs.core.config import GCONF, GinkgoConfig


@pytest.fixture
def compose_dir(tmp_path):
    """临时 compose 目录：含 docker-compose.yml 占位 + 不存在的 .env。"""
    (tmp_path / "docker-compose.yml").write_text("services:\n  x:\n    image: x\n")
    return str(tmp_path)


@pytest.mark.unit
class TestConfigSetEnvCli:
    def test_set_env_development_writes_env_and_restarts(self, monkeypatch, compose_dir):
        """set env DEVELOPMENT → 写 .env（GINKGO_ENV + -test host）+ 触发 compose 重启。"""
        compose_file = os.path.join(compose_dir, "docker-compose.yml")
        monkeypatch.setattr(GinkgoConfig, "COMPOSE_FILE_PATH",
                            property(lambda self: compose_file))
        monkeypatch.setattr(GCONF, "set_env", lambda v: None)  # 不污染进程 env
        captured = {"called": False}

        import ginkgo.client.config_cli as cli
        import subprocess as _sp
        monkeypatch.setattr(_sp, "run", lambda *a, **k: (captured.__setitem__("called", True) or
                                                        _SimpleResult(0)))

        cli.set("env", "DEVELOPMENT")

        env_path = os.path.join(compose_dir, ".env")
        content = open(env_path).read()
        assert "GINKGO_ENV=DEVELOPMENT" in content
        assert "GINKGO_MYSQL_HOST=mysql-test" in content
        assert captured["called"] is True

    def test_set_env_accepts_dev_alias(self, monkeypatch, compose_dir):
        """别名 DEV → DEVELOPMENT。"""
        compose_file = os.path.join(compose_dir, "docker-compose.yml")
        monkeypatch.setattr(GinkgoConfig, "COMPOSE_FILE_PATH",
                            property(lambda self: compose_file))
        captured_env = {}
        monkeypatch.setattr(GCONF, "set_env", lambda v: captured_env.__setitem__("v", v))
        import subprocess as _sp
        monkeypatch.setattr(_sp, "run", lambda *a, **k: _SimpleResult(0))

        import ginkgo.client.config_cli as cli
        cli.set("env", "DEV")
        assert captured_env["v"] == "DEVELOPMENT"

    def test_set_env_rejects_invalid(self, monkeypatch, compose_dir):
        """非法值 → 不写 .env、不重启。"""
        compose_file = os.path.join(compose_dir, "docker-compose.yml")
        monkeypatch.setattr(GinkgoConfig, "COMPOSE_FILE_PATH",
                            property(lambda self: compose_file))
        import subprocess as _sp
        monkeypatch.setattr(_sp, "run", lambda *a, **k: pytest.fail("compose 不应被调用"))

        import ginkgo.client.config_cli as cli
        cli.set("env", "STAGING")  # 非 PRODUCTION|DEVELOPMENT
        assert not os.path.exists(os.path.join(compose_dir, ".env"))

    def test_set_debug_on_does_not_restart(self, monkeypatch, compose_dir):
        """regression：set debug on 不再触发 docker compose（debug 与 DB 解耦）。"""
        monkeypatch.setattr(GCONF, "set_debug", lambda v: None)  # 不写 config.yml
        import subprocess as _sp
        monkeypatch.setattr(_sp, "run", lambda *a, **k: pytest.fail("compose 不应被调用"))

        import ginkgo.client.config_cli as cli
        cli.set("debug", "on")  # 不应触发 subprocess


class _SimpleResult:
    def __init__(self, code):
        self.returncode = code
        self.stdout = ""
        self.stderr = ""


# --- 回测/测试拒跑生产守卫 ---

def _set_env(monkeypatch, env_value):
    monkeypatch.setattr(GinkgoConfig, "ENV", property(lambda self: env_value))
    GinkgoConfig._cluster_guard_done = False


@pytest.mark.unit
class TestRefuseProduction:
    def test_engine_run_refuses_production(self, monkeypatch):
        """engine run 在 PRODUCTION env 下 Exit(1)。"""
        _set_env(monkeypatch, "PRODUCTION")
        from ginkgo.client import engine_cli
        with pytest.raises(typer.Exit):
            engine_cli.run(engine_id="any")

    def test_backtest_run_refuses_production(self, monkeypatch):
        """backtest run（core_cli.run）在 PRODUCTION env 下 Exit(1)。"""
        _set_env(monkeypatch, "PRODUCTION")
        from ginkgo.client import core_cli
        with pytest.raises(typer.Exit):
            core_cli.run(engine_id="any")

    def test_core_test_refuses_production(self, monkeypatch):
        """core test 在 PRODUCTION env 下 Exit(1)。"""
        _set_env(monkeypatch, "PRODUCTION")
        from ginkgo.client import core_cli
        with pytest.raises(typer.Exit):
            core_cli.test()

    def test_backtest_run_task_refuses_production(self, monkeypatch):
        """`ginkgo backtest run`（backtest_cli.run_task，真入口）在 PRODUCTION env 下 Exit(1)。

        ADR-028 Decision 4 守卫须覆盖真实活动入口。早期版本误把守卫加在 deprecated
        的 engine_cli.run，真入口 backtest_cli.run_task（ginkgo backtest run 的实际派发
        目标）漏覆盖，PRODUCTION 下最常用回测命令仍直连 master 写数据（review P1）。
        """
        _set_env(monkeypatch, "PRODUCTION")
        from ginkgo.client import backtest_cli
        with pytest.raises(typer.Exit):
            backtest_cli.run_task(task_id="any")

    def test_backtest_run_allows_development(self, monkeypatch):
        """DEVELOPMENT env 下守卫不触发 Exit（不误伤研发工作流）。

        守卫在函数顶部、try 之外，PRODUCTION 才抛 typer.Exit。DEVELOPMENT
        会放行进入真实装配，装配可能因无 DB 失败，但那与守卫无关——
        只要不是 typer.Exit 即证明守卫未误伤。
        """
        _set_env(monkeypatch, "DEVELOPMENT")
        from ginkgo.client import core_cli
        try:
            core_cli.run(engine_id="any")
        except typer.Exit:
            pytest.fail("DEVELOPMENT env 不应触发生产拒跑守卫")
        except Exception:
            pass  # 后续真实装配失败，与守卫行为无关
