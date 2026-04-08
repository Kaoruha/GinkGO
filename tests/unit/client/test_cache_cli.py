"""
性能: 221MB RSS, 2.0s, 19 tests [PASS]
Cache CLI 单元测试

测试 ginkgo.client.cache_cli 的所有命令：
- clear: 清除 Redis 缓存（支持 all/function/sync/tick 类型）
- status: 显示缓存状态和统计
- list: 列出缓存条目

Mock 策略：
  - 各命令在函数内部 import container -> patch "ginkgo.data.containers.container"
  - patch Redis 服务方法（clear_function_cache, clear_all_sync_progress 等）
  - patch "ginkgo.data.redis_schema.RedisKeyPattern" 用于 list/status 中的模式匹配
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from ginkgo.client import cache_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_redis_service():
    """Mock redis_service，预设常用方法"""
    m = MagicMock()
    m.clear_function_cache.return_value = 5
    m.clear_all_sync_progress.return_value = 3
    m.clear_sync_progress.return_value = 1
    m.get_redis_info.return_value = {"connected": True, "version": "7.0.0"}
    # crud_repo 用于 keys() 查询
    m.crud_repo.keys.return_value = []
    return m


@pytest.fixture
def mock_tick_service():
    """Mock tick_service，用于 tick 缓存清除"""
    m = MagicMock()
    m.clear_sync_cache.return_value = "cleared 2 entries"
    return m


@pytest.fixture
def mock_container(mock_redis_service, mock_tick_service):
    """Mock container，提供 redis_service 和 tick_service"""
    m = MagicMock()
    m.redis_service.return_value = mock_redis_service
    m.tick_service.return_value = mock_tick_service
    return m


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestCacheHelp:
    """cache 命令帮助信息"""

    def test_cache_root_help_shows_commands(self, cli_runner):
        """cache --help 显示所有可用子命令"""
        result = cli_runner.invoke(cache_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "clear" in result.output
        assert "status" in result.output
        assert "list" in result.output

    def test_cache_clear_help(self, cli_runner):
        """cache clear --help 显示 clear 命令的参数和用法"""
        result = cli_runner.invoke(cache_cli.app, ["clear", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output
        assert "--code" in result.output
        assert "--force" in result.output


# ============================================================================
# 2. clear 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestCacheClear:
    """cache clear 命令测试"""

    def test_clear_all_with_force(self, cli_runner, mock_container):
        """clear --type all --force 清除所有缓存"""
        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(cache_cli.app, ["clear", "--type", "all", "--force"])
        assert result.exit_code == 0
        assert "Successfully cleared" in result.output
        mock_container.redis_service.return_value.clear_function_cache.assert_called_once()
        mock_container.redis_service.return_value.clear_all_sync_progress.assert_called_once()

    def test_clear_function_all(self, cli_runner, mock_container):
        """clear --type function --force 清除所有函数缓存"""
        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(cache_cli.app, ["clear", "--type", "function", "--force"])
        assert result.exit_code == 0
        assert "Successfully cleared" in result.output
        mock_container.redis_service.return_value.clear_function_cache.assert_called_once_with(None)

    def test_clear_function_by_name(self, cli_runner, mock_container):
        """clear --type function --name get_bars --force 清除指定函数缓存"""
        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(
                cache_cli.app, ["clear", "--type", "function", "--name", "get_bars", "--force"]
            )
        assert result.exit_code == 0
        assert "Successfully cleared" in result.output
        mock_container.redis_service.return_value.clear_function_cache.assert_called_once_with("get_bars")

    def test_clear_sync_with_code(self, cli_runner, mock_container):
        """clear --type sync --code 000001.SZ --force 清除同步缓存"""
        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(
                cache_cli.app, ["clear", "--type", "sync", "--code", "000001.SZ", "--force"]
            )
        assert result.exit_code == 0
        assert "Successfully cleared" in result.output
        mock_container.redis_service.return_value.clear_sync_progress.assert_called()

    def test_clear_tick_with_code(self, cli_runner, mock_container):
        """clear --type tick --code 000001.SZ --force 清除 tick 缓存"""
        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(
                cache_cli.app, ["clear", "--type", "tick", "--code", "000001.SZ", "--force"]
            )
        assert result.exit_code == 0
        assert "Successfully cleared" in result.output
        mock_container.tick_service.return_value.clear_sync_cache.assert_called_once_with("000001.SZ")

    def test_clear_sync_without_code_fails(self, cli_runner):
        """sync 类型缺少 --code 参数时报错"""
        result = cli_runner.invoke(cache_cli.app, ["clear", "--type", "sync", "--force"])
        assert result.exit_code == 1
        assert "--code" in result.output

    def test_clear_tick_without_code_fails(self, cli_runner):
        """tick 类型缺少 --code 参数时报错"""
        result = cli_runner.invoke(cache_cli.app, ["clear", "--type", "tick", "--force"])
        assert result.exit_code == 1
        assert "--code" in result.output

    def test_clear_redis_error(self, cli_runner, mock_container):
        """Redis 服务异常时 clear 命令返回错误"""
        mock_container.redis_service.return_value.clear_function_cache.side_effect = Exception("Connection lost")
        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(cache_cli.app, ["clear", "--type", "all", "--force"])
        assert result.exit_code == 1
        assert "Error clearing cache" in result.output


# ============================================================================
# 3. status 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestCacheStatus:
    """cache status 命令测试"""

    def test_status_connected(self, cli_runner, mock_container):
        """Redis 已连接时显示连接状态"""
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["status"])
        assert result.exit_code == 0
        assert "Cache Status Report" in result.output
        assert "Connected" in result.output

    def test_status_empty_cache(self, cli_runner, mock_container):
        """缓存为空时显示 Empty 状态"""
        mock_container.redis_service.return_value.crud_repo.keys.return_value = []
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["status"])
        assert result.exit_code == 0
        assert "Empty" in result.output

    def test_status_redis_disconnected(self, cli_runner, mock_container):
        """Redis 未连接时显示 Disconnected 状态"""
        mock_container.redis_service.return_value.get_redis_info.return_value = {
            "connected": False,
            "error": "Connection refused"
        }
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["status"])
        assert result.exit_code == 0
        assert "Disconnected" in result.output

    def test_status_service_error(self, cli_runner):
        """Redis 服务不可用时显示错误信息"""
        mock_broken = MagicMock()
        mock_broken.redis_service.side_effect = Exception("Service unavailable")
        with patch("ginkgo.data.containers.container", mock_broken), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["status"])
        assert result.exit_code == 0
        assert "Error" in result.output


# ============================================================================
# 4. list 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestCacheList:
    """cache list 命令测试"""

    def test_list_no_filter_empty(self, cli_runner, mock_container):
        """无过滤条件且缓存为空时显示提示"""
        mock_container.redis_service.return_value.crud_repo.keys.return_value = []
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["list"])
        assert result.exit_code == 0
        assert "No cache entries found" in result.output

    def test_list_with_function_entries(self, cli_runner, mock_container):
        """存在函数缓存条目时正确展示"""
        mock_container.redis_service.return_value.crud_repo.keys.return_value = [
            "ginkgo_func_cache_get_bars_000001.SZ",
        ]
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Function" in result.output
        assert "get_bars" in result.output

    def test_list_with_sync_entries(self, cli_runner, mock_container):
        """存在同步进度缓存条目时正确展示"""
        mock_container.redis_service.return_value.crud_repo.keys.return_value = [
            "bar_update_000001.SZ",
        ]
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Sync Progress" in result.output
        assert "000001.SZ" in result.output

    def test_list_error(self, cli_runner):
        """Redis 服务异常时 list 命令返回错误"""
        mock_broken = MagicMock()
        mock_broken.redis_service.side_effect = Exception("Connection lost")
        with patch("ginkgo.data.containers.container", mock_broken), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["list"])
        assert result.exit_code == 1
        assert "Error listing cache entries" in result.output

    def test_list_with_limit(self, cli_runner, mock_container):
        """--limit 参数控制返回条目数"""
        mock_container.redis_service.return_value.crud_repo.keys.return_value = [
            f"ginkgo_func_cache_func_{i}" for i in range(10)
        ]
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.data.redis_schema.RedisKeyPattern") as mock_pattern:
            mock_pattern.FUNC_CACHE_ALL = "ginkgo_func_cache_*"
            mock_pattern.SYNC_PROGRESS_ALL = "*_update_*"
            result = cli_runner.invoke(cache_cli.app, ["list", "--limit", "3"])
        assert result.exit_code == 0
        assert "Showing first 3" in result.output
