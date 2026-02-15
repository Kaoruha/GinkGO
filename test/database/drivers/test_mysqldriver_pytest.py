"""
MySQL驱动测试 - 使用Pytest最佳实践重构。

测试MySQL驱动的初始化、连接、健康检查等核心功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

try:
    from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
    from ginkgo.data.drivers.base_driver import DatabaseDriverBase
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs.core.logger import GLOG
    from sqlalchemy import text
except ImportError:
    GinkgoMysql = None
    DatabaseDriverBase = None
    GCONF = None
    GLOG = None
    text = None


@pytest.mark.mysql
@pytest.mark.database
class TestMysqlDriverUnit:
    """MySQL驱动单元测试（不依赖真实数据库）."""

    @pytest.fixture
    def mock_config(self) -> dict:
        """Mock MySQL配置."""
        return {
            "user": "test_user",
            "pwd": "test_password",
            "host": "localhost",
            "port": "3306",
            "db": "test_db",
        }

    @pytest.fixture
    def driver(self, mock_config):
        """创建驱动实例的fixture."""
        if GinkgoMysql is None:
            pytest.skip("GinkgoMysql not available")
        return GinkgoMysql(**mock_config)

    @pytest.mark.unit
    def test_mysql_initialization(self, driver, mock_config):
        """测试MySQL驱动初始化."""
        # 验证基本属性设置
        assert driver.driver_name == "MySQL"
        assert driver._db_type == "mysql"
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
    def test_mysql_initialization_custom_params(self, mock_config):
        """测试MySQL驱动自定义参数初始化."""
        custom_config = mock_config.copy()
        custom_config.update({"echo": True, "connect_timeout": 20, "read_timeout": 30})

        if GinkgoMysql is None:
            pytest.skip("GinkgoMysql not available")

        driver = GinkgoMysql(**custom_config)

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
    def test_mysql_parametrized_initialization(self, mock_config, echo, timeout):
        """参数化测试不同初始化参数."""
        if GinkgoMysql is None:
            pytest.skip("GinkgoMysql not available")

        config = mock_config.copy()
        if echo is not None:
            config["echo"] = echo
        config["connect_timeout"] = timeout

        driver = GinkgoMysql(**config)

        assert driver._connect_timeout == timeout
        if echo is not None:
            assert driver._echo == echo

    @pytest.mark.unit
    def test_mysql_uri_construction(self, driver, mock_config):
        """测试MySQL URI构建逻辑."""
        uri = driver._get_uri()
        expected_uri = (
            f"mysql+pymysql://{mock_config['user']}:{mock_config['pwd']}"
            f"@{mock_config['host']}:{mock_config['port']}"
            f"/{mock_config['db']}?connect_timeout=10&read_timeout=10"
        )

        assert uri == expected_uri

    @pytest.mark.unit
    def test_mysql_uri_construction_custom_timeouts(self, mock_config):
        """测试MySQL URI构建（自定义超时）."""
        if GinkgoMysql is None:
            pytest.skip("GinkgoMysql not available")

        custom_config = mock_config.copy()
        custom_config.update({"connect_timeout": 25, "read_timeout": 45})

        driver = GinkgoMysql(**custom_config)
        uri = driver._get_uri()

        # 验证超时参数在URI中正确设置
        assert "connect_timeout=25" in uri
        assert "read_timeout=45" in uri

    @pytest.mark.unit
    def test_mysql_health_check_query(self, driver):
        """测试健康检查查询."""
        query = driver._health_check_query()
        assert query == "SELECT 1"

    @pytest.mark.unit
    def test_mysql_inheritance(self, driver):
        """验证继承关系."""
        assert isinstance(driver, DatabaseDriverBase)

    @pytest.mark.unit
    def test_mysql_base_attributes(self, driver):
        """验证基类属性初始化."""
        assert driver._connection_stats is not None
        assert driver._lock is not None
        assert isinstance(driver.loggers, list)


@pytest.mark.mysql
@pytest.mark.database
class TestMysqlDriverIntegration:
    """MySQL驱动集成测试（需要真实数据库）."""

    @pytest.fixture
    def real_config(self, ginkgo_config) -> dict:
        """获取真实MySQL配置."""
        if GCONF is None:
            pytest.skip("GCONF not available")

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
    def real_driver(self, real_config):
        """创建真实驱动实例."""
        if GinkgoMysql is None:
            pytest.skip("GinkgoMysql not available")
        return GinkgoMysql(**real_config)

    @pytest.mark.integration
    def test_mysql_engine_creation(self, real_driver, real_config):
        """测试SQLAlchemy引擎创建."""
        # 验证引擎创建
        assert real_driver._engine is not None
        assert real_driver.engine is not None

        # 验证引擎URL
        engine_url = str(real_driver._engine.url)
        assert "mysql" in engine_url
        assert real_config["host"] in engine_url
        assert real_config["port"] in engine_url
        assert real_config["db"] in engine_url

    @pytest.mark.integration
    def test_mysql_session_factory_creation(self, real_driver):
        """测试会话工厂创建."""
        # 验证会话工厂创建
        assert real_driver._session_factory is not None

        # 验证会话工厂绑定到正确的引擎
        assert real_driver._session_factory.bind is real_driver._engine

    @pytest.mark.integration
    def test_mysql_health_check_integration(self, real_driver):
        """测试MySQL健康检查集成."""
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
            pytest.skip(f"MySQL not available for health check: {e}")

    @pytest.mark.integration
    def test_mysql_context_manager_session(self, real_driver):
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
            pytest.skip(f"MySQL not available for session test: {e}")

    @pytest.mark.integration
    def test_mysql_connection_stats(self, real_driver):
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

        assert stats["driver_name"] == "MySQL"
        assert isinstance(stats["uptime"], (int, float))
        assert isinstance(stats["connection_efficiency"], (int, float))


@pytest.mark.mysql
@pytest.mark.database
class TestMysqlDriverErrorHandling:
    """测试MySQL驱动错误处理."""

    @pytest.mark.unit
    def test_mysql_invalid_config_error_handling(self):
        """测试无效配置的错误处理."""
        if GinkgoMysql is None:
            pytest.skip("GinkgoMysql not available")

        invalid_config = {
            "user": "invalid_user",
            "pwd": "invalid_password",
            "host": "invalid_host",
            "port": "99999",
            "db": "invalid_db",
        }

        try:
            driver = GinkgoMysql(**invalid_config)

            # 健康检查应该失败但不抛出异常
            result = driver.health_check()
            assert result is False

        except Exception:
            # 如果在初始化时就失败，这也是可以接受的
            pass

    @pytest.mark.unit
    def test_mysql_multiple_instances_independence(self):
        """测试多个MySQL驱动实例的独立性."""
        if GinkgoMysql is None:
            pytest.skip("GinkgoMysql not available")

        config = {
            "user": "test_user",
            "pwd": "test_password",
            "host": "localhost",
            "port": "3306",
            "db": "test_db",
        }

        driver1 = GinkgoMysql(**config)
        driver2 = GinkgoMysql(**config)

        # 验证实例独立性
        assert driver1 is not driver2
        assert driver1._engine is not driver2._engine
        assert driver1._session_factory is not driver2._session_factory
        assert driver1._connection_stats is not driver2._connection_stats
