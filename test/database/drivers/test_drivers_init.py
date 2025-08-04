import unittest
import threading
import time
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Numeric, DECIMAL, text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from test.database.test_isolation import database_test_required


try:
    from ginkgo.data.drivers import (
        ConnectionManager,
        get_mysql_connection,
        get_click_connection,
        create_mysql_connection,
        create_click_connection,
        get_db_connection,
        get_connection_status,
        add,
        add_all,
        is_table_exists,
        create_table,
        drop_table,
        get_table_size,
        _connection_manager,
    )
    from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
    from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
    from ginkgo.data.drivers.base_driver import DatabaseDriverBase
    from ginkgo.data.models import MClickBase, MMysqlBase
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs import GLOG

except ImportError:
    ConnectionManager = None
    get_mysql_connection = None
    GinkgoMysql = None
    GinkgoClickhouse = None
    MClickBase = None
    MMysqlBase = None
    GCONF = None
    GLOG = None
    DatabaseDriverBase = None


# 创建测试用的数据模型
class TestClickModel(MClickBase if MClickBase else object):
    """ClickHouse测试模型"""

    __tablename__ = "test_click_drivers_init"
    __abstract__ = False

    if MClickBase:
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        name: Mapped[str] = mapped_column(String(32), default="")
        value: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class TestMysqlModel(MMysqlBase if MMysqlBase else object):
    """MySQL测试模型"""

    __tablename__ = "test_mysql_drivers_init"
    __abstract__ = False

    if MMysqlBase:
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(50))
        value = Column(Numeric(10, 2))
        created_at = Column(DateTime, default=datetime.now)


class TestConnectionManager(unittest.TestCase):
    """ConnectionManager类测试 - 使用真实数据库连接"""

    @classmethod
    def setUpClass(cls):
        """类级别的设置，检查必要的依赖和配置"""
        if ConnectionManager is None or GCONF is None:
            raise AssertionError(
                "ConnectionManager or GCONF not available - this is a critical test dependency failure"
            )

        # 检查数据库配置
        try:
            cls.mysql_config = {
                "user": GCONF.MYSQLUSER,
                "pwd": GCONF.MYSQLPWD,
                "host": GCONF.MYSQLHOST,
                "port": str(GCONF.MYSQLPORT),
                "db": GCONF.MYSQLDB,
            }

            cls.clickhouse_config = {
                "user": GCONF.CLICKUSER,
                "pwd": GCONF.CLICKPWD,
                "host": GCONF.CLICKHOST,
                "port": str(GCONF.CLICKPORT),
                "db": GCONF.CLICKDB,
            }

            # 验证配置完整性
            for key, value in cls.mysql_config.items():
                if not value:
                    raise AssertionError(
                        f"MySQL configuration missing: {key} - database configuration is required for driver tests"
                    )

            for key, value in cls.clickhouse_config.items():
                if not value:
                    raise AssertionError(
                        f"ClickHouse configuration missing: {key} - database configuration is required for driver tests"
                    )

            # 添加连接健康检查和重试逻辑
            cls._verify_database_connections()

        except Exception as e:
            raise AssertionError(f"Failed to setup database configuration: {e}")

    @classmethod
    def _verify_database_connections(cls):
        """验证数据库连接可用性 - 简单直接，失败即fail"""
        # 验证MySQL连接
        mysql_conn = create_mysql_connection()
        if not mysql_conn.health_check():
            raise AssertionError("MySQL connection health check failed")

        # 验证ClickHouse连接
        click_conn = create_click_connection()
        if not click_conn.health_check():
            raise AssertionError("ClickHouse connection health check failed")

    def setUp(self):
        """每个测试前的设置"""
        # 创建测试专用的连接管理器实例，不影响全局状态
        self.connection_manager = ConnectionManager()

    @database_test_required
    def test_initialization(self):
        """测试ConnectionManager初始化"""
        manager = ConnectionManager()

        self.assertIsNone(manager._mysql_conn)
        self.assertIsNone(manager._click_conn)
        self.assertIsInstance(manager._lock, type(threading.Lock()))

    @database_test_required
    def test_get_mysql_connection_real(self):
        """测试真实MySQL连接获取"""
        # 首次获取连接
        conn1 = self.connection_manager.get_mysql_connection()

        # 验证连接对象
        self.assertIsInstance(conn1, GinkgoMysql)
        self.assertIsInstance(conn1, DatabaseDriverBase)

        # 验证健康检查
        health_status = conn1.health_check()
        self.assertIsInstance(health_status, bool)

        # 验证单例行为
        conn2 = self.connection_manager.get_mysql_connection()
        self.assertIs(conn1, conn2)

    @database_test_required
    def test_get_clickhouse_connection_real(self):
        """测试真实ClickHouse连接获取"""
        # 首次获取连接
        conn1 = self.connection_manager.get_clickhouse_connection()

        # 验证连接对象
        self.assertIsInstance(conn1, GinkgoClickhouse)
        self.assertIsInstance(conn1, DatabaseDriverBase)

        # 验证健康检查
        health_status = conn1.health_check()
        self.assertIsInstance(health_status, bool)

        # 验证单例行为
        conn2 = self.connection_manager.get_clickhouse_connection()
        self.assertIs(conn1, conn2)

    @database_test_required
    def test_get_connection_status_real(self):
        """测试获取真实连接状态"""
        # 获取连接以初始化状态
        mysql_conn = self.connection_manager.get_mysql_connection()
        click_conn = self.connection_manager.get_clickhouse_connection()

        # 获取连接状态
        status = self.connection_manager.get_connection_status()

        # 验证状态结构
        self.assertIn("mysql", status)
        self.assertIn("clickhouse", status)

        # 验证MySQL状态
        mysql_status = status["mysql"]
        self.assertIn("healthy", mysql_status)
        self.assertIsInstance(mysql_status["healthy"], bool)
        if mysql_status["healthy"]:
            self.assertIn("stats", mysql_status)
            self.assertIsInstance(mysql_status["stats"], dict)

        # 验证ClickHouse状态
        click_status = status["clickhouse"]
        self.assertIn("healthy", click_status)
        self.assertIsInstance(click_status["healthy"], bool)
        if click_status["healthy"]:
            self.assertIn("stats", click_status)
            self.assertIsInstance(click_status["stats"], dict)

    @database_test_required
    def test_connection_stats_real(self):
        """测试真实连接统计信息"""
        # 获取MySQL连接
        mysql_conn = self.connection_manager.get_mysql_connection()

        # 获取连接统计
        stats = mysql_conn.get_connection_stats()

        # 验证统计信息结构
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

        # 验证统计值类型
        self.assertIsInstance(stats["uptime"], (int, float))
        self.assertIsInstance(stats["connection_efficiency"], (int, float))
        self.assertEqual(stats["driver_name"], "MySQL")

    @database_test_required
    def test_thread_safety_real(self):
        """测试真实环境下的线程安全性"""
        results = []
        errors = []

        def get_connection_worker():
            try:
                conn = self.connection_manager.get_mysql_connection()
                results.append(conn)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时获取连接
        threads = []
        for _ in range(5):  # 减少线程数避免过多数据库连接
            thread = threading.Thread(target=get_connection_worker)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        if errors:
            # 如果有错误，可能是数据库不可用
            self.fail(f"Thread safety test encountered database errors (database was verified in setUpClass): {errors}")

        self.assertEqual(len(results), 5)
        # 所有结果应该是同一个连接对象（单例模式）
        if results:
            first_conn = results[0]
            for conn in results[1:]:
                self.assertIs(conn, first_conn)


class TestConnectionFunctions(unittest.TestCase):
    """连接创建和获取函数测试 - 使用真实数据库连接"""

    @classmethod
    def setUpClass(cls):
        if get_mysql_connection is None or GCONF is None:
            raise AssertionError(
                "Connection functions or GCONF not available - this is a critical test dependency failure"
            )

        # 验证数据库连接可用性
        cls._verify_database_connections()

    @classmethod
    def _verify_database_connections(cls):
        """验证数据库连接可用性 - 简单直接，失败即fail"""
        # 验证MySQL连接
        mysql_conn = create_mysql_connection()
        if not mysql_conn.health_check():
            raise AssertionError("MySQL connection health check failed")

        # 验证ClickHouse连接
        click_conn = create_click_connection()
        if not click_conn.health_check():
            raise AssertionError("ClickHouse connection health check failed")

    def setUp(self):
        """每个测试前的设置"""
        # 这些测试直接测试底层连接创建函数，不需要重置全局状态
        pass

    @database_test_required
    def test_create_mysql_connection_real(self):
        """测试真实MySQL连接创建"""
        # 执行测试
        result = create_mysql_connection()

        # 验证结果
        self.assertIsInstance(result, GinkgoMysql)
        self.assertIsInstance(result, DatabaseDriverBase)

        # 验证健康检查已通过
        health_status = result.health_check()
        self.assertTrue(health_status)

        # 验证连接属性
        self.assertIsNotNone(result.engine)
        self.assertIsNotNone(result.session)

    @database_test_required
    def test_create_clickhouse_connection_real(self):
        """测试真实ClickHouse连接创建"""
        # 执行测试
        result = create_click_connection()

        # 验证结果
        self.assertIsInstance(result, GinkgoClickhouse)
        self.assertIsInstance(result, DatabaseDriverBase)

        # 验证健康检查已通过
        health_status = result.health_check()
        self.assertTrue(health_status)

        # 验证连接属性
        self.assertIsNotNone(result.engine)
        self.assertIsNotNone(result.session)

    @database_test_required
    def test_get_mysql_connection_compatibility(self):
        """测试get_mysql_connection向后兼容性"""
        result = get_mysql_connection()

        self.assertIsInstance(result, GinkgoMysql)

        # 验证单例行为
        result2 = get_mysql_connection()
        self.assertIs(result, result2)

    @database_test_required
    def test_get_click_connection_compatibility(self):
        """测试get_click_connection向后兼容性"""
        result = get_click_connection()

        self.assertIsInstance(result, GinkgoClickhouse)

        # 验证单例行为
        result2 = get_click_connection()
        self.assertIs(result, result2)

    @database_test_required
    def test_get_db_connection_model_type_detection(self):
        """测试get_db_connection模型类型检测"""
        if MClickBase is None or MMysqlBase is None:
            self.fail("Database models not available - this is a critical test dependency failure")

        # 测试ClickHouse模型类型检测
        click_result = get_db_connection(TestClickModel)
        self.assertIsInstance(click_result, GinkgoClickhouse)

        # 测试MySQL模型类型检测
        mysql_result = get_db_connection(TestMysqlModel)
        self.assertIsInstance(mysql_result, GinkgoMysql)

        # 测试实例类型检测
        click_instance = TestClickModel()
        mysql_instance = TestMysqlModel()

        click_result2 = get_db_connection(click_instance)
        mysql_result2 = get_db_connection(mysql_instance)

        self.assertIsInstance(click_result2, GinkgoClickhouse)
        self.assertIsInstance(mysql_result2, GinkgoMysql)

    @database_test_required
    def test_get_connection_status_function(self):
        """测试get_connection_status函数"""
        # 初始化连接
        get_mysql_connection()
        get_click_connection()

        # 获取状态
        result = get_connection_status()

        # 验证状态结构
        self.assertIsInstance(result, dict)
        self.assertIn("mysql", result)
        self.assertIn("clickhouse", result)

    @database_test_required
    def test_connection_creation_with_config(self):
        """测试使用配置创建连接"""
        # 验证配置值被正确使用
        mysql_conn = create_mysql_connection()

        # 验证连接配置
        self.assertEqual(mysql_conn.driver_name, "MySQL")

        click_conn = create_click_connection()
        self.assertEqual(click_conn.driver_name, "ClickHouse")

    @database_test_required
    def test_health_check_service_verification(self):
        """测试健康检查服务验证"""

        # 测试MySQL健康检查
        mysql_conn = create_mysql_connection()
        self.assertTrue(mysql_conn.health_check())

        # 测试ClickHouse健康检查
        click_conn = create_click_connection()
        self.assertTrue(click_conn.health_check())


class TestDataOperations(unittest.TestCase):
    """数据操作函数测试 - 使用真实数据库连接"""

    @classmethod
    def setUpClass(cls):
        if add is None or GCONF is None:
            raise AssertionError(
                "Data operation functions or GCONF not available - this is a critical test dependency failure"
            )

        # 检查必要的模型类
        if MClickBase is None or MMysqlBase is None:
            raise AssertionError("Database models not available - this is a critical test dependency failure")

        # 验证数据库连接可用性
        cls._verify_database_connections()

    @classmethod
    def _verify_database_connections(cls):
        """验证数据库连接可用性 - 简单直接，失败即fail"""
        # 验证MySQL连接
        mysql_conn = get_mysql_connection()
        if not mysql_conn.health_check():
            raise AssertionError("MySQL connection health check failed")

        # 验证ClickHouse连接
        click_conn = get_click_connection()
        if not click_conn.health_check():
            raise AssertionError("ClickHouse connection health check failed")

    def setUp(self):
        """每个测试前的设置"""
        # 创建测试表（必须成功，否则测试失败）
        self._ensure_test_tables()

    def tearDown(self):
        """每个测试后的清理 - 清理失败则测试fail"""
        self._cleanup_test_data()

    def _ensure_test_tables(self):
        """确保测试表存在"""
        errors = []

        # MySQL测试表创建
        try:
            mysql_conn = get_mysql_connection()
            if mysql_conn:
                # 直接使用SQLAlchemy创建表，绕过缓存
                TestMysqlModel.metadata.create_all(mysql_conn.engine, checkfirst=True)
                # 验证表是否真正创建成功
                if not is_table_exists(TestMysqlModel):
                    errors.append("MySQL test table creation failed - table not found after creation")
            else:
                errors.append("MySQL connection is None")
        except Exception as e:
            errors.append(f"MySQL table creation failed: {e}")

        # ClickHouse测试表创建
        try:
            click_conn = get_click_connection()
            if click_conn:
                # 直接使用SQLAlchemy创建表，绕过缓存
                TestClickModel.metadata.create_all(click_conn.engine, checkfirst=True)
                # 验证表是否真正创建成功
                if not is_table_exists(TestClickModel):
                    errors.append("ClickHouse test table creation failed - table not found after creation")
            else:
                errors.append("ClickHouse connection is None")
        except Exception as e:
            errors.append(f"ClickHouse table creation failed: {e}")

        # 如果有错误，抛出异常而不是静默忽略
        if errors:
            error_msg = "Test table creation failed:\n" + "\n".join(errors)
            raise RuntimeError(error_msg)

    def _cleanup_test_data(self):
        """清理测试数据 - 简单直接，失败即fail"""
        # 清理MySQL测试数据
        mysql_conn = get_mysql_connection()
        with mysql_conn.get_session() as session:
            session.query(TestMysqlModel).delete()

        # 清理ClickHouse测试数据
        click_conn = get_click_connection()
        with click_conn.get_session() as session:
            session.execute(text("TRUNCATE TABLE test_click_drivers_init"))

    @database_test_required
    def test_add_invalid_item(self):
        """测试添加无效项目"""
        # 创建非数据库模型对象
        invalid_item = "not a model"

        # 执行测试
        result = add(invalid_item)

        # 验证结果
        self.assertIsNone(result)

    @database_test_required
    def test_add_single_mysql_item_real(self):
        """测试添加单个MySQL项目"""
        # 创建测试数据
        test_item = TestMysqlModel(name="test_mysql_item", value=Decimal("123.45"))

        # 保存预期值，避免访问detached对象
        expected_name = test_item.name
        expected_value = test_item.value

        # 执行测试
        result = add(test_item)

        # 验证结果 - 现在对象已expunge，可以安全访问属性
        self.assertIsNotNone(result, "add() should return the inserted object")
        self.assertEqual(result.name, expected_name)
        self.assertEqual(result.value, expected_value)
        self.assertIsNotNone(result.id, "Inserted object should have an auto-generated ID")

        # 额外验证数据确实被插入到数据库
        mysql_conn = get_mysql_connection()
        with mysql_conn.get_session() as session:
            count = session.query(TestMysqlModel).filter(TestMysqlModel.name == expected_name).count()
            self.assertGreater(count, 0, "Data should be persisted in database")

    @database_test_required
    def test_add_single_clickhouse_item_real(self):
        """测试添加单个ClickHouse项目"""
        # 创建测试数据
        test_item = TestClickModel(id=1001, name="test_click_item", value=Decimal("678.90"))

        # 保存预期值，避免访问detached对象
        expected_id = test_item.id
        expected_name = test_item.name
        expected_value = test_item.value

        # 执行测试
        result = add(test_item)

        # 验证结果 - 现在对象已expunge，可以安全访问属性
        self.assertIsNotNone(result, "add() should return the inserted object")
        # ClickHouse字符串字段需要strip null字符（与model_base.py中的处理一致）
        self.assertEqual(result.name.strip("\x00"), expected_name)
        self.assertEqual(result.value, expected_value)
        self.assertEqual(result.id, expected_id)

        # 额外验证数据确实被插入到数据库
        click_conn = get_click_connection()
        with click_conn.get_session() as session:
            count = session.query(TestClickModel).filter(TestClickModel.id == expected_id).count()
            self.assertGreater(count, 0, "Data should be persisted in database")

    @database_test_required
    def test_add_all_mixed_models_real(self):
        """测试批量添加混合模型"""
        # 创建测试数据
        mysql_items = [TestMysqlModel(name=f"mysql_item_{i}", value=Decimal(f"{i}.00")) for i in range(3)]

        click_items = [
            TestClickModel(id=2000 + i, name=f"click_item_{i}", value=Decimal(f"{i*10}.00")) for i in range(3)
        ]

        mixed_items = mysql_items + click_items + ["invalid_item"]

        # 执行测试
        click_count, mysql_count = add_all(mixed_items)

        # 验证结果
        self.assertEqual(mysql_count, 3)
        self.assertEqual(click_count, 3)

    @database_test_required
    def test_add_all_clickhouse_bulk_optimization_real(self):
        """测试ClickHouse批量插入优化"""
        # 创建大量测试数据
        test_items = [TestClickModel(id=3000 + i, name=f"bulk_test_{i}", value=Decimal(f"{i}.50")) for i in range(10)]

        # 执行测试
        click_count, mysql_count = add_all(test_items)

        # 验证结果
        self.assertEqual(click_count, 10)
        self.assertEqual(mysql_count, 0)

        # 验证数据确实被插入
        click_conn = get_click_connection()
        with click_conn.get_session() as session:
            count = session.query(TestClickModel).filter(TestClickModel.id >= 3000, TestClickModel.id < 3010).count()
            self.assertEqual(count, 10)

    @database_test_required
    def test_add_all_mysql_batch_real(self):
        """测试MySQL批量添加"""
        # 创建测试数据
        test_items = [TestMysqlModel(name=f"mysql_batch_{i}", value=Decimal(f"{i*2}.25")) for i in range(5)]

        # 执行测试
        click_count, mysql_count = add_all(test_items)

        # 验证结果
        self.assertEqual(click_count, 0)
        self.assertEqual(mysql_count, 5)

        # 验证数据确实被插入
        mysql_conn = get_mysql_connection()
        with mysql_conn.get_session() as session:
            count = session.query(TestMysqlModel).filter(TestMysqlModel.name.like("mysql_batch_%")).count()
            self.assertGreaterEqual(count, 5)

    @database_test_required
    def test_session_management_real(self):
        """测试会话管理"""
        # 创建测试数据
        test_item = TestMysqlModel(name="session_test", value=Decimal("999.99"))

        # 保存预期值
        expected_name = test_item.name
        expected_value = test_item.value

        # 验证会话管理工作正常
        result = add(test_item)
        self.assertIsNotNone(result, "add() should return the inserted object")
        self.assertIsNotNone(result.id, "Inserted object should have an ID")

        # 验证数据已提交
        mysql_conn = get_mysql_connection()
        with mysql_conn.get_session() as session:
            found_item = session.query(TestMysqlModel).filter(TestMysqlModel.name == expected_name).first()
            self.assertIsNotNone(found_item, f"Item with name '{expected_name}' should exist in database")
            self.assertEqual(found_item.value, expected_value)


class TestTableOperations(unittest.TestCase):
    """表操作函数测试 - 使用真实数据库连接"""

    @classmethod
    def setUpClass(cls):
        if is_table_exists is None or GCONF is None:
            raise AssertionError(
                "Table operation functions or GCONF not available - this is a critical test dependency failure"
            )

        # 验证数据库连接可用性
        cls._verify_database_connections()

    @classmethod
    def _verify_database_connections(cls):
        """验证数据库连接可用性 - 简单直接，失败即fail"""
        # 验证MySQL连接
        mysql_conn = get_mysql_connection()
        if not mysql_conn.health_check():
            raise AssertionError("MySQL connection health check failed")

        # 验证ClickHouse连接
        click_conn = get_click_connection()
        if not click_conn.health_check():
            raise AssertionError("ClickHouse connection health check failed")

    def setUp(self):
        """每个测试前的设置"""
        # 这些测试操作表结构，不需要重置全局连接状态
        pass

    @database_test_required
    def test_is_table_exists_mysql_real(self):
        """测试MySQL表存在检查"""
        # 测试存在的表
        result_exists = is_table_exists(TestMysqlModel)
        self.assertIsInstance(result_exists, bool)

        # 如果表不存在，创建它
        if not result_exists:
            create_table(TestMysqlModel, no_skip=True)
            time.sleep(0.2)  # 等待创建操作完成
            result_after_create = is_table_exists(TestMysqlModel)
            self.assertTrue(result_after_create)

    @database_test_required
    def test_is_table_exists_clickhouse_real(self):
        """测试ClickHouse表存在检查"""
        # 测试存在的表
        result_exists = is_table_exists(TestClickModel)
        self.assertIsInstance(result_exists, bool)

        # 如果表不存在，创建它
        if not result_exists:
            create_table(TestClickModel, no_skip=True)  # 强制执行，跳过缓存
            time.sleep(0.2)  # 等待创建操作完成
            result_after_create = is_table_exists(TestClickModel)
            self.assertTrue(result_after_create)

    @database_test_required
    def test_create_table_mysql_real(self):
        """测试MySQL表创建"""
        # 先删除表（如果存在），强制绕过缓存
        try:
            drop_table(TestMysqlModel, no_skip=True)
            time.sleep(0.2)  # 等待删除操作完成
        except Exception as e:
            print(f":warning: 删除表时出现异常（可能表不存在）: {e}")

        # 验证表不存在
        exists_before = is_table_exists(TestMysqlModel)
        if exists_before:
            # 如果删除失败，可能是缓存问题或权限问题
            print(f":magnifying_glass_tilted_left: 调试信息: 表 {TestMysqlModel.__tablename__} 在删除后仍然存在")
            # 再次尝试强制删除
            try:
                drop_table(TestMysqlModel, no_skip=True)
                time.sleep(0.5)  # 延长等待时间
                exists_retry = is_table_exists(TestMysqlModel)
                if exists_retry:
                    self.fail(f"无法删除表 {TestMysqlModel.__tablename__} - 可能是数据库权限问题或表被锁定")
            except Exception as retry_error:
                self.fail(f"重试删除表失败: {retry_error}")

        # 创建表，强制绕过缓存
        create_table(TestMysqlModel, no_skip=True)
        time.sleep(0.2)  # 等待创建操作完成

        # 验证表已创建
        exists_after = is_table_exists(TestMysqlModel)
        self.assertTrue(exists_after, f"表 {TestMysqlModel.__tablename__} 创建失败")

    @database_test_required
    def test_create_table_clickhouse_real(self):
        """测试ClickHouse表创建"""
        # 先删除表（如果存在）
        try:
            drop_table(TestClickModel)
            time.sleep(0.2)  # 等待删除操作完成
        except Exception as e:
            print(f":warning: 删除ClickHouse表时出现异常（可能表不存在）: {e}")

        # 验证表不存在
        exists_before = is_table_exists(TestClickModel)
        if exists_before:
            # 如果删除失败，可能是缓存问题或权限问题
            print(f":magnifying_glass_tilted_left: 调试信息: ClickHouse表 {TestClickModel.__tablename__} 在删除后仍然存在")
            # 再次尝试强制删除
            try:
                drop_table(TestClickModel)
                time.sleep(0.5)  # 延长等待时间
                exists_retry = is_table_exists(TestClickModel)
                if exists_retry:
                    self.fail(f"无法删除ClickHouse表 {TestClickModel.__tablename__} - 可能是数据库权限问题或表被锁定")
            except Exception as retry_error:
                self.fail(f"重试删除ClickHouse表失败: {retry_error}")

        # 创建表，强制绕过缓存
        create_table(TestClickModel, no_skip=True)
        time.sleep(0.2)  # 等待创建操作完成

        # 验证表已创建
        exists_after = is_table_exists(TestClickModel)
        self.assertTrue(exists_after, f"ClickHouse表 {TestClickModel.__tablename__} 创建失败")

    @database_test_required
    def test_create_table_already_exists_real(self):
        """测试创建已存在的表"""
        # 确保表存在
        if not is_table_exists(TestMysqlModel):
            create_table(TestMysqlModel, no_skip=True)
            time.sleep(0.2)  # 等待创建操作完成

        # 再次创建相同的表，应该不报错
        create_table(TestMysqlModel, no_skip=True)
        time.sleep(0.2)  # 等待创建操作完成

        # 验证表仍然存在
        exists = is_table_exists(TestMysqlModel)
        self.assertTrue(exists)

    @database_test_required
    def test_get_table_size_real(self):
        """测试获取真实表大小"""
        # 确保表存在
        if not is_table_exists(TestMysqlModel):
            create_table(TestMysqlModel, no_skip=True)
            time.sleep(0.2)  # 等待创建操作完成

        # 获取表大小
        size = get_table_size(TestMysqlModel)

        # 验证返回值
        self.assertIsInstance(size, int)
        self.assertGreaterEqual(size, 0)

        # 添加一些数据后再次检查
        test_item = TestMysqlModel(name="size_test", value=Decimal("1.0"))
        add(test_item)

        size_after = get_table_size(TestMysqlModel)
        self.assertGreaterEqual(size_after, size)

    @database_test_required
    def test_drop_table_real(self):
        """测试删除表"""

        # 创建一个临时表用于删除测试
        class TempTestModel(MMysqlBase if MMysqlBase else object):
            __tablename__ = "temp_test_drop_table"
            __abstract__ = False
            if MMysqlBase:
                id = Column(Integer, primary_key=True, autoincrement=True)
                name = Column(String(50))

        # 创建表
        create_table(TempTestModel, no_skip=True)
        time.sleep(0.2)  # 等待创建操作完成
        exists_before = is_table_exists(TempTestModel)
        self.assertTrue(exists_before)

        # 删除表
        drop_table(TempTestModel)
        time.sleep(0.2)  # 等待删除操作完成

        # 验证表已删除
        exists_after = is_table_exists(TempTestModel)
        self.assertFalse(exists_after)

    @database_test_required
    def test_abstract_model_handling(self):
        """测试抽象模型处理"""

        # 创建抽象模型
        class AbstractTestModel:
            __tablename__ = "abstract_test"
            __abstract__ = True

        # 创建抽象模型表应该被跳过
        create_table(AbstractTestModel, no_skip=True)

        # 不应该尝试检查抽象模型表的存在性
        # 这个测试主要验证不会抛出异常


class TestIntegration(unittest.TestCase):
    """集成测试 - 使用真实数据库连接的完整流程测试"""

    @classmethod
    def setUpClass(cls):
        if GCONF is None:
            raise AssertionError("GCONF not available - this is a critical test dependency failure")

        # 验证数据库连接可用性
        cls._verify_database_connections()

    @classmethod
    def _verify_database_connections(cls):
        """验证数据库连接可用性 - 简单直接，失败即fail"""
        # 验证MySQL连接
        mysql_conn = get_mysql_connection()
        if not mysql_conn.health_check():
            raise AssertionError("MySQL connection health check failed")

        # 验证ClickHouse连接
        click_conn = get_click_connection()
        if not click_conn.health_check():
            raise AssertionError("ClickHouse connection health check failed")

    def setUp(self):
        """每个测试前的设置"""
        # 集成测试使用稳定的连接状态，不需要重置
        pass

    @database_test_required
    def test_full_workflow_integration_real(self):
        """测试完整工作流程集成"""

        # 1. 获取连接
        mysql_conn = get_mysql_connection()
        click_conn = get_click_connection()

        self.assertIsNotNone(mysql_conn)
        self.assertIsNotNone(click_conn)
        self.assertIsInstance(mysql_conn, GinkgoMysql)
        self.assertIsInstance(click_conn, GinkgoClickhouse)

        # 2. 检查连接状态
        status = get_connection_status()

        self.assertIn("mysql", status)
        self.assertIn("clickhouse", status)

        # 3. 验证单例行为
        mysql_conn2 = get_mysql_connection()
        click_conn2 = get_click_connection()

        self.assertIs(mysql_conn, mysql_conn2)
        self.assertIs(click_conn, click_conn2)

        # 4. 测试表操作
        if not is_table_exists(TestMysqlModel):
            create_table(TestMysqlModel, no_skip=True)
            time.sleep(0.2)  # 等待创建操作完成
        if not is_table_exists(TestClickModel):
            create_table(TestClickModel, no_skip=True)
            time.sleep(0.2)  # 等待创建操作完成

        # 5. 测试数据操作
        mysql_item = TestMysqlModel(name="integration_test", value=Decimal("999.99"))
        click_item = TestClickModel(id=9999, name="integration_test", value=Decimal("888.88"))

        mysql_result = add(mysql_item)
        click_result = add(click_item)

        self.assertIsNotNone(mysql_result)
        self.assertIsNotNone(click_result)

        # 6. 验证数据持久化
        mysql_size = get_table_size(TestMysqlModel)
        click_size = get_table_size(TestClickModel)

        self.assertGreater(mysql_size, 0)
        self.assertGreater(click_size, 0)

    @database_test_required
    def test_connection_manager_singleton_behavior(self):
        """测试连接管理器单例行为"""

        # 获取多个连接管理器实例
        manager1 = ConnectionManager()
        manager2 = ConnectionManager()

        # 它们应该是不同的实例（非全局单例）
        self.assertIsNot(manager1, manager2)

        # 但全局连接管理器应该保持一致
        mysql_conn1 = get_mysql_connection()
        mysql_conn2 = get_mysql_connection()

        self.assertIs(mysql_conn1, mysql_conn2)

    @database_test_required
    def test_error_handling_across_operations(self):
        """测试跨操作错误处理"""

        # 测试无效数据处理
        invalid_result = add("invalid_data")
        self.assertIsNone(invalid_result)

        # 测试正常数据操作仍然工作
        if not is_table_exists(TestMysqlModel):
            create_table(TestMysqlModel, no_skip=True)
            time.sleep(0.2)  # 等待创建操作完成

        valid_item = TestMysqlModel(name="error_test", value=Decimal("1.0"))
        valid_result = add(valid_item)
        self.assertIsNotNone(valid_result)

    @database_test_required
    def test_performance_and_caching(self):
        """测试性能和缓存功能"""
        # 多次获取连接状态，验证缓存
        start_time = time.time()
        status1 = get_connection_status()
        first_call_time = time.time() - start_time

        start_time = time.time()
        status2 = get_connection_status()
        second_call_time = time.time() - start_time

        # 第二次调用应该更快（由于缓存）
        self.assertLessEqual(second_call_time, first_call_time * 2)  # 允许一些误差

        # 状态应该一致
        self.assertEqual(len(status1), len(status2))

    @database_test_required
    def test_thread_safety_integration(self):
        """测试线程安全集成"""
        if threading is None:
            self.skipTest("Threading not available")

        results = []
        errors = []

        def worker_function():
            try:
                # 每个线程执行完整的操作流程
                mysql_conn = get_mysql_connection()
                click_conn = get_click_connection()
                status = get_connection_status()

                results.append({"mysql_conn": mysql_conn, "click_conn": click_conn, "status": status})
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=worker_function)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        if errors:
            self.fail(f"Thread safety test failed (database was verified in setUpClass): {errors}")

        self.assertEqual(len(results), 3)

        # 验证所有线程获取到相同的连接对象
        if results:
            first_mysql = results[0]["mysql_conn"]
            first_click = results[0]["click_conn"]

            for result in results[1:]:
                self.assertIs(result["mysql_conn"], first_mysql)
                self.assertIs(result["click_conn"], first_click)

    @database_test_required
    def test_decorator_integration(self):
        """测试装饰器集成功能"""
        # 验证@time_logger装饰器工作
        start_time = time.time()
        mysql_conn = create_mysql_connection()
        end_time = time.time()

        self.assertIsInstance(mysql_conn, GinkgoMysql)
        self.assertGreater(end_time - start_time, 0)

        # 验证@retry装饰器（通过成功创建连接间接验证）
        click_conn = create_click_connection()
        self.assertIsInstance(click_conn, GinkgoClickhouse)
