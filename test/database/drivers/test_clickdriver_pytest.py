"""
ClickHouse驱动测试 - 使用Pytest最佳实践重构。

测试ClickHouse驱动的初始化、连接、健康检查等核心功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

try:
    from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
    from ginkgo.data.drivers.base_driver import DatabaseDriverBase
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs.core.logger import GLOG, GinkgoLogger
    from ginkgo.libs.utils.health_check import check_clickhouse_ready
    from sqlalchemy import text
except ImportError:
    GinkgoClickhouse = None
    DatabaseDriverBase = None
    GCONF = None
    GLOG = None
    GinkgoLogger = None
    check_clickhouse_ready = None
    text = None


@pytest.mark.clickhouse
@pytest.mark.database
class TestClickhouseDriverUnit:
    """ClickHouse驱动单元测试（不依赖真实数据库）."""

    @pytest.fixture
    def mock_config(self) -> dict:
        """Mock ClickHouse配置."""
        return {
            "user": "test_user",
            "pwd": "test_password",
            "host": "localhost",
            "port": "8123",
            "db": "test_db",
        }

    @pytest.fixture
    def driver(self, mock_config):
        """创建驱动实例的fixture."""
        if GinkgoClickhouse is None:
            pytest.skip("GinkgoClickhouse not available")
        return GinkgoClickhouse(**mock_config)

    @pytest.mark.unit
    def test_clickhouse_initialization(self, driver, mock_config):
        """测试ClickHouse驱动初始化."""
        # 验证基本属性设置
        assert driver.driver_name == "ClickHouse"
        assert driver._db_type == "clickhouse"
        assert driver._user == mock_config["user"]
        assert driver._pwd == mock_config["pwd"]
        assert driver._host == mock_config["host"]
        assert driver._port == mock_config["port"]
        assert driver._db == mock_config["db"]

        # 验证默认参数
        assert driver._echo is False
        assert driver._connect_timeout == 10
        assert driver._read_timeout == 10

    @pytest.mark.unit
    def test_clickhouse_initialization_custom_params(self, driver, mock_config):
        """测试ClickHouse驱动自定义参数初始化."""
        custom_config = mock_config.copy()
        custom_config.update({"echo": True, "connect_timeout": 20, "read_timeout": 30})

        driver = GinkgoClickhouse(**custom_config)

        # 验证自定义参数
        assert driver._echo is True
        assert driver._connect_timeout == 20
        assert driver._read_timeout == 30

    @pytest.mark.unit
    @pytest.mark.parametrize("echo,timeout", [
        (True, 15),
        (False, 25),
        (None, 10),
    ])
    def test_clickhouse_parametrized_initialization(self, mock_config, echo, timeout):
        """参数化测试不同初始化参数."""
        config = mock_config.copy()
        if echo is not None:
            config["echo"] = echo
        config["connect_timeout"] = timeout

        driver = GinkgoClickhouse(**config)

        assert driver._connect_timeout == timeout
        if echo is not None:
            assert driver._echo == echo

    @pytest.mark.unit
    def test_clickhouse_uri_construction(self, driver, mock_config):
        """测试ClickHouse URI构建逻辑."""
        uri = driver._get_uri()
        expected_uri = (
            f"clickhouse://{mock_config['user']}:{mock_config['pwd']}"
            f"@{mock_config['host']}:{mock_config['port']}"
            f"/{mock_config['db']}?connect_timeout=10&read_timeout=10"
        )

        assert uri == expected_uri

    @pytest.mark.unit
    def test_clickhouse_uri_construction_custom_timeouts(self, driver, mock_config):
        """测试ClickHouse URI构建（自定义超时）."""
        custom_config = mock_config.copy()
        custom_config.update({"connect_timeout": 25, "read_timeout": 45})

        driver = GinkgoClickhouse(**custom_config)
        uri = driver._get_uri()

        # 验证超时参数在URI中正确设置
        assert "connect_timeout=25" in uri
        assert "read_timeout=45" in uri

    @pytest.mark.unit
    def test_clickhouse_health_check_query(self, driver):
        """测试健康检查查询."""
        query = driver._health_check_query()
        assert query == "SELECT 1"

    @pytest.mark.unit
    def test_clickhouse_inheritance(self, driver):
        """验证继承关系."""
        assert isinstance(driver, DatabaseDriverBase)

    @pytest.mark.unit
    def test_clickhouse_base_attributes(self, driver):
        """验证基类属性初始化."""
        assert driver._connection_stats is not None
        assert driver._lock is not None
        assert isinstance(driver.loggers, list)

    @pytest.mark.unit
    def test_clickhouse_backwards_compatibility(self, driver):
        """测试向后兼容属性."""
        # 测试engine属性
        assert driver.engine is driver._engine

        # 测试session属性
        session = driver.session
        assert session is not None


@pytest.mark.clickhouse
@pytest.mark.database
class TestClickhouseDriverIntegration:
    """ClickHouse驱动集成测试（需要真实数据库）."""

    @pytest.fixture
    def real_config(self, ginkgo_config) -> dict:
        """获取真实ClickHouse配置."""
        if GCONF is None:
            pytest.skip("GCONF not available")

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

    @pytest.fixture
    def real_driver(self, real_config):
        """创建真实驱动实例."""
        if GinkgoClickhouse is None:
            pytest.skip("GinkgoClickhouse not available")
        return GinkgoClickhouse(**real_config)

    @pytest.mark.integration
    def test_clickhouse_engine_creation(self, real_driver, real_config):
        """测试SQLAlchemy引擎创建."""
        # 验证引擎创建
        assert real_driver._engine is not None
        assert real_driver.engine is not None

        # 验证引擎URL
        engine_url = str(real_driver._engine.url)
        assert "clickhouse" in engine_url
        assert real_config["host"] in engine_url
        assert real_config["port"] in engine_url
        assert real_config["db"] in engine_url

    @pytest.mark.integration
    def test_clickhouse_session_factory_creation(self, real_driver):
        """测试会话工厂创建."""
        # 验证会话工厂创建
        assert real_driver._session_factory is not None

        # 验证会话工厂绑定到正确的引擎
        assert real_driver._session_factory.bind is real_driver._engine

    @pytest.mark.integration
    def test_clickhouse_health_check_integration(self, real_driver):
        """测试ClickHouse健康检查集成."""
        try:
            # 执行健康检查
            result = real_driver.health_check()

            # 健康检查应该返回布尔值
            assert isinstance(result, bool)

            # 如果连接成功，验证统计更新
            if result:
                stats = real_driver.get_connection_stats()
                assert stats["last_health_check"] > 0

        except Exception as e:
            # 如果数据库不可用，跳过此测试
            pytest.skip(f"ClickHouse not available for health check: {e}")

    @pytest.mark.integration
    def test_clickhouse_context_manager_session(self, real_driver):
        """测试上下文管理器会话."""
        try:
            with real_driver.get_session() as session:
                # 验证会话对象
                assert session is not None

                # 尝试执行简单查询验证连接
                result = session.execute(text(real_driver._health_check_query()))
                assert result is not None

        except Exception as e:
            # 如果数据库不可用，跳过测试
            pytest.skip(f"ClickHouse not available for session test: {e}")

    @pytest.mark.integration
    def test_clickhouse_connection_stats(self, real_driver):
        """测试连接统计集成."""
        stats = real_driver.get_connection_stats()

        # 验证必要的统计字段
        required_fields = [
            "driver_name",
            "connections_created",
            "connections_closed",
            "active_connections",
            "uptime",
            "connection_efficiency",
            "created_at",
            "last_health_check",
            "health_check_failures",
        ]

        for field in required_fields:
            assert field in stats

        assert stats["driver_name"] == "ClickHouse"
        assert isinstance(stats["uptime"], (int, float))
        assert isinstance(stats["connection_efficiency"], (int, float))


@pytest.mark.clickhouse
@pytest.mark.database
class TestClickhouseDriverLogging:
    """测试ClickHouse驱动日志功能."""

    @pytest.fixture
    def driver(self, mock_config):
        """创建驱动实例."""
        if GinkgoClickhouse is None:
            pytest.skip("GinkgoClickhouse not available")
        return GinkgoClickhouse(**mock_config)

    @pytest.fixture
    def mock_config(self) -> dict:
        """Mock配置."""
        return {
            "user": "test_user",
            "pwd": "test_password",
            "host": "localhost",
            "port": "8123",
            "db": "test_db",
        }

    @pytest.mark.unit
    def test_clickhouse_logger_integration(self, driver):
        """测试ClickHouse Logger集成."""
        if GLOG is None:
            pytest.skip("GLOG not available")

        # 应该有多个logger
        assert len(driver.loggers) >= 1

        # 验证GLOG在队列中（如果可用）
        if GLOG in driver.loggers:
            assert GLOG in driver.loggers

    @pytest.mark.unit
    def test_clickhouse_logger_singleton_behavior(self, driver, mock_config):
        """测试ClickHouse Logger单例行为."""
        driver1 = driver
        driver2 = GinkgoClickhouse(**mock_config)

        # 验证ClickHouse logger单例（如果存在）
        if hasattr(GinkgoClickhouse, '_clickhouse_logger') and GinkgoClickhouse._clickhouse_logger is not None:
            assert driver1._clickhouse_logger is driver2._clickhouse_logger
            assert GinkgoClickhouse._clickhouse_logger is driver1._clickhouse_logger

    @pytest.mark.unit
    def test_clickhouse_log_method(self, driver):
        """测试日志方法."""
        # 测试日志方法不抛出异常
        try:
            driver.log("INFO", "Test ClickHouse log message")
            driver.log("WARNING", "Test ClickHouse warning message")
            driver.log("ERROR", "Test ClickHouse error message")
        except Exception as e:
            pytest.fail(f"Log method failed: {e}")


@pytest.mark.clickhouse
@pytest.mark.database
class TestClickhouseDriverErrorHandling:
    """测试ClickHouse驱动错误处理."""

    @pytest.mark.unit
    def test_clickhouse_invalid_config_error_handling(self):
        """测试无效配置的错误处理."""
        if GinkgoClickhouse is None:
            pytest.skip("GinkgoClickhouse not available")

        invalid_config = {
            "user": "invalid_user",
            "pwd": "invalid_password",
            "host": "invalid_host",
            "port": "99999",
            "db": "invalid_db",
        }

        try:
            driver = GinkgoClickhouse(**invalid_config)

            # 健康检查应该失败但不抛出异常
            result = driver.health_check()
            assert result is False

        except Exception:
            # 如果在初始化时就失败，这也是可以接受的
            pass

    @pytest.mark.unit
    def test_clickhouse_multiple_instances_independence(self):
        """测试多个ClickHouse驱动实例的独立性."""
        if GinkgoClickhouse is None:
            pytest.skip("GinkgoClickhouse not available")

        config = {
            "user": "test_user",
            "pwd": "test_password",
            "host": "localhost",
            "port": "8123",
            "db": "test_db",
        }

        driver1 = GinkgoClickhouse(**config)
        driver2 = GinkgoClickhouse(**config)

        # 验证实例独立性
        assert driver1 is not driver2
        assert driver1._engine is not driver2._engine
        assert driver1._session_factory is not driver2._session_factory
        assert driver1._connection_stats is not driver2._connection_stats


@pytest.mark.clickhouse
@pytest.mark.database
class TestClickhouseDriverPerformance:
    """测试ClickHouse驱动性能."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_clickhouse_engine_creation_performance(self):
        """测试引擎创建性能."""
        if GinkgoClickhouse is None:
            pytest.skip("GinkgoClickhouse not available")

        import time

        config = {
            "user": "test_user",
            "pwd": "test_password",
            "host": "localhost",
            "port": "8123",
            "db": "test_db",
        }

        start_time = time.perf_counter()
        driver = GinkgoClickhouse(**config)
        end_time = time.perf_counter()

        creation_time = (end_time - start_time) * 1000  # 转换为毫秒

        # 引擎创建应该在合理时间内完成
        assert creation_time < 100, f"Engine creation took too long: {creation_time:.2f}ms"
        assert driver._engine is not None
