"""
Pytest配置和共享fixtures for database tests.
"""

import pytest
import os
from typing import Dict, Any, Generator
from unittest.mock import Mock, MagicMock

try:
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs.core.logger import GLOG
    from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
    from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
    from ginkgo.data.drivers.base_driver import DatabaseDriverBase
except ImportError:
    GCONF = None
    GLOG = None
    GinkgoClickhouse = None
    GinkgoMysql = None
    DatabaseDriverBase = None


@pytest.fixture(scope="session")
def ginkgo_config():
    """Ginkgo配置fixture，确保调试模式开启."""
    if GCONF is None:
        pytest.skip("Ginkgo configuration not available")

    # 保存原始配置
    original_debug = GCONF.DEBUGMODE

    # 设置调试模式
    GCONF.set_debug(True)

    yield GCONF

    # 恢复原始配置
    GCONF.set_debug(original_debug)


@pytest.fixture(scope="session")
def clickhouse_config(ginkgo_config) -> Dict[str, Any]:
    """ClickHouse配置fixture."""
    if GCONF is None:
        pytest.skip("Ginkgo configuration not available")

    config = {
        "user": GCONF.CLICKUSER,
        "pwd": GCONF.CLICKPWD,
        "host": GCONF.CLICKHOST,
        "port": str(GCONF.CLICKPORT),
        "db": GCONF.CLICKDB,
    }

    # 验证配置完整性
    for key, value in config.items():
        if not value:
            pytest.skip(f"ClickHouse configuration missing: {key}")

    return config


@pytest.fixture(scope="session")
def mysql_config(ginkgo_config) -> Dict[str, Any]:
    """MySQL配置fixture."""
    if GCONF is None:
        pytest.skip("Ginkgo configuration not available")

    config = {
        "user": GCONF.MYSQLUSER,
        "pwd": GCONF.MYSQLPWD,
        "host": GCONF.MYSQLHOST,
        "port": str(GCONF.MYSQLPORT),
        "db": GCONF.MYSQLDB,
    }

    # 验证配置完整性
    for key, value in config.items():
        if not value:
            pytest.skip(f"MySQL configuration missing: {key}")

    return config


@pytest.fixture
def mock_clickhouse_driver() -> Mock:
    """Mock ClickHouse驱动实例."""
    mock_driver = Mock(spec=GinkgoClickhouse)
    mock_driver.driver_name = "ClickHouse"
    mock_driver._db_type = "clickhouse"
    mock_driver._engine = Mock()
    mock_driver._session_factory = Mock()
    mock_driver._connection_stats = {
        "driver_name": "ClickHouse",
        "connections_created": 0,
        "connections_closed": 0,
        "active_connections": 0,
        "uptime": 0,
        "connection_efficiency": 1.0,
        "created_at": 0,
        "last_health_check": 0,
        "health_check_failures": 0,
    }
    mock_driver.loggers = []

    return mock_driver


@pytest.fixture
def mock_mysql_driver() -> Mock:
    """Mock MySQL驱动实例."""
    mock_driver = Mock(spec=GinkgoMysql)
    mock_driver.driver_name = "MySQL"
    mock_driver._db_type = "mysql"
    mock_driver._engine = Mock()
    mock_driver._session_factory = Mock()
    mock_driver._connection_stats = {
        "driver_name": "MySQL",
        "connections_created": 0,
        "connections_closed": 0,
        "active_connections": 0,
        "uptime": 0,
        "connection_efficiency": 1.0,
        "created_at": 0,
        "last_health_check": 0,
        "health_check_failures": 0,
    }
    mock_driver.loggers = []

    return mock_driver


@pytest.fixture
def test_database_config() -> Dict[str, str]:
    """测试数据库配置."""
    return {
        "test_code": "TEST000001.SZ",
        "test_name": "测试股票",
        "test_market": "SZ",
        "test_industry": "测试行业",
    }


@pytest.fixture
def sample_bar_data() -> Dict[str, Any]:
    """示例K线数据."""
    return {
        "code": "000001.SZ",
        "timestamp": "2024-01-01 09:30:00",
        "open": 10.0,
        "high": 10.5,
        "low": 9.8,
        "close": 10.2,
        "volume": 1000000,
    }


@pytest.fixture
def sample_tick_data() -> Dict[str, Any]:
    """示例Tick数据."""
    return {
        "code": "000001.SZ",
        "timestamp": "2024-01-01 09:30:00.100",
        "price": 10.15,
        "volume": 1000,
        "direction": 1,  # 买入
    }


def pytest_configure(config):
    """Pytest配置钩子."""
    # 注册自定义标记
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "database: 数据库测试标记")
    config.addinivalue_line("markers", "slow: 慢速测试标记")
    config.addinivalue_line("markers", "clickhouse: ClickHouse特定测试")
    config.addinivalue_line("markers", "mysql: MySQL特定测试")
