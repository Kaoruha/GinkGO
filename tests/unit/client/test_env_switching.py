"""统一集群切换测试（ADR-026）

验证 ginkgo config set env DEVELOPMENT|PRODUCTION 经 update_env_for_env 更新 .env：
- DEVELOPMENT → GINKGO_ENV=DEVELOPMENT + CLICKHOUSE_HOST=clickhouse-test + MYSQL_HOST=mysql-test
- PRODUCTION → GINKGO_ENV=PRODUCTION + CLICKHOUSE_HOST=clickhouse-master + MYSQL_HOST=mysql-master
- Mongo 恒 master（无 -test 实例）
- .env 不存在时自动创建
- 其他变量不受影响
- 幂等：目标值已一致时返回空 dict
"""

import os
import pytest


@pytest.mark.unit
class TestEnvUpdateLogic:
    """验证 update_env_for_env 函数的核心逻辑"""

    def test_development_sets_test_hosts(self, tmp_path):
        """DEVELOPMENT 写入 test 集群主机"""
        from ginkgo.client.config_cli import update_env_for_env

        env_file = str(tmp_path / ".env")
        changed = update_env_for_env(env_file, "DEVELOPMENT")

        with open(env_file) as f:
            content = f.read()

        assert "GINKGO_ENV=DEVELOPMENT" in content
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-test" in content
        assert "GINKGO_MYSQL_HOST=mysql-test" in content
        assert "GINKGO_ENV" in changed

    def test_production_sets_master_hosts(self, tmp_path):
        """PRODUCTION 写入 master 集群主机"""
        from ginkgo.client.config_cli import update_env_for_env

        env_file = str(tmp_path / ".env")
        changed = update_env_for_env(env_file, "PRODUCTION")

        with open(env_file) as f:
            content = f.read()

        assert "GINKGO_ENV=PRODUCTION" in content
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content
        assert "GINKGO_MYSQL_HOST=mysql-master" in content

    def test_mongo_always_master(self, tmp_path):
        """Mongo 恒 master（无 -test 实例，不随 env 切）"""
        from ginkgo.client.config_cli import update_env_for_env

        env_file = str(tmp_path / ".env")
        update_env_for_env(env_file, "DEVELOPMENT")
        with open(env_file) as f:
            content_dev = f.read()
        assert "GINKGO_MONGODB_HOST=mongo-master" in content_dev

        update_env_for_env(env_file, "PRODUCTION")
        with open(env_file) as f:
            content_prod = f.read()
        assert "GINKGO_MONGODB_HOST=mongo-master" in content_prod

    def test_preserves_other_env_vars(self, tmp_path):
        """更新时保留其他环境变量"""
        from ginkgo.client.config_cli import update_env_for_env

        env_file = str(tmp_path / ".env")
        with open(env_file, "w") as f:
            f.write("MYSQL_ROOT_PASSWORD=hellomysql\n")
            f.write("GINKGO_CLICKHOUSE_HOST=clickhouse-test\n")
            f.write("SOME_OTHER_VAR=keep_me\n")

        update_env_for_env(env_file, "PRODUCTION")

        with open(env_file) as f:
            content = f.read()

        assert "MYSQL_ROOT_PASSWORD=hellomysql" in content
        assert "SOME_OTHER_VAR=keep_me" in content
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content

    def test_creates_env_file_if_not_exists(self, tmp_path):
        """.env 不存在时自动创建"""
        from ginkgo.client.config_cli import update_env_for_env

        env_file = str(tmp_path / ".env")
        assert not os.path.exists(env_file)

        changed = update_env_for_env(env_file, "DEVELOPMENT")

        assert os.path.exists(env_file)
        assert len(changed) > 0

    def test_no_change_returns_empty(self, tmp_path):
        """当前值与目标一致时返回空 dict（幂等）"""
        from ginkgo.client.config_cli import update_env_for_env

        env_file = str(tmp_path / ".env")
        update_env_for_env(env_file, "DEVELOPMENT")
        changed = update_env_for_env(env_file, "DEVELOPMENT")
        assert changed == {}

    def test_switching_prod_then_dev_reports_changes(self, tmp_path):
        """PRODUCTION → DEVELOPMENT 切换，报告变化的 key"""
        from ginkgo.client.config_cli import update_env_for_env

        env_file = str(tmp_path / ".env")
        update_env_for_env(env_file, "PRODUCTION")
        changed = update_env_for_env(env_file, "DEVELOPMENT")

        with open(env_file) as f:
            content = f.read()
        assert "GINKGO_ENV=DEVELOPMENT" in content
        assert "GINKGO_MYSQL_HOST=mysql-test" in content
        assert "GINKGO_ENV" in changed
        assert "GINKGO_MYSQL_HOST" in changed
