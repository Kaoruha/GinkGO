# Upstream: libs/core/config.py
# Downstream: -
# Role: ADR-028 GINKGO_ENV + 启动期集群护栏 smoke（diff coverage gate #6135 采集）

"""ADR-028 GINKGO_ENV 单一旋钮 + 启动期集群一致性护栏 smoke。

#6756/#6773 PR 在 config.py 新增的可执行逻辑——ENV property（bridge 推断）、
IS_DEV_ENV、set_env、_assert_cluster_consistency——被 import 链触达（几乎所有
gate 测试 from ginkgo.libs import GCONF）但方法体无 smoke 调用：gate 测试不读
CLICKHOST/MYSQLHOST 故 _assert 从不触发，ENV 也只在 IS_DEV_ENV/_assert 间接
读取。→ diff coverage gate 红（20% < 80%）。

本 smoke 调起方法体补覆盖信号，并锁定集群选择 + 护栏新契约：
- bridge：GINKGO_ENV 未设时从 DEBUGMODE 推断（True→DEVELOPMENT）并材料化到 environ
- ENV 显式值 upper() 归一
- set_env 合法/非法校验
- _assert：DEV 一致（不 raise+绿横幅）/ 幂等（二次静默）/ 冲突 raise / SKIP 逃生
"""

import os
import pytest
from ginkgo.libs.core.config import GinkgoConfig, GCONF

_ENV_KEYS = (
    "GINKGO_ENV",
    "GINKGO_SKIP_CLUSTER_GUARD",
    "GINKGO_MYSQL_HOST",
    "GINKGO_CLICKHOUSE_HOST",
)


@pytest.fixture(autouse=True)
def _isolate_env():
    """每测试重置护栏幂等标志 + 清理相关 env，防跨测试污染。"""
    GinkgoConfig._cluster_guard_done = False
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    yield
    GinkgoConfig._cluster_guard_done = False
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


@pytest.mark.unit
class TestEnvClusterGuardSmoke:
    def test_env_bridge_from_debugmode_true(self, monkeypatch):
        """GINKGO_ENV 未设 + DEBUGMODE=True → bridge 推断 DEVELOPMENT 并材料化。"""
        monkeypatch.setattr(GinkgoConfig, "DEBUGMODE", property(lambda self: True))
        assert os.environ.get("GINKGO_ENV") is None
        assert GCONF.ENV == "DEVELOPMENT"
        assert os.environ["GINKGO_ENV"] == "DEVELOPMENT"
        assert GCONF.IS_DEV_ENV is True

    def test_env_bridge_from_debugmode_false(self, monkeypatch):
        """GINKGO_ENV 未设 + DEBUGMODE=False → bridge 推断 PRODUCTION。"""
        monkeypatch.setattr(GinkgoConfig, "DEBUGMODE", property(lambda self: False))
        assert GCONF.ENV == "PRODUCTION"
        assert GCONF.IS_DEV_ENV is False

    def test_env_explicit_upper_normalized(self):
        """显式 GINKGO_ENV 小写值 → upper() 归一。"""
        os.environ["GINKGO_ENV"] = "development"
        assert GCONF.ENV == "DEVELOPMENT"

    def test_set_env_valid_and_invalid(self):
        """set_env：合法值 upper 后写入；非法值 raise ValueError。

        set_env 不做别名（DEV→DEVELOPMENT 别名在 config_cli.set 层），只接受
        PRODUCTION/DEVELOPMENT（upper 归一后）。
        """
        GCONF.set_env("development")
        assert os.environ["GINKGO_ENV"] == "DEVELOPMENT"
        GCONF.set_env("production")
        assert os.environ["GINKGO_ENV"] == "PRODUCTION"
        with pytest.raises(ValueError):
            GCONF.set_env("STAGING")

    def test_assert_dev_consistent_banner(self, monkeypatch, capsys):
        """DEV + mysql-test/clickhouse-test → 不 raise，打绿色 [TEST] 横幅。"""
        monkeypatch.setattr(GinkgoConfig, "DEBUGMODE", property(lambda self: True))
        os.environ["GINKGO_MYSQL_HOST"] = "mysql-test"
        os.environ["GINKGO_CLICKHOUSE_HOST"] = "clickhouse-test"
        # 读 CLICKHOST 触发 _assert_cluster_consistency
        assert GCONF.CLICKHOST == "clickhouse-test"
        assert GCONF.MYSQLHOST == "mysql-test"
        assert "[TEST]" in capsys.readouterr().err

    def test_assert_idempotent(self, monkeypatch, capsys):
        """二次读 host 不再打横幅（幂等）。"""
        monkeypatch.setattr(GinkgoConfig, "DEBUGMODE", property(lambda self: True))
        _ = GCONF.MYSQLHOST
        _ = GCONF.CLICKHOST
        assert capsys.readouterr().err.count("[TEST]") == 1

    def test_assert_conflict_raises(self, monkeypatch):
        """PRODUCTION env 但 host=-test → raise RuntimeError。"""
        os.environ["GINKGO_ENV"] = "PRODUCTION"
        os.environ["GINKGO_MYSQL_HOST"] = "mysql-test"
        with pytest.raises(RuntimeError, match="Env Guard"):
            _ = GCONF.MYSQLHOST

    def test_assert_skip_flag_bypasses_assertion(self, monkeypatch, capsys):
        """GINKGO_SKIP_CLUSTER_GUARD=1 跳断言（冲突也不 raise，横幅照打）。"""
        os.environ["GINKGO_ENV"] = "PRODUCTION"
        os.environ["GINKGO_MYSQL_HOST"] = "mysql-test"
        os.environ["GINKGO_SKIP_CLUSTER_GUARD"] = "1"
        # 不 raise（SKIP 生效）
        assert GCONF.MYSQLHOST == "mysql-test"
        assert "[PROD]" in capsys.readouterr().err
