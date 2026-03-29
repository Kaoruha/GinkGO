"""
CLI 单元测试共享 fixtures

提供 CliRunner、ServiceResult mock 工厂和断言辅助函数。
通过环境变量 GINKGO_SKIP_DEBUG_CHECK=1 豁免根 conftest 的 DEBUG 模式检查。
"""
import os

import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch


# 豁免根 conftest 的 DEBUG 检查
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cli_runner():
    """CliRunner 实例"""
    return CliRunner()


@pytest.fixture
def mock_gconf():
    """Mock GCONF 对象，预设常用属性"""
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


@pytest.fixture
def mock_gtm():
    """Mock GTM 对象"""
    m = MagicMock()
    m.get_workers_status.return_value = {}
    m.main_status = "running"
    m.watch_dog_status = "active"
    m.get_worker_count.return_value = 0
    return m


@pytest.fixture
def mock_glog():
    """Mock GLOG 对象"""
    return MagicMock()


@pytest.fixture
def success_result(data=None):
    """创建成功的 ServiceResult"""
    from ginkgo.data.services.base_service import ServiceResult
    return ServiceResult.success(data=data)


@pytest.fixture
def error_result(error="test error"):
    """创建失败的 ServiceResult"""
    from ginkgo.data.services.base_service import ServiceResult
    return ServiceResult.error(error=error)


# ============================================================================
# 断言辅助
# ============================================================================

def assert_success(result, contains=None):
    """断言命令执行成功"""
    assert result.exit_code == 0, f"Expected exit_code 0, got {result.exit_code}. Output: {result.output}"
    if contains:
        assert contains in result.output, f"Expected '{contains}' in output. Got: {result.output}"


def assert_failure(result, contains=None):
    """断言命令执行失败"""
    assert result.exit_code != 0, f"Expected non-zero exit_code, got 0. Output: {result.output}"
    if contains:
        assert contains in result.output, f"Expected '{contains}' in output. Got: {result.output}"


def assert_output_contains(result, text):
    """断言输出包含指定文本"""
    assert text in result.output, f"Expected '{text}' in output. Got:\n{result.output}"
