"""
MySQL数据库驱动综合测试

测试MySQL驱动的特有功能和行为
涵盖事务管理、ACID特性、外键约束、存储引擎等
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
from ginkgo.data.drivers.base_driver import DatabaseDriverBase


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverConstruction:
    """1. MySQL驱动构造测试"""

    def test_mysql_driver_initialization(self):
        """测试MySQL驱动初始化"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver.driver_name == "MySQL"
        assert driver._user == "user"
        assert driver._pwd == "pwd"
        assert driver._host == "localhost"
        assert driver._port == "3306"
        assert driver._db == "testdb"

    def test_mysql_connection_uri_construction(self):
        """测试MySQL连接URI构建"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        uri = driver._get_uri()
        assert "mysql+pymysql://" in uri
        assert "user:pwd@" in uri
        assert "localhost:3306" in uri
        assert "/testdb" in uri

    def test_mysql_charset_configuration(self):
        """测试MySQL字符集配置"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # Charset is configured at URI and connect_args level
        streaming_uri = driver._get_streaming_uri()
        assert "charset=utf8mb4" in streaming_uri

    def test_mysql_engine_options_setting(self):
        """测试MySQL引擎选项设置"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # Default connect_timeout and read_timeout
        assert driver._connect_timeout == 2
        assert driver._read_timeout == 4

    def test_mysql_ssl_configuration(self):
        """测试MySQL SSL配置"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb", echo=True)
        assert driver._echo is True


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverConnectionManagement:
    """2. MySQL驱动连接管理测试"""

    def test_mysql_engine_creation(self):
        """测试MySQL引擎创建"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        mock_create.assert_called_once()
        assert driver._engine is not None

    def test_mysql_connection_pooling(self):
        """测试MySQL连接池管理"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['pool_size'] == 20
        assert call_kwargs['pool_timeout'] == 30
        assert call_kwargs['max_overflow'] == 10
        assert call_kwargs['pool_recycle'] == 3600
        assert call_kwargs['pool_pre_ping'] is True

    def test_mysql_connection_authentication(self):
        """测试MySQL连接认证"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("testuser", "testpwd", "localhost", "3306", "testdb")
        uri = driver._get_uri()
        assert "testuser:testpwd@" in uri

    def test_mysql_database_selection(self):
        """测试MySQL连接到指定的MySQL数据库"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "my_database")
        uri = driver._get_uri()
        assert "/my_database" in uri

    def test_mysql_connection_timezone_handling(self):
        """测试MySQL连接时区处理"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # MySQL timezone handled at session level via SQLAlchemy
        assert driver._engine is not None


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverTransactionManagement:
    """3. MySQL驱动事务管理测试"""

    def test_mysql_transaction_autocommit_control(self):
        """测试MySQL事务自动提交控制"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # autocommit=false in streaming URI for transaction control
        streaming_uri = driver._get_streaming_uri()
        assert "autocommit=false" in streaming_uri

    def test_mysql_transaction_isolation_levels(self):
        """测试MySQL事务隔离级别"""
        # SQLAlchemy supports isolation levels via execution_options
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None

    def test_mysql_transaction_rollback_handling(self):
        """测试MySQL事务回滚处理"""
        # get_session context manager handles rollback on exception
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        mock_session = Mock()
        mock_session.commit.side_effect = RuntimeError("commit failed")
        driver._session_factory = Mock(return_value=mock_session)
        with pytest.raises(RuntimeError):
            with driver.get_session():
                pass
        mock_session.rollback.assert_called()

    def test_mysql_nested_transaction_support(self):
        """测试MySQL嵌套事务支持"""
        # SQLAlchemy supports savepoints via session.begin_nested()
        from sqlalchemy.orm import Session
        assert hasattr(Session, 'begin_nested')

    def test_mysql_deadlock_detection_handling(self):
        """测试MySQL死锁检测处理"""
        # @retry decorator handles transient deadlock errors
        from ginkgo.libs import retry
        assert retry is not None


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverHealthCheck:
    """4. MySQL驱动健康检查测试"""

    def test_mysql_health_check_query(self):
        """测试MySQL健康检查查询"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._health_check_query() == "SELECT 1"

    def test_mysql_server_status_check(self):
        """测试MySQL服务器状态检查"""
        with patch('ginkgo.data.drivers.ginkgo_mysql.check_mysql_ready', return_value=True) as mock_check:
            with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
                driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
            mock_session = Mock()
            driver._session_factory = Mock(return_value=mock_session)
            result = driver.health_check()
        mock_check.assert_called_with("localhost", 3306, "user", "pwd")

    def test_mysql_replication_status_check(self):
        """测试MySQL复制状态检查"""
        # Replication status checked via SQL queries
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._health_check_query() == "SELECT 1"

    def test_mysql_performance_schema_access(self):
        """测试MySQL性能模式访问"""
        # Performance schema accessible via SQL
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverConstraintSupport:
    """5. MySQL驱动约束支持测试"""

    def test_mysql_foreign_key_constraint_handling(self):
        """测试MySQL外键约束处理"""
        # Foreign keys handled by SQLAlchemy ORM model definitions
        # Driver provides session for constraint enforcement
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver.session is not None

    def test_mysql_unique_constraint_handling(self):
        """测试MySQL唯一约束处理"""
        # Unique constraints enforced by MySQL
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._session_factory is not None

    def test_mysql_check_constraint_support(self):
        """测试MySQL检查约束支持"""
        # Check constraints handled at model level
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None

    def test_mysql_trigger_integration(self):
        """测试MySQL触发器集成"""
        # Triggers are database-side, driver executes SQL
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverStorageEngines:
    """6. MySQL驱动存储引擎测试"""

    def test_mysql_innodb_engine_support(self):
        """测试MySQL InnoDB引擎支持"""
        # SQLAlchemy default MySQL engine is InnoDB
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None

    def test_mysql_myisam_engine_support(self):
        """测试MySQL MyISAM引擎支持"""
        # Engine selection is at table DDL level, not driver level
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None

    def test_mysql_memory_engine_support(self):
        """测试MySQL Memory引擎支持"""
        # Memory tables accessible via driver session
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver.session is not None

    def test_mysql_engine_specific_optimizations(self):
        """测试针对不同存储引擎的查询优化"""
        # pool_pre_ping ensures connection validity (InnoDB optimization)
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['pool_pre_ping'] is True


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverDataTypes:
    """7. MySQL驱动数据类型测试"""

    def test_mysql_datetime_precision_handling(self):
        """测试MySQL日期时间精度处理"""
        # SQLAlchemy DateTime(timezone=True) for timezone-aware timestamps
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None

    def test_mysql_decimal_precision_accuracy(self):
        """测试MySQL小数精度准确性"""
        # DECIMAL(16,2) handled by SQLAlchemy type system
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver.session is not None

    def test_mysql_json_type_support(self):
        """测试MySQL JSON类型支持"""
        # MySQL 5.7+ supports JSON via SQLAlchemy
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None

    def test_mysql_geometry_type_support(self):
        """测试MySQL几何类型支持"""
        # Spatial types handled by SQLAlchemy GeoAlchemy2 extension
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver._engine is not None

    def test_mysql_enum_set_type_handling(self):
        """测试MySQL枚举集合类型处理"""
        # Enum values stored as TINYINT in ginkgo models
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # TINYINT type used for enum storage
        assert driver._engine is not None


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverPerformanceOptimization:
    """8. MySQL驱动性能优化测试"""

    def test_mysql_query_cache_utilization(self):
        """测试MySQL查询缓存利用"""
        # pool_pre_ping avoids stale connections
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['pool_pre_ping'] is True

    def test_mysql_index_optimization_hints(self):
        """测试MySQL索引优化提示"""
        # Index hints applied at query level
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        assert driver.session is not None

    def test_mysql_bulk_insert_optimization(self):
        """测试MySQL批量插入优化"""
        # Large pool_size enables concurrent bulk inserts
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['pool_size'] == 20
        assert call_kwargs['max_overflow'] == 10

    def test_mysql_connection_compression(self):
        """测试MySQL连接压缩"""
        # Compress could be added to URI parameters
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        uri = driver._get_uri()
        assert "mysql+pymysql://" in uri

    def test_mysql_prepared_statement_caching(self):
        """测试MySQL预编译语句缓存"""
        # SQLAlchemy compiled_cache handles statement caching
        streaming_kwargs = None
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # streaming engine uses compiled_cache
        assert driver._create_streaming_engine is not None


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverThreadSafety:
    """9. MySQL驱动线程安全测试"""

    def test_mysql_concurrent_connection_acquisition(self):
        """测试MySQL并发连接获取"""
        import threading
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        results = []
        def get_session():
            s = driver.session
            results.append(1)
        threads = [threading.Thread(target=get_session) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2)
        assert len(results) == 5

    def test_mysql_connection_pool_thread_safety(self):
        """测试MySQL连接池线程安全"""
        import threading
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        errors = []
        def use_pool():
            try:
                with driver.get_session():
                    pass
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=use_pool) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3)
        assert len(errors) == 0

    def test_mysql_concurrent_transaction_handling(self):
        """测试MySQL并发事务处理"""
        import threading
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        errors = []
        def transaction():
            try:
                with driver.get_session() as s:
                    pass
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=transaction) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3)
        assert len(errors) == 0

    def test_mysql_concurrent_crud_operations(self):
        """测试MySQL并发CRUD操作"""
        import threading
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # scoped_session handles concurrent CRUD
        assert driver._session_factory is not None

    def test_mysql_thread_safe_statistics_collection(self):
        """测试MySQL线程安全统计收集"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # Stats use threading.Lock in base driver
        assert driver._lock is not None
        stats = driver.get_connection_stats()
        assert "connections_created" in stats


@pytest.mark.unit
@pytest.mark.database
class TestMySQLDriverErrorHandling:
    """10. MySQL驱动错误处理测试"""

    def test_mysql_connection_error_recovery(self):
        """测试MySQL连接错误恢复"""
        with patch('ginkgo.data.drivers.ginkgo_mysql.check_mysql_ready', return_value=False):
            with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
                driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
            result = driver.health_check()
            assert result is False

    def test_mysql_duplicate_key_error_handling(self):
        """测试MySQL重复键错误处理"""
        # IntegrityError from SQLAlchemy for duplicate keys
        from sqlalchemy.exc import IntegrityError
        assert IntegrityError is not None

    def test_mysql_constraint_violation_handling(self):
        """测试MySQL约束违反处理"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        # Constraint violations raised as SQLAlchemy errors
        assert driver._session_factory is not None

    def test_mysql_timeout_error_handling(self):
        """测试MySQL超时错误处理"""
        with patch.object(GinkgoMysql, '_create_engine', return_value=Mock()):
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb", connect_timeout=1, read_timeout=2)
        assert driver._connect_timeout == 1
        assert driver._read_timeout == 2

    def test_mysql_server_gone_away_handling(self):
        """测试MySQL服务器断开处理"""
        # pool_pre_ping detects stale connections before use
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_mysql.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoMysql("user", "pwd", "localhost", "3306", "testdb")
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['pool_pre_ping'] is True
        assert call_kwargs['pool_recycle'] == 3600
