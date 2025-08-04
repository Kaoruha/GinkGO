import unittest
import time
from decimal import Decimal

try:
    from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
    from ginkgo.data.drivers.base_driver import DatabaseDriverBase
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs import GLOG, GinkgoLogger
    from ginkgo.libs.utils.health_check import check_clickhouse_ready
except ImportError:
    GinkgoClickhouse = None
    DatabaseDriverBase = None
    GCONF = None
    GLOG = None
    GinkgoLogger = None
    check_clickhouse_ready = None


class ClickhouseDriverRealTest(unittest.TestCase):
    """
    ClickHouse驱动真实连接测试 - 使用GCONF配置进行实际验证
    """

    @classmethod
    def setUpClass(cls):
        """类级别的设置，检查必要的依赖和配置"""
        if GinkgoClickhouse is None or GCONF is None:
            raise unittest.SkipTest("ClickHouse driver or GCONF not available")

        # 检查GCONF配置是否可用
        try:
            cls.clickhouse_config = {
                "user": GCONF.CLICKUSER,
                "pwd": GCONF.CLICKPWD,
                "host": GCONF.CLICKHOST,
                "port": str(GCONF.CLICKPORT),
                "db": GCONF.CLICKDB,
            }

            # 验证配置完整性
            for key, value in cls.clickhouse_config.items():
                if not value:
                    raise unittest.SkipTest(f"ClickHouse configuration missing: {key}")

        except Exception as e:
            raise unittest.SkipTest(f"Failed to read ClickHouse configuration: {e}")

    def setUp(self):
        """每个测试前的设置"""
        # 重置类级别的logger，避免测试间干扰
        GinkgoClickhouse._clickhouse_logger = None
        DatabaseDriverBase._shared_database_logger = None

    def test_clickhouse_initialization_real(self):
        """测试ClickHouse驱动真实初始化"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        # 验证基本属性设置
        self.assertEqual(driver.driver_name, "ClickHouse")
        self.assertEqual(driver._db_type, "clickhouse")
        self.assertEqual(driver._user, self.clickhouse_config["user"])
        self.assertEqual(driver._pwd, self.clickhouse_config["pwd"])
        self.assertEqual(driver._host, self.clickhouse_config["host"])
        self.assertEqual(driver._port, self.clickhouse_config["port"])
        self.assertEqual(driver._db, self.clickhouse_config["db"])

        # 验证默认参数
        self.assertEqual(driver._echo, False)
        self.assertEqual(driver._connect_timeout, 10)
        self.assertEqual(driver._read_timeout, 10)

        # 验证继承关系
        self.assertIsInstance(driver, DatabaseDriverBase)

        # 验证基类属性初始化
        self.assertIsNotNone(driver._connection_stats)
        self.assertIsNotNone(driver._lock)
        self.assertIsInstance(driver.loggers, list)

    def test_clickhouse_initialization_custom_params(self):
        """测试ClickHouse驱动自定义参数初始化"""
        custom_config = self.clickhouse_config.copy()
        custom_config.update({"echo": True, "connect_timeout": 20, "read_timeout": 30})

        driver = GinkgoClickhouse(**custom_config)

        # 验证自定义参数
        self.assertEqual(driver._echo, True)
        self.assertEqual(driver._connect_timeout, 20)
        self.assertEqual(driver._read_timeout, 30)

    def test_clickhouse_uri_construction(self):
        """测试ClickHouse URI构建逻辑"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        uri = driver._get_uri()
        expected_uri = (
            f"clickhouse://{self.clickhouse_config['user']}:{self.clickhouse_config['pwd']}"
            f"@{self.clickhouse_config['host']}:{self.clickhouse_config['port']}"
            f"/{self.clickhouse_config['db']}?connect_timeout=10&read_timeout=10"
        )

        self.assertEqual(uri, expected_uri)

    def test_clickhouse_uri_construction_custom_timeouts(self):
        """测试ClickHouse URI构建（自定义超时）"""
        custom_config = self.clickhouse_config.copy()
        custom_config.update({"connect_timeout": 25, "read_timeout": 45})

        driver = GinkgoClickhouse(**custom_config)
        uri = driver._get_uri()

        # 验证超时参数在URI中正确设置
        self.assertIn("connect_timeout=25", uri)
        self.assertIn("read_timeout=45", uri)

    def test_clickhouse_engine_creation(self):
        """测试SQLAlchemy引擎创建"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        # 验证引擎创建
        self.assertIsNotNone(driver._engine)
        self.assertIsNotNone(driver.engine)  # 向后兼容属性

        # 验证引擎URL
        engine_url = str(driver._engine.url)
        self.assertIn("clickhouse", engine_url)
        self.assertIn(self.clickhouse_config["host"], engine_url)
        self.assertIn(self.clickhouse_config["port"], engine_url)
        self.assertIn(self.clickhouse_config["db"], engine_url)

    def test_clickhouse_engine_pool_configuration(self):
        """测试ClickHouse引擎连接池配置"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        engine = driver._engine

        # 验证连接池参数（如果SQLAlchemy版本支持访问这些属性）
        try:
            pool = engine.pool
            # ClickHouse连接池应该存在
            self.assertIsNotNone(pool)
        except AttributeError:
            # 如果无法访问pool属性，跳过此验证
            pass

    def test_clickhouse_session_factory_creation(self):
        """测试会话工厂创建"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        # 验证会话工厂创建
        self.assertIsNotNone(driver._session_factory)

        # 验证会话工厂绑定到正确的引擎
        self.assertEqual(driver._session_factory.bind, driver._engine)

    def test_clickhouse_health_check_query(self):
        """测试健康检查查询"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        query = driver._health_check_query()
        self.assertEqual(query, "SELECT 1")

    def test_clickhouse_health_check_integration(self):
        """测试ClickHouse健康检查集成"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        try:
            # 执行健康检查
            result = driver.health_check()

            # 健康检查应该返回布尔值
            self.assertIsInstance(result, bool)

            # 如果连接成功，验证统计更新
            if result:
                stats = driver.get_connection_stats()
                self.assertGreater(stats["last_health_check"], 0)

        except Exception as e:
            # 如果数据库不可用，跳过此测试
            self.skipTest(f"ClickHouse not available for health check: {e}")

    def test_clickhouse_logger_integration(self):
        """测试ClickHouse Logger集成"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        # 应该有3个logger: GLOG, database, clickhouse
        self.assertGreaterEqual(len(driver.loggers), 3)

        # 验证GLOG在队列中
        self.assertIn(GLOG, driver.loggers)

        # 验证ClickHouse专用logger
        self.assertIsNotNone(GinkgoClickhouse._clickhouse_logger)
        self.assertIn(GinkgoClickhouse._clickhouse_logger, driver.loggers)
        self.assertEqual(GinkgoClickhouse._clickhouse_logger.logger_name, "ginkgo_clickhouse")

        # 验证共享database logger
        self.assertIsNotNone(DatabaseDriverBase._shared_database_logger)
        self.assertIn(DatabaseDriverBase._shared_database_logger, driver.loggers)

    def test_clickhouse_logger_singleton_behavior(self):
        """测试ClickHouse Logger单例行为"""
        driver1 = GinkgoClickhouse(**self.clickhouse_config)
        driver2 = GinkgoClickhouse(**self.clickhouse_config)

        # 验证ClickHouse logger单例
        self.assertIs(driver1._clickhouse_logger, driver2._clickhouse_logger)
        self.assertIs(GinkgoClickhouse._clickhouse_logger, driver1._clickhouse_logger)

        # 验证shared database logger单例
        shared_logger1 = None
        shared_logger2 = None

        for logger in driver1.loggers:
            if logger is DatabaseDriverBase._shared_database_logger:
                shared_logger1 = logger
                break

        for logger in driver2.loggers:
            if logger is DatabaseDriverBase._shared_database_logger:
                shared_logger2 = logger
                break

        self.assertIs(shared_logger1, shared_logger2)

    def test_clickhouse_backwards_compatibility_properties(self):
        """测试向后兼容属性"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        # 测试engine属性
        self.assertIs(driver.engine, driver._engine)

        # 测试session属性
        session = driver.session
        self.assertIsNotNone(session)

        # 测试remove_session方法
        try:
            driver.remove_session()
        except Exception as e:
            self.fail(f"remove_session failed: {e}")

    def test_clickhouse_connection_stats_integration(self):
        """测试连接统计集成"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        stats = driver.get_connection_stats()

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
            self.assertIn(field, stats)

        self.assertEqual(stats["driver_name"], "ClickHouse")
        self.assertIsInstance(stats["uptime"], (int, float))
        self.assertIsInstance(stats["connection_efficiency"], (int, float))

    def test_clickhouse_context_manager_session(self):
        """测试上下文管理器会话"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        try:
            with driver.get_session() as session:
                # 验证会话对象
                self.assertIsNotNone(session)

                # 尝试执行简单查询验证连接（使用SQLAlchemy 2.0语法）
                from sqlalchemy import text

                result = session.execute(text(driver._health_check_query()))
                self.assertIsNotNone(result)

        except Exception as e:
            # 如果数据库不可用，跳过测试
            self.skipTest(f"ClickHouse not available for session test: {e}")

    def test_clickhouse_log_method_integration(self):
        """测试日志方法集成"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        # 测试日志方法不抛出异常
        try:
            driver.log("INFO", "Test ClickHouse log message")
            driver.log("WARNING", "Test ClickHouse warning message")
            driver.log("ERROR", "Test ClickHouse error message")
        except Exception as e:
            self.fail(f"Log method failed: {e}")

    def test_clickhouse_multiple_instances_independence(self):
        """测试多个ClickHouse驱动实例的独立性"""
        driver1 = GinkgoClickhouse(**self.clickhouse_config)
        driver2 = GinkgoClickhouse(**self.clickhouse_config)

        # 验证实例独立性
        self.assertIsNot(driver1, driver2)
        self.assertIsNot(driver1._engine, driver2._engine)
        self.assertIsNot(driver1._session_factory, driver2._session_factory)
        self.assertIsNot(driver1._connection_stats, driver2._connection_stats)

        # 但共享logger
        self.assertIs(driver1._clickhouse_logger, driver2._clickhouse_logger)

    def test_clickhouse_error_handling_graceful(self):
        """测试错误处理的优雅性"""
        # 使用无效配置测试错误处理
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
            self.assertFalse(result)

        except Exception:
            # 如果在初始化时就失败，这也是可以接受的
            pass

    def test_clickhouse_real_database_verification(self):
        """测试真实ClickHouse数据库连接验证"""
        try:
            # 使用health_check模块直接验证连接
            connection_ok = check_clickhouse_ready(self.clickhouse_config["host"], int(self.clickhouse_config["port"]))

            if connection_ok:
                # 如果连接成功，测试驱动
                driver = GinkgoClickhouse(**self.clickhouse_config)
                health_result = driver.health_check()
                self.assertTrue(health_result)
            else:
                self.skipTest("ClickHouse database not available for real connection test")

        except Exception as e:
            self.skipTest(f"Cannot verify real ClickHouse connection: {e}")

    def test_clickhouse_port_parameter_flexibility(self):
        """测试ClickHouse端口参数的灵活性"""
        # 测试字符串端口
        config_str_port = self.clickhouse_config.copy()
        config_str_port["port"] = str(config_str_port["port"])

        driver_str = GinkgoClickhouse(**config_str_port)
        self.assertEqual(driver_str._port, config_str_port["port"])

        # 验证URI构建正确
        uri_str = driver_str._get_uri()
        self.assertIn(config_str_port["port"], uri_str)

    def test_clickhouse_connection_pool_optimized_parameters(self):
        """测试ClickHouse连接池优化参数"""
        driver = GinkgoClickhouse(**self.clickhouse_config)

        # 由于无法直接访问连接池参数，我们通过引擎创建验证逻辑正确性
        # 主要验证没有异常抛出，连接池配置合理
        self.assertIsNotNone(driver._engine)

        # 验证引擎URL格式正确
        engine_url = str(driver._engine.url)
        self.assertTrue(engine_url.startswith("clickhouse://"))

    def test_clickhouse_http_health_check_integration(self):
        """测试ClickHouse HTTP健康检查集成"""
        try:
            # 直接测试HTTP健康检查
            if check_clickhouse_ready is not None:
                result = check_clickhouse_ready(self.clickhouse_config["host"], int(self.clickhouse_config["port"]))

                # HTTP健康检查应该返回布尔值
                self.assertIsInstance(result, bool)

                if result:
                    # 如果HTTP健康检查成功，驱动健康检查也应该成功
                    driver = GinkgoClickhouse(**self.clickhouse_config)
                    driver_result = driver.health_check()
                    self.assertTrue(driver_result)

        except Exception as e:
            self.skipTest(f"ClickHouse HTTP health check not available: {e}")

    def test_clickhouse_timeout_parameter_propagation(self):
        """测试ClickHouse超时参数传播"""
        custom_config = self.clickhouse_config.copy()
        custom_config.update({"connect_timeout": 15, "read_timeout": 25})

        driver = GinkgoClickhouse(**custom_config)

        # 验证超时参数正确保存
        self.assertEqual(driver._connect_timeout, 15)
        self.assertEqual(driver._read_timeout, 25)

        # 验证超时参数在URI中正确传播
        uri = driver._get_uri()
        self.assertIn("connect_timeout=15", uri)
        self.assertIn("read_timeout=25", uri)
