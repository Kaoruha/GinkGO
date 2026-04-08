"""
性能: 220MB RSS, 2.05s, 41 tests [PASS]
Config CLI 单元测试

测试 ginkgo.client.config_cli 的所有命令：
- get: 获取配置值
- set: 设置配置值
- list: 列出所有配置
- reset: 重置为默认值
- workers: 旧版 Worker 管理
- containers: Docker 容器管理
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from ginkgo.client import config_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_gconf():
    m = MagicMock()
    m.DEBUGMODE = True
    m.QUIET = False
    m.CPURATIO = 0.8
    m.LOGGING_PATH = "/tmp/ginkgo/logs"
    m.WORKING_PATH = "/home/kaoru/Ginkgo"
    m.CLICKHOST = "localhost"
    m.CLICKPORT = 8123
    m.MYSQLHOST = "localhost"
    m.MYSQLPORT = 3306
    m.MYSQLUSER = "root"
    m.MYSQLPWD = ""
    m.MONGOPORT = 27017
    m.MONGOHOST = "localhost"
    m.MONGOUSER = ""
    m.MONGOPWD = ""
    m.REDISHOST = "localhost"
    m.REDISPORT = 6379
    m.KAFKAHOST = "localhost"
    m.KAFKAPORT = 9092
    return m


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestConfigHelp:
    """config 命令帮助信息"""

    def test_config_root_help_shows_commands(self, cli_runner):
        """config --help 显示所有可用命令"""
        result = cli_runner.invoke(config_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "get" in result.output
        assert "set" in result.output
        assert "list" in result.output
        assert "reset" in result.output
        assert "workers" in result.output
        assert "containers" in result.output

    def test_config_get_help(self, cli_runner):
        """config get --help 显示 get 命令用法"""
        result = cli_runner.invoke(config_cli.app, ["get", "--help"])
        assert result.exit_code == 0
        assert "Configuration key" in result.output or "key" in result.output


# ============================================================================
# 2. get 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestConfigGet:
    """config get 命令测试"""

    def test_get_without_args_shows_all_config(self, cli_runner, mock_gconf):
        """get 不带参数时显示所有配置"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["get"])
        assert result.exit_code == 0
        assert "debug" in result.output
        assert "quiet" in result.output
        assert "cpu_ratio" in result.output
        assert "log_path" in result.output
        assert "working_path" in result.output

    def test_get_debug_shows_debug_value(self, cli_runner, mock_gconf):
        """get debug 显示 debug 模式值"""
        mock_gconf.DEBUGMODE = True
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["get", "debug"])
        assert result.exit_code == 0
        assert "debug" in result.output
        assert "True" in result.output

    def test_get_quiet_shows_quiet_value(self, cli_runner, mock_gconf):
        """get quiet 显示 quiet 模式值"""
        mock_gconf.QUIET = False
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["get", "quiet"])
        assert result.exit_code == 0
        assert "quiet" in result.output
        assert "False" in result.output

    def test_get_cpu_ratio_shows_value(self, cli_runner, mock_gconf):
        """get cpu_ratio 显示 CPU 使用率"""
        mock_gconf.CPURATIO = 0.8
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["get", "cpu_ratio"])
        assert result.exit_code == 0
        assert "cpu_ratio" in result.output
        assert "80" in result.output

    def test_get_unknown_key_shows_not_found(self, cli_runner, mock_gconf):
        """get 未知 key 显示 not found"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["get", "nonexistent_key"])
        assert result.exit_code == 0
        assert "not found" in result.output or "not found" in result.output.lower()

    def test_get_handles_exception(self, cli_runner):
        """get 命令异常时优雅处理"""
        # Use a real object whose attribute access raises to trigger the
        # exception path inside the function's try/except.
        class BrokenConfig:
            @property
            def DEBUGMODE(self):
                raise Exception("db error")
        with patch("ginkgo.libs.GCONF", BrokenConfig()):
            result = cli_runner.invoke(config_cli.app, ["get", "debug"])
        assert result.exit_code == 0
        assert "Failed" in result.output or "error" in result.output.lower()


# ============================================================================
# 3. set 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestConfigSet:
    """config set 命令测试"""

    def test_set_debug_on(self, cli_runner, mock_gconf):
        """set debug on 启用 debug 模式"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["set", "debug", "on"])
        assert result.exit_code == 0
        mock_gconf.set_debug.assert_called_once_with(True)
        assert "debug" in result.output.lower()

    def test_set_debug_off(self, cli_runner, mock_gconf):
        """set debug off 关闭 debug 模式"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["set", "debug", "off"])
        assert result.exit_code == 0
        mock_gconf.set_debug.assert_called_once_with(False)

    def test_set_quiet_on(self, cli_runner, mock_gconf):
        """set quiet on 启用 quiet 模式"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["set", "quiet", "on"])
        assert result.exit_code == 0
        mock_gconf.set_quiet.assert_called_once_with(True)
        assert "quiet" in result.output.lower()

    def test_set_quiet_off(self, cli_runner, mock_gconf):
        """set quiet off 关闭 quiet 模式"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["set", "quiet", "off"])
        assert result.exit_code == 0
        mock_gconf.set_quiet.assert_called_once_with(False)

    def test_set_cpu_ratio(self, cli_runner, mock_gconf):
        """set cpu_ratio 设置 CPU 使用率"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["set", "cpu_ratio", "70"])
        assert result.exit_code == 0
        mock_gconf.set_cpu_ratio.assert_called_once_with(0.7)
        assert "70" in result.output

    def test_set_missing_key_shows_error(self, cli_runner, mock_gconf):
        """set 缺少 key 时显示错误"""
        result = cli_runner.invoke(config_cli.app, ["set"])
        assert result.exit_code != 0

    def test_set_missing_value_shows_error(self, cli_runner, mock_gconf):
        """set 缺少 value 时显示错误"""
        result = cli_runner.invoke(config_cli.app, ["set", "debug"])
        assert result.exit_code != 0

    def test_set_unknown_key_shows_not_found(self, cli_runner, mock_gconf):
        """set 未知 key 显示 not found"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["set", "bad_key", "value"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_set_handles_exception(self, cli_runner):
        """set 命令异常时优雅处理"""
        class BrokenConfig:
            def set_debug(self, val):
                raise Exception("db error")
        with patch("ginkgo.libs.GCONF", BrokenConfig()):
            result = cli_runner.invoke(config_cli.app, ["set", "debug", "on"])
        assert result.exit_code == 0
        assert "Failed" in result.output


# ============================================================================
# 4. list 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestConfigList:
    """config list 命令测试"""

    def test_list_shows_all_config_keys(self, cli_runner, mock_gconf):
        """list 显示所有配置键"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["list"])
        assert result.exit_code == 0
        assert "debug" in result.output
        assert "quiet" in result.output
        assert "cpu_ratio" in result.output
        assert "log_path" in result.output
        assert "working_path" in result.output

    def test_list_shows_usage_examples(self, cli_runner, mock_gconf):
        """list 显示使用示例"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Usage" in result.output or "Examples" in result.output or "config set" in result.output

    def test_list_handles_exception(self, cli_runner):
        """list 命令异常时优雅处理"""
        # list 命令只执行了 import GCONF 但不访问属性，需要让 import 本身失败
        import ginkgo.libs as libs_module
        original = libs_module.GCONF
        try:
            delattr(libs_module, "GCONF")
            result = cli_runner.invoke(config_cli.app, ["list"])
            assert result.exit_code == 0
            assert "Failed" in result.output
        finally:
            libs_module.GCONF = original


# ============================================================================
# 5. reset 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestConfigReset:
    """config reset 命令测试"""

    def test_reset_calls_gconf_methods(self, cli_runner, mock_gconf):
        """reset 调用 GCONF 的各 set 方法"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["reset"])
        assert result.exit_code == 0
        mock_gconf.set_debug.assert_called_once_with(False)
        mock_gconf.set_quiet.assert_called_once_with(False)
        mock_gconf.set_cpu_ratio.assert_called_once_with(80.0)

    def test_reset_shows_success_message(self, cli_runner, mock_gconf):
        """reset 显示成功消息"""
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(config_cli.app, ["reset"])
        assert result.exit_code == 0
        assert "reset" in result.output.lower() or "defaults" in result.output.lower()

    def test_reset_handles_exception(self, cli_runner):
        """reset 命令异常时优雅处理"""
        class BrokenConfig:
            def set_debug(self, val):
                raise Exception("reset fail")
        with patch("ginkgo.libs.GCONF", BrokenConfig()):
            result = cli_runner.invoke(config_cli.app, ["reset"])
        assert result.exit_code == 0
        assert "Failed" in result.output


# ============================================================================
# 6. workers 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestConfigWorkers:
    """config workers 命令测试"""

    def test_workers_status_no_workers(self, cli_runner, mock_gtm):
        """workers status 无活跃 worker 时显示提示"""
        mock_gtm.get_workers_status.return_value = {}
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()):
            result = cli_runner.invoke(config_cli.app, ["workers", "status"])
        assert result.exit_code == 0
        assert "No active" in result.output or "not available" in result.output.lower()

    def test_workers_status_with_workers(self, cli_runner, mock_gtm):
        """workers status 有活跃 worker 时显示状态"""
        mock_gtm.get_workers_status.return_value = {
            "worker-1": {"running": True},
            "worker-2": {"running": False},
        }
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()):
            result = cli_runner.invoke(config_cli.app, ["workers", "status"])
        assert result.exit_code == 0
        assert "worker-1" in result.output
        assert "worker-2" in result.output

    def test_workers_start(self, cli_runner, mock_gtm):
        """workers start 启动 worker"""
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()):
            result = cli_runner.invoke(config_cli.app, ["workers", "start"])
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_workers_start_with_count(self, cli_runner, mock_gtm):
        """workers start --count N 启动指定数量 worker"""
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()):
            result = cli_runner.invoke(config_cli.app, ["workers", "start", "--count", "4"])
        assert result.exit_code == 0
        assert "4" in result.output

    def test_workers_stop(self, cli_runner, mock_gtm):
        """workers stop 停止所有 worker"""
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()):
            result = cli_runner.invoke(config_cli.app, ["workers", "stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

    def test_workers_restart(self, cli_runner, mock_gtm):
        """workers restart 重启 worker"""
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()):
            result = cli_runner.invoke(config_cli.app, ["workers", "restart"])
        assert result.exit_code == 0
        assert "restarted" in result.output.lower()

    def test_workers_unknown_action(self, cli_runner, mock_gtm):
        """workers 未知 action 显示错误"""
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()):
            result = cli_runner.invoke(config_cli.app, ["workers", "invalid_action"])
        assert result.exit_code == 0
        assert "Unknown" in result.output or "not found" in result.output.lower()

    def test_workers_handles_exception(self, cli_runner, mock_gtm):
        """workers 命令异常时优雅处理"""
        mock_gtm.get_workers_status.side_effect = Exception("worker error")
        with patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.data.containers.container", MagicMock()), \
             patch("ginkgo.client.config_cli.GLOG"):
            result = cli_runner.invoke(config_cli.app, ["workers", "status"])
        assert result.exit_code == 0
        assert "not available" in result.output.lower()


# ============================================================================
# 7. containers 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestConfigContainers:
    """config containers 命令测试"""

    def test_containers_status(self, cli_runner):
        """containers status 显示容器状态表"""
        result = cli_runner.invoke(config_cli.app, ["containers", "status"])
        assert result.exit_code == 0
        assert "Container" in result.output or "container" in result.output.lower()

    def test_containers_start(self, cli_runner):
        """containers start 启动容器"""
        result = cli_runner.invoke(config_cli.app, ["containers", "start"])
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_containers_start_with_count(self, cli_runner):
        """containers start --count N 启动指定数量容器"""
        result = cli_runner.invoke(config_cli.app, ["containers", "start", "--count", "3"])
        assert result.exit_code == 0
        assert "3" in result.output

    def test_containers_start_with_image(self, cli_runner):
        """containers start --image 使用指定镜像"""
        result = cli_runner.invoke(config_cli.app, ["containers", "start", "--image", "my/image:v1"])
        assert result.exit_code == 0
        assert "my/image:v1" in result.output

    def test_containers_stop(self, cli_runner):
        """containers stop 停止所有容器"""
        result = cli_runner.invoke(config_cli.app, ["containers", "stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

    def test_containers_restart(self, cli_runner):
        """containers restart 重启所有容器"""
        result = cli_runner.invoke(config_cli.app, ["containers", "restart"])
        assert result.exit_code == 0
        assert "restarted" in result.output.lower()

    def test_containers_scale_with_count(self, cli_runner):
        """containers scale --count N 扩容"""
        result = cli_runner.invoke(config_cli.app, ["containers", "scale", "--count", "8"])
        assert result.exit_code == 0
        assert "8" in result.output

    def test_containers_scale_without_count(self, cli_runner):
        """containers scale 不带 --count 显示错误"""
        result = cli_runner.invoke(config_cli.app, ["containers", "scale"])
        assert result.exit_code == 0
        assert "specify" in result.output or "--count" in result.output

    def test_containers_deploy(self, cli_runner):
        """containers deploy 部署"""
        result = cli_runner.invoke(config_cli.app, ["containers", "deploy"])
        assert result.exit_code == 0
        assert "Deployment" in result.output or "deploy" in result.output.lower()

    def test_containers_unknown_action(self, cli_runner):
        """containers 未知 action 显示错误"""
        result = cli_runner.invoke(config_cli.app, ["containers", "invalid"])
        assert result.exit_code == 0
        assert "Unknown" in result.output
