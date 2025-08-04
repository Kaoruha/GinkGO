import unittest
import time
from decimal import Decimal

try:
    from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
    from ginkgo.data.drivers.base_driver import DatabaseDriverBase
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs import GLOG, GinkgoLogger
except ImportError:
    GinkgoMysql = None
    DatabaseDriverBase = None
    GCONF = None
    GLOG = None
    GinkgoLogger = None


class MysqlDriverRealTest(unittest.TestCase):
    """
    MySQL驱动真实连接测试 - 使用GCONF配置进行实际验证
    """

    @classmethod
    def setUpClass(cls):
        """类级别的设置，检查必要的依赖和配置"""
        if GinkgoMysql is None or GCONF is None:
            raise unittest.SkipTest("MySQL driver or GCONF not available")

        # 检查GCONF配置是否可用
        try:
            cls.mysql_config = {
                "user": GCONF.MYSQLUSER,
                "pwd": GCONF.MYSQLPWD,
                "host": GCONF.MYSQLHOST,
                "port": str(GCONF.MYSQLPORT),
                "db": GCONF.MYSQLDB,
            }

            # 验证配置完整性
            for key, value in cls.mysql_config.items():
                if not value:
                    raise unittest.SkipTest(f"MySQL configuration missing: {key}")

        except Exception as e:
            self.fail(f"Failed to read MySQL configuration: {e}")

    def setUp(self):
        """每个测试前的设置"""
        # 重置类级别的logger，避免测试间干扰
        GinkgoMysql._mysql_logger = None
        DatabaseDriverBase._shared_database_logger = None

    def test_mysql_initialization_real(self):
        """测试MySQL驱动真实初始化"""
        driver = GinkgoMysql(**self.mysql_config)

        # 验证基本属性设置
        self.assertEqual(driver.driver_name, "MySQL")
        self.assertEqual(driver._db_type, "mysql")
        self.assertEqual(driver._user, self.mysql_config["user"])
        self.assertEqual(driver._pwd, self.mysql_config["pwd"])
        self.assertEqual(driver._host, self.mysql_config["host"])
        self.assertEqual(driver._port, self.mysql_config["port"])
        self.assertEqual(driver._db, self.mysql_config["db"])

        # 验证默认参数
        self.assertEqual(driver._echo, False)
        self.assertEqual(driver._connect_timeout, 2)
        self.assertEqual(driver._read_timeout, 4)

        # 验证继承关系
        self.assertIsInstance(driver, DatabaseDriverBase)

        # 验证基类属性初始化
        self.assertIsNotNone(driver._connection_stats)
        self.assertIsNotNone(driver._lock)
        self.assertIsInstance(driver.loggers, list)

    def test_mysql_initialization_custom_params(self):
        """测试MySQL驱动自定义参数初始化"""
        custom_config = self.mysql_config.copy()
        custom_config.update({"echo": True, "connect_timeout": 10, "read_timeout": 20})

        driver = GinkgoMysql(**custom_config)

        # 验证自定义参数
        self.assertEqual(driver._echo, True)
        self.assertEqual(driver._connect_timeout, 10)
        self.assertEqual(driver._read_timeout, 20)

    def test_mysql_uri_construction(self):
        """测试MySQL URI构建逻辑"""
        driver = GinkgoMysql(**self.mysql_config)

        uri = driver._get_uri()
        expected_uri = (
            f"mysql+pymysql://{self.mysql_config['user']}:{self.mysql_config['pwd']}"
            f"@{self.mysql_config['host']}:{self.mysql_config['port']}"
            f"/{self.mysql_config['db']}?connect_timeout=2&read_timeout=4"
        )

        self.assertEqual(uri, expected_uri)

    def test_mysql_uri_construction_custom_timeouts(self):
        """测试MySQL URI构建（自定义超时）"""
        custom_config = self.mysql_config.copy()
        custom_config.update({"connect_timeout": 15, "read_timeout": 30})

        driver = GinkgoMysql(**custom_config)
        uri = driver._get_uri()

        # 验证超时参数在URI中正确设置
        self.assertIn("connect_timeout=15", uri)
        self.assertIn("read_timeout=30", uri)

    def test_mysql_engine_creation(self):
        """测试SQLAlchemy引擎创建"""
        driver = GinkgoMysql(**self.mysql_config)

        # 验证引擎创建
        self.assertIsNotNone(driver._engine)
        self.assertIsNotNone(driver.engine)  # 向后兼容属性

        # 验证引擎URL
        engine_url = str(driver._engine.url)
        self.assertIn("mysql+pymysql", engine_url)
        self.assertIn(self.mysql_config["host"], engine_url)
        self.assertIn(self.mysql_config["port"], engine_url)
        self.assertIn(self.mysql_config["db"], engine_url)

    def test_mysql_session_factory_creation(self):
        """测试会话工厂创建"""
        driver = GinkgoMysql(**self.mysql_config)

        # 验证会话工厂创建
        self.assertIsNotNone(driver._session_factory)

        # 验证会话工厂绑定到正确的引擎
        self.assertEqual(driver._session_factory.bind, driver._engine)

    def test_mysql_health_check_query(self):
        """测试健康检查查询"""
        driver = GinkgoMysql(**self.mysql_config)

        query = driver._health_check_query()
        self.assertEqual(query, "SELECT 1")

    def test_mysql_health_check_integration(self):
        """测试MySQL健康检查集成"""
        driver = GinkgoMysql(**self.mysql_config)

        # 执行健康检查
        result = driver.health_check()
        print(result)

        # 健康检查应该返回布尔值
        self.assertIsInstance(result, bool)

        stats = driver.get_connection_stats()
        print(stats)
        self.assertGreater(stats["last_health_check"], 0)

    def test_mysql_logger_integration(self):
        """测试MySQL Logger集成"""
        driver = GinkgoMysql(**self.mysql_config)

        # 应该有3个logger: GLOG, database, mysql
        self.assertGreaterEqual(len(driver.loggers), 3)

        # 验证GLOG在队列中
        self.assertIn(GLOG, driver.loggers)

        # 验证MySQL专用logger
        self.assertIsNotNone(GinkgoMysql._mysql_logger)
        self.assertIn(GinkgoMysql._mysql_logger, driver.loggers)
        self.assertEqual(GinkgoMysql._mysql_logger.logger_name, "ginkgo_mysql")

        # 验证共享database logger
        self.assertIsNotNone(DatabaseDriverBase._shared_database_logger)
        self.assertIn(DatabaseDriverBase._shared_database_logger, driver.loggers)

    def test_mysql_logger_singleton_behavior(self):
        """测试MySQL Logger单例行为"""
        driver1 = GinkgoMysql(**self.mysql_config)
        driver2 = GinkgoMysql(**self.mysql_config)

        # 验证MySQL logger单例
        self.assertIs(driver1._mysql_logger, driver2._mysql_logger)
        self.assertIs(GinkgoMysql._mysql_logger, driver1._mysql_logger)

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

    def test_mysql_backwards_compatibility_properties(self):
        """测试向后兼容属性"""
        driver = GinkgoMysql(**self.mysql_config)

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

    def test_mysql_connection_stats_integration(self):
        """测试连接统计集成"""
        driver = GinkgoMysql(**self.mysql_config)

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

        self.assertEqual(stats["driver_name"], "MySQL")
        self.assertIsInstance(stats["uptime"], (int, float))
        self.assertIsInstance(stats["connection_efficiency"], (int, float))

    def test_mysql_context_manager_session(self):
        """测试上下文管理器会话"""
        driver = GinkgoMysql(**self.mysql_config)

        with driver.get_session() as session:
            # 验证会话对象
            self.assertIsNotNone(session)

            # 尝试执行简单查询验证连接（使用SQLAlchemy 2.0语法）
            from sqlalchemy import text

            result = session.execute(text(driver._health_check_query()))
            self.assertIsNotNone(result)

    def test_mysql_log_method_integration(self):
        """测试日志方法集成"""
        driver = GinkgoMysql(**self.mysql_config)

        # 测试日志方法不抛出异常
        driver.log("INFO", "Test log message")
        driver.log("WARNING", "Test warning message")
        driver.log("ERROR", "Test error message")

    def test_mysql_multiple_instances_independence(self):
        """测试多个MySQL驱动实例的独立性"""
        driver1 = GinkgoMysql(**self.mysql_config)
        driver2 = GinkgoMysql(**self.mysql_config)

        # 验证实例独立性
        self.assertIsNot(driver1, driver2)
        self.assertIsNot(driver1._engine, driver2._engine)
        self.assertIsNot(driver1._session_factory, driver2._session_factory)
        self.assertIsNot(driver1._connection_stats, driver2._connection_stats)

        # 但共享logger
        self.assertIs(driver1._mysql_logger, driver2._mysql_logger)

    def test_mysql_engine_pool_configuration(self):
        """测试引擎连接池配置"""
        driver = GinkgoMysql(**self.mysql_config)

        engine = driver._engine

        # 验证连接池参数（如果SQLAlchemy版本支持访问这些属性）
        pool = engine.pool
        # 某些连接池参数可能可以验证
        self.assertIsNotNone(pool)

    def test_mysql_error_handling_graceful(self):
        """测试错误处理的优雅性"""
        # 使用无效配置测试错误处理
        invalid_config = {
            "user": "invalid_user",
            "pwd": "invalid_password",
            "host": "invalid_host",
            "port": "99999",
            "db": "invalid_db",
        }

        driver = GinkgoMysql(**invalid_config)

        # 健康检查应该失败但不抛出异常
        result = driver.health_check()
        self.assertFalse(result)

    def test_mysql_real_database_verification(self):
        """测试真实数据库连接验证"""
        driver = GinkgoMysql(**self.mysql_config)
        health_result = driver.health_check()
        self.assertTrue(health_result)
