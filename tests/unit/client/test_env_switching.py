"""
统一环境切换测试

验证 ginkgo config set debug on/off 自动更新 .env 文件：
- debug=on → CLICKHOUSE_HOST=clickhouse-test, MYSQL_HOST=mysql-test
- debug=off → CLICKHOUSE_HOST=clickhouse-master, MYSQL_HOST=mysql-master
- .env 不存在时自动创建
- 其他变量不受影响
"""

import os
import pytest


@pytest.mark.unit
class TestEnvUpdateLogic:
    """验证 update_env_for_debug 函数的核心逻辑"""

    def test_debug_on_sets_test_hosts(self, tmp_path):
        """debug=on 时写入 test 环境主机"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        changed = update_env_for_debug(env_file, debug_on=True)

        with open(env_file) as f:
            content = f.read()

        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-test" in content
        assert "GINKGO_MYSQL_HOST=mysql-test" in content
        assert "GINKGO_CLICKHOUSE_HOST" in changed
        assert "GINKGO_MYSQL_HOST" in changed

    def test_debug_off_sets_master_hosts(self, tmp_path):
        """debug=off 时写入 master 环境主机"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        changed = update_env_for_debug(env_file, debug_on=False)

        with open(env_file) as f:
            content = f.read()

        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content
        assert "GINKGO_MYSQL_HOST=mysql-master" in content
        assert "GINKGO_CLICKHOUSE_HOST" in changed

    def test_preserves_other_env_vars(self, tmp_path):
        """更新时保留其他环境变量"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        with open(env_file, "w") as f:
            f.write("MYSQL_ROOT_PASSWORD=hellomysql\n")
            f.write("GINKGO_CLICKHOUSE_HOST=clickhouse-test\n")
            f.write("SOME_OTHER_VAR=keep_me\n")

        changed = update_env_for_debug(env_file, debug_on=False)

        with open(env_file) as f:
            content = f.read()

        assert "MYSQL_ROOT_PASSWORD=hellomysql" in content
        assert "SOME_OTHER_VAR=keep_me" in content
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content

    def test_creates_env_file_if_not_exists(self, tmp_path):
        """.env 不存在时自动创建"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        assert not os.path.exists(env_file)

        changed = update_env_for_debug(env_file, debug_on=True)

        assert os.path.exists(env_file)
        assert len(changed) > 0

    def test_no_change_returns_empty(self, tmp_path):
        """当前值与目标一致时返回空 dict"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        # 先设为 test
        update_env_for_debug(env_file, debug_on=True)
        # 再设为 test，应无变化
        changed = update_env_for_debug(env_file, debug_on=True)
        assert changed == {}

    def test_debug_mapping_table(self, tmp_path):
        """验证完整的 debug → 数据库映射"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")

        # debug=on
        changed_on = update_env_for_debug(env_file, debug_on=True)
        with open(env_file) as f:
            content_on = f.read()
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-test" in content_on
        assert "GINKGO_MYSQL_HOST=mysql-test" in content_on
        assert "GINKGO_MONGODB_HOST=mongo-master" in content_on

        # debug=off
        changed_off = update_env_for_debug(env_file, debug_on=False)
        with open(env_file) as f:
            content_off = f.read()
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content_off
        assert "GINKGO_MYSQL_HOST=mysql-master" in content_off
        assert "GINKGO_MONGODB_HOST=mongo-master" in content_off
