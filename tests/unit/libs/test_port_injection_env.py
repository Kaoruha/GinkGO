# Upstream: libs/core/config.py
# Downstream: -
# Role: 回归测试端口 +1 守卫判据改用 IS_DEV_ENV（ADR-028，与 DEBUGMODE 解耦）

"""端口 +1 守卫测试（ADR-028）。

CLICKPORT/MYSQLPORT 的首位 +1 判据从 DEBUGMODE 改为 IS_DEV_ENV（集群选择），
容器守卫与幂等保留。覆盖：
- DEVELOPMENT 非容器 → +1（13306/18123）
- PRODUCTION → 不 +1（3306/8123）
- PRODUCTION + DEBUGMODE=True → 不 +1（解耦核心回归：DEBUGMODE 不再驱动 +1）
- 容器内 DEVELOPMENT → 守卫跳过 +1（连内部端口）
- 幂等：端口已以 1 开头（映射端口）不重复加
"""

import pytest
import ginkgo.libs.utils.log_utils as _lu
from ginkgo.libs.core.config import GCONF, GinkgoConfig


def _setup(monkeypatch, env, container, debug="FALSE",
           mysql_port="3306", click_port="8123"):
    """隔离环境 + 确定性容器检测，聚焦端口派生逻辑。"""
    monkeypatch.setenv("GINKGO_ENV", env)
    monkeypatch.setenv("GINKGO_DEBUG_MODE", debug)
    monkeypatch.setenv("GINKGO_MYSQL_PORT", mysql_port)
    monkeypatch.setenv("GINKGO_CLICKHOUSE_PORT", click_port)
    monkeypatch.setenv("GINKGO_SKIP_CLUSTER_GUARD", "1")  # 跳 host 断言，聚焦端口
    monkeypatch.setattr(_lu, "is_container_environment", lambda: container)
    GinkgoConfig._cluster_guard_done = False


@pytest.mark.unit
class TestPortInjectionEnv:
    def test_dev_non_container_plus_one(self, monkeypatch):
        """DEVELOPMENT + 宿主客户端 → 端口首位 +1。"""
        _setup(monkeypatch, "DEVELOPMENT", container=False, debug="TRUE")
        assert GCONF.MYSQLPORT == 13306
        assert GCONF.CLICKPORT == 18123

    def test_prod_no_plus_one(self, monkeypatch):
        """PRODUCTION → 原端口，不 +1。"""
        _setup(monkeypatch, "PRODUCTION", container=False, debug="FALSE")
        assert GCONF.MYSQLPORT == 3306
        assert GCONF.CLICKPORT == 8123

    def test_prod_with_debug_true_no_plus_one(self, monkeypatch):
        """解耦核心回归：PRODUCTION + DEBUGMODE=True → 仍 3306（DEBUGMODE 不再驱动 +1）。"""
        _setup(monkeypatch, "PRODUCTION", container=False, debug="TRUE")
        assert GCONF.MYSQLPORT == 3306
        assert GCONF.CLICKPORT == 8123

    def test_dev_in_container_no_plus_one(self, monkeypatch):
        """容器内 DEVELOPMENT → 守卫跳过 +1（连内部端口 3306/8123）。"""
        _setup(monkeypatch, "DEVELOPMENT", container=True, debug="TRUE")
        assert GCONF.MYSQLPORT == 3306
        assert GCONF.CLICKPORT == 8123

    def test_idempotent_already_mapped_port(self, monkeypatch):
        """幂等：端口已以 1 开头（已是映射端口）不重复加。"""
        _setup(monkeypatch, "DEVELOPMENT", container=False, debug="TRUE",
               mysql_port="13306", click_port="18123")
        assert GCONF.MYSQLPORT == 13306
        assert GCONF.CLICKPORT == 18123
