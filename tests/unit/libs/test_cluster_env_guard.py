# Upstream: libs/core/config.py
# Downstream: -
# Role: 回归测试启动期集群一致性护栏（ADR-026：GINKGO_ENV vs DB host 后缀）

"""启动期护栏：GINKGO_ENV（DEVELOPMENT/PRODUCTION）与 DB host 后缀不一致拒启。

ADR-026 起，护栏判据从 DEBUGMODE 改为 IS_DEV_ENV（集群选择单一旋钮）。
护栏在 GCONF.MYSQLHOST/CLICKHOST 首次访问时惰性触发，幂等。本套件每用例
重置幂等标志 + monkeypatch 环境变量隔离验证，另覆盖 bridge-default 迁移逻辑。
"""

import pytest
from ginkgo.libs.core.config import GCONF, GinkgoConfig


@pytest.fixture(autouse=True)
def _isolate_config_yml(monkeypatch, tmp_path):
    """隔离 config.yml：防 set_env 写 env 字位污染全局 GCONF 单例的 bridge 测试。

    ADR-028 review Q5 修复后 ENV property 优先读 config.yml env 字位；若其他测试
    （如 smoke 的 test_set_env_valid_and_invalid）调 set_env 写了真实 ~/.ginkgo/config.yml
    的 env 字位，本套件 bridge 测试（期望未设 env 时从 DEBUGMODE 推断）会读到残留而失效。
    把 setting_path 指到 tmp_path 干净 config.yml（无 env 字位）保证 bridge 正常触发。
    """
    cfg = tmp_path / "config.yml"
    cfg.write_text("debug: False\n")
    monkeypatch.setattr(GinkgoConfig, "setting_path", property(lambda self: str(cfg)))
    GCONF._config_cache = {}
    GCONF._config_mtime = 0
    yield
    GCONF._config_cache = {}
    GCONF._config_mtime = 0


def _trigger(monkeypatch, env: str, mh: str, ch: str, skip: str = "0") -> str:
    """重置护栏幂等标志并按给定 GINKGO_ENV 触发一次校验，返回解析的 MySQL host。"""
    monkeypatch.setenv("GINKGO_ENV", env)
    monkeypatch.setenv("GINKGO_MYSQL_HOST", mh)
    monkeypatch.setenv("GINKGO_CLICKHOUSE_HOST", ch)
    monkeypatch.setenv("GINKGO_SKIP_CLUSTER_GUARD", skip)
    GinkgoConfig._cluster_guard_done = False
    return GCONF.MYSQLHOST


def test_conflict_prod_env_but_test_host_raises(monkeypatch):
    """PRODUCTION 却连 -test 集群 → 拒启（防真实运行静默连 test）。"""
    with pytest.raises(RuntimeError, match="Ginkgo Env Guard"):
        _trigger(monkeypatch, "PRODUCTION", "mysql-test", "clickhouse-test")


def test_conflict_dev_env_but_master_host_raises(monkeypatch):
    """DEVELOPMENT 却连 -master 集群 → 拒启（防测试写脏生产数据）。"""
    with pytest.raises(RuntimeError, match="Ginkgo Env Guard"):
        _trigger(monkeypatch, "DEVELOPMENT", "mysql-master", "clickhouse-master")


def test_consistent_dev_env_ok(monkeypatch):
    """DEVELOPMENT + -test 集群 → 放行。"""
    assert _trigger(monkeypatch, "DEVELOPMENT", "mysql-test", "clickhouse-test") == "mysql-test"


def test_consistent_prod_env_ok(monkeypatch):
    """PRODUCTION + -master 集群 → 放行。"""
    assert _trigger(monkeypatch, "PRODUCTION", "mysql-master", "clickhouse-master") == "mysql-master"


def test_localhost_host_skips_assertion(monkeypatch):
    """localhost/外部域名不在 master/test 体系 → 断言跳过，不误伤外部部署。"""
    assert _trigger(monkeypatch, "PRODUCTION", "localhost", "localhost") == "localhost"


def test_skip_guard_escape_hatch(monkeypatch):
    """GINKGO_SKIP_CLUSTER_GUARD=1 → 冲突也放行（测试/特殊部署逃生口）。"""
    assert _trigger(monkeypatch, "PRODUCTION", "mysql-test", "clickhouse-test", skip="1") == "mysql-test"


def test_guard_is_idempotent(monkeypatch):
    """幂等：同进程第二次访问 host 不再重复触发断言/横幅。"""
    monkeypatch.setenv("GINKGO_ENV", "DEVELOPMENT")
    monkeypatch.setenv("GINKGO_MYSQL_HOST", "mysql-test")
    monkeypatch.setenv("GINKGO_CLICKHOUSE_HOST", "clickhouse-test")
    GinkgoConfig._cluster_guard_done = False
    assert GCONF.MYSQLHOST == "mysql-test"
    # 第二次把环境改成冲突态，因幂等已不再校验，不应抛
    monkeypatch.setenv("GINKGO_ENV", "PRODUCTION")
    assert GCONF.MYSQLHOST == "mysql-test"


# --- bridge-default 迁移逻辑（ADR-026 Decision 2）---

def test_bridge_unset_debug_true_is_dev(monkeypatch):
    """GINKGO_ENV 未设 + DEBUGMODE=True → bridge 推断 DEVELOPMENT。"""
    monkeypatch.delenv("GINKGO_ENV", raising=False)
    monkeypatch.setenv("GINKGO_DEBUG_MODE", "TRUE")
    assert GCONF.ENV == "DEVELOPMENT"
    assert GCONF.IS_DEV_ENV is True


def test_bridge_unset_debug_false_is_prod(monkeypatch):
    """GINKGO_ENV 未设 + DEBUGMODE=False → bridge 推断 PRODUCTION。"""
    monkeypatch.delenv("GINKGO_ENV", raising=False)
    monkeypatch.setenv("GINKGO_DEBUG_MODE", "FALSE")
    assert GCONF.ENV == "PRODUCTION"
    assert GCONF.IS_DEV_ENV is False


def test_explicit_env_overrides_debugmode(monkeypatch):
    """显式 GINKGO_ENV 优先于 DEBUGMODE（bridge 不触发）。"""
    monkeypatch.setenv("GINKGO_ENV", "PRODUCTION")
    monkeypatch.setenv("GINKGO_DEBUG_MODE", "TRUE")
    assert GCONF.ENV == "PRODUCTION"
    assert GCONF.IS_DEV_ENV is False


def test_env_lowercase_normalized(monkeypatch):
    """取值统一大写（小写输入经 .upper() 归一）。"""
    monkeypatch.setenv("GINKGO_ENV", "development")
    assert GCONF.ENV == "DEVELOPMENT"
    monkeypatch.setenv("GINKGO_ENV", "production")
    assert GCONF.ENV == "PRODUCTION"
