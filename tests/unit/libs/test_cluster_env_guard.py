# Upstream: libs/core/config.py
# Downstream: -
# Role: 回归测试 #6756 启动期集群一致性护栏（DEBUGMODE vs DB host 后缀）

"""#6756 启动期护栏：DEBUGMODE 与 DB host 后缀（master/test 体系）不一致拒启。

护栏在 GCONF.MYSQLHOST/CLICKHOST 首次访问时惰性触发，幂等。本套件每用例
重置幂等标志 + monkeypatch 环境变量隔离验证。
"""

import pytest
from ginkgo.libs.core.config import GCONF, GinkgoConfig


def _trigger(monkeypatch, dbg: str, mh: str, ch: str, skip: str = "0") -> str:
    """重置护栏幂等标志并按给定环境触发一次校验，返回解析的 MySQL host。"""
    monkeypatch.setenv("GINKGO_DEBUG_MODE", dbg)
    monkeypatch.setenv("GINKGO_MYSQL_HOST", mh)
    monkeypatch.setenv("GINKGO_CLICKHOUSE_HOST", ch)
    monkeypatch.setenv("GINKGO_SKIP_CLUSTER_GUARD", skip)
    GinkgoConfig._cluster_guard_done = False
    return GCONF.MYSQLHOST


def test_conflict_prod_mode_but_test_host_raises(monkeypatch):
    """debug=off(生产) 却连 -test 集群 → 拒启（防真实运行静默连 test）。"""
    with pytest.raises(RuntimeError, match="Ginkgo Env Guard"):
        _trigger(monkeypatch, "FALSE", "mysql-test", "clickhouse-test")


def test_conflict_test_mode_but_master_host_raises(monkeypatch):
    """debug=on(测试) 却连 -master 集群 → 拒启（防测试写脏生产数据）。"""
    with pytest.raises(RuntimeError, match="Ginkgo Env Guard"):
        _trigger(monkeypatch, "TRUE", "mysql-master", "clickhouse-master")


def test_consistent_test_env_ok(monkeypatch):
    """debug=on + -test 集群 → 放行。"""
    assert _trigger(monkeypatch, "TRUE", "mysql-test", "clickhouse-test") == "mysql-test"


def test_consistent_prod_env_ok(monkeypatch):
    """debug=off + -master 集群 → 放行。"""
    assert _trigger(monkeypatch, "FALSE", "mysql-master", "clickhouse-master") == "mysql-master"


def test_localhost_host_skips_assertion(monkeypatch):
    """localhost/外部域名不在 master/test 体系 → 断言跳过，不误伤外部部署。"""
    assert _trigger(monkeypatch, "FALSE", "localhost", "localhost") == "localhost"


def test_skip_guard_escape_hatch(monkeypatch):
    """GINKGO_SKIP_CLUSTER_GUARD=1 → 冲突也放行（测试/特殊部署逃生口）。"""
    assert _trigger(monkeypatch, "FALSE", "mysql-test", "clickhouse-test", skip="1") == "mysql-test"


def test_guard_is_idempotent(monkeypatch):
    """幂等：同进程第二次访问 host 不再重复触发断言/横幅。"""
    monkeypatch.setenv("GINKGO_DEBUG_MODE", "TRUE")
    monkeypatch.setenv("GINKGO_MYSQL_HOST", "mysql-test")
    monkeypatch.setenv("GINKGO_CLICKHOUSE_HOST", "clickhouse-test")
    GinkgoConfig._cluster_guard_done = False
    assert GCONF.MYSQLHOST == "mysql-test"
    # 第二次把环境改成冲突态，因幂等已不再校验，不应抛
    monkeypatch.setenv("GINKGO_DEBUG_MODE", "FALSE")
    assert GCONF.MYSQLHOST == "mysql-test"
