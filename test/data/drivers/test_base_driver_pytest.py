"""
数据库基础驱动测试 - Pytest最佳实践重构

测试DatabaseDriverBase抽象基类的核心功能
涵盖连接管理、健康检查、流式查询、统计监控等
"""
import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from contextlib import contextmanager
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.drivers.base_driver import DatabaseDriverBase


# 创建一个具体实现用于测试
class ConcreteTestDriver(DatabaseDriverBase):
    """具体测试驱动实现"""

    def __init__(self):
        super().__init__("TestDriver")
        self._create_engine_called = False
        self._create_streaming_engine_called = False

    def _create_engine(self):
        self._create_engine_called = True
        return MagicMock()

    def _create_streaming_engine(self):
        self._create_streaming_engine_called = True
        return MagicMock()

    def _health_check_query(self) -> str:
        return "SELECT 1"

    def _get_uri(self) -> str:
        return "test://localhost"

    def _get_streaming_uri(self) -> str:
        return "test://localhost/streaming"


@pytest.fixture
def test_driver():
    """测试驱动实例"""
    return ConcreteTestDriver()


@pytest.fixture
def initialized_driver(test_driver):
    """已初始化的驱动"""
    test_driver._engine = MagicMock()
    test_driver._session_factory = MagicMock()
    return test_driver


@pytest.mark.unit
class TestDatabaseDriverBaseConstruction:
    """测试驱动基础构造"""

    def test_driver_initialization(self, test_driver):
        """测试驱动初始化"""
        assert test_driver.driver_name == "TestDriver"
        assert test_driver._db_type == "testdriver"
        assert test_driver._engine is None
        assert test_driver._session_factory is None

    def test_driver_stats_initialization(self, test_driver):
        """测试统计信息初始化"""
        assert "created_at" in test_driver._connection_stats
        assert "connections_created" in test_driver._connection_stats
        assert test_driver._connection_stats["connections_created"] == 0

    def test_driver_streaming_initialization(self, test_driver):
        """测试流式查询初始化"""
        assert test_driver._streaming_engine is None
        assert test_driver._streaming_session_factory is None
        assert test_driver.is_streaming_enabled() is False

    def test_driver_lock_initialization(self, test_driver):
        """测试锁初始化"""
        assert test_driver._lock is not None
        assert isinstance(test_driver._lock, threading.Lock)

    def test_driver_loggers_initialization(self, test_driver):
        """测试日志器初始化"""
        assert len(test_driver.loggers) >= 1  # 至少有GLOG


@pytest.mark.unit
class TestDatabaseDriverLogging:
    """测试日志系统"""

    def test_add_logger(self, test_driver, mock_logger):
        """测试添加日志器"""
        initial_count = len(test_driver.loggers)
        test_driver.add_logger(mock_logger)
        assert len(test_driver.loggers) == initial_count + 1

    def test_duplicate_logger_prevention(self, test_driver, mock_logger):
        """测试防止重复日志器"""
        test_driver.add_logger(mock_logger)
        initial_count = len(test_driver.loggers)
        test_driver.add_logger(mock_logger)  # 添加相同日志器
        assert len(test_driver.loggers) == initial_count

    def test_log_method(self, test_driver, mock_logger):
        """测试log方法"""
        test_driver.add_logger(mock_logger)
        test_driver.log("INFO", "test message")
        mock_logger.info.assert_called_once()

    def test_log_all_levels(self, test_driver):
        """测试所有日志级别"""
        logger = MagicMock()
        test_driver.add_logger(logger)

        test_driver.log("INFO", "info msg")
        test_driver.log("ERROR", "error msg")
        test_driver.log("WARNING", "warning msg")
        test_driver.log("DEBUG", "debug msg")

        logger.info.assert_called_once()
        logger.error.assert_called_once()
        logger.warning.assert_called_once()
        logger.debug.assert_called_once()

    def test_log_with_incompatible_logger(self, test_driver):
        """测试不兼容日志器的处理"""
        bad_logger = Mock()  # 没有正确方法
        test_driver.add_logger(bad_logger)
        # 应该不抛出异常
        test_driver.log("INFO", "test message")


@pytest.mark.unit
class TestDatabaseDriverConnectionManagement:
    """测试连接管理"""

    def test_initialize_engine(self, test_driver):
        """测试引擎初始化"""
        test_driver.initialize()
        assert test_driver._create_engine_called is True

    def test_session_creation(self, initialized_driver):
        """测试会话创建"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        with initialized_driver.get_session() as session:
            assert session == mock_session

    def test_session_commit_on_success(self, initialized_driver):
        """测试成功时提交"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        with initialized_driver.get_session() as session:
            pass

        mock_session.commit.assert_called_once()

    def test_session_rollback_on_error(self, initialized_driver):
        """测试错误时回滚"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        try:
            with initialized_driver.get_session() as session:
                raise ValueError("Test error")
        except ValueError:
            pass

        mock_session.rollback.assert_called_once()

    def test_session_close_on_exit(self, initialized_driver):
        """测试退出时关闭会话"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        with initialized_driver.get_session() as session:
            pass

        mock_session.close.assert_called_once()

    def test_connection_stats_update(self, initialized_driver):
        """测试连接统计更新"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        with initialized_driver.get_session() as session:
            pass

        assert initialized_driver._connection_stats["connections_created"] >= 1
        assert initialized_driver._connection_stats["connections_closed"] >= 1


@pytest.mark.unit
class TestDatabaseDriverStreaming:
    """测试流式查询支持"""

    def test_streaming_initialize(self, test_driver):
        """测试流式查询初始化"""
        test_driver.initialize_streaming()
        assert test_driver._create_streaming_engine_called is True

    def test_streaming_session_creation(self, test_driver):
        """测试流式会话创建"""
        test_driver.initialize_streaming()
        mock_session = MagicMock()
        test_driver._streaming_session_factory.return_value = mock_session

        with test_driver.get_streaming_session() as session:
            assert session == mock_session

    def test_streaming_enabled_check(self, test_driver):
        """测试流式查询启用检查"""
        assert test_driver.is_streaming_enabled() is False
        test_driver.initialize_streaming()
        assert test_driver.is_streaming_enabled() is True

    def test_streaming_connection_get(self, test_driver):
        """测试流式连接获取"""
        test_driver.initialize_streaming()
        mock_connection = MagicMock()
        test_driver._streaming_engine.raw_connection.return_value = mock_connection

        connection = test_driver.get_streaming_connection()
        assert connection is not None


@pytest.mark.unit
class TestDatabaseDriverHealthCheck:
    """测试健康检查"""

    def test_health_check_success(self, initialized_driver):
        """测试健康检查成功"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        result = initialized_driver.health_check()
        assert result is True

    def test_health_check_failure(self, initialized_driver):
        """测试健康检查失败"""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Connection failed")
        initialized_driver._session_factory.return_value = mock_session

        result = initialized_driver.health_check()
        assert result is False

    def test_health_check_updates_stats(self, initialized_driver):
        """测试健康检查更新统计"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        initialized_driver.health_check()
        assert initialized_driver._connection_stats["last_health_check"] > 0

    def test_health_check_failure_counter(self, initialized_driver):
        """测试健康检查失败计数"""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Connection failed")
        initialized_driver._session_factory.return_value = mock_session

        initialized_driver.health_check()
        assert initialized_driver._connection_stats["health_check_failures"] >= 1


@pytest.mark.unit
class TestDatabaseDriverStatistics:
    """测试统计信息"""

    def test_get_connection_stats(self, test_driver):
        """测试获取连接统计"""
        stats = test_driver.get_connection_stats()
        assert "driver_name" in stats
        assert "uptime" in stats
        assert "connection_efficiency" in stats

    def test_stats_uptime_calculation(self, test_driver):
        """测试运行时间计算"""
        time.sleep(0.1)
        stats = test_driver.get_connection_stats()
        assert stats["uptime"] >= 0.1

    def test_stats_streaming_info(self, test_driver):
        """测试流式查询统计"""
        info = test_driver.get_streaming_pool_info()
        assert "enabled" in info
        assert info["enabled"] is False


@pytest.mark.unit
class TestDatabaseDriverBackwardCompatibility:
    """测试向后兼容性"""

    def test_engine_property(self, test_driver):
        """测试engine属性"""
        test_driver.initialize()
        assert test_driver.engine is not None

    def test_session_property(self, test_driver):
        """测试session属性"""
        test_driver.initialize()
        assert test_driver.session is not None

    def test_remove_session(self, test_driver):
        """测试remove_session方法"""
        test_driver.initialize()
        test_driver.remove_session()  # 应该不抛出异常


@pytest.mark.unit
class TestDatabaseDriverAbstractMethods:
    """测试抽象方法"""

    def test_create_engine_must_be_implemented(self):
        """测试_create_engine必须实现"""
        class IncompleteDriver(DatabaseDriverBase):
            def __init__(self):
                super().__init__("Incomplete")
            def _create_streaming_engine(self):
                return MagicMock()
            def _health_check_query(self):
                return "SELECT 1"
            def _get_uri(self):
                return "test://"
            def _get_streaming_uri(self):
                return "test://"

        driver = IncompleteDriver()
        with pytest.raises(AttributeError):
            driver._create_engine()

    def test_abstract_methods_exist(self, test_driver):
        """测试抽象方法存在"""
        assert hasattr(test_driver, '_create_engine')
        assert hasattr(test_driver, '_create_streaming_engine')
        assert hasattr(test_driver, '_health_check_query')
        assert hasattr(test_driver, '_get_uri')
        assert hasattr(test_driver, '_get_streaming_uri')


@pytest.mark.unit
class TestDatabaseDriverThreadSafety:
    """测试线程安全性"""

    def test_concurrent_session_creation(self, initialized_driver):
        """测试并发会话创建"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        results = []
        def create_session():
            with initialized_driver.get_session() as session:
                results.append(session)

        threads = [threading.Thread(target=create_session) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10

    def test_thread_safe_stats_update(self, initialized_driver):
        """测试线程安全统计更新"""
        mock_session = MagicMock()
        initialized_driver._session_factory.return_value = mock_session

        def create_session():
            with initialized_driver.get_session() as session:
                pass

        threads = [threading.Thread(target=create_session) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = initialized_driver.get_connection_stats()
        assert stats["connections_created"] >= 10


@pytest.mark.unit
class TestDatabaseDriverErrorHandling:
    """测试错误处理"""

    def test_initialize_retry(self, test_driver):
        """测试初始化重试"""
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection failed")
            return MagicMock()

        with patch.object(test_driver, '_create_engine', side_effect=side_effect):
            test_driver.initialize()
            assert call_count >= 2

    def test_session_error_doesnt_crash(self, initialized_driver):
        """测试会话错误不会崩溃"""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Query failed")
        initialized_driver._session_factory.return_value = mock_session

        with pytest.raises(Exception):
            with initialized_driver.get_session() as session:
                session.execute("SELECT 1")

    def test_health_check_error_resilience(self, initialized_driver):
        """测试健康检查错误弹性"""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Health check failed")
        initialized_driver._session_factory.return_value = mock_session

        result = initialized_driver.health_check()
        assert result is False


@pytest.mark.unit
class TestDatabaseDriverStreamingFallback:
    """测试流式查询降级"""

    def test_streaming_fallback_to_regular(self, test_driver):
        """测试流式查询降级到常规会话"""
        mock_session = MagicMock()
        test_driver._session_factory.return_value = mock_session

        # 流式查询未启用，应该降级
        with test_driver.get_streaming_session() as session:
            assert session == mock_session

    def test_streaming_auto_initialization(self, test_driver):
        """测试流式查询自动初始化"""
        test_driver.initialize()  # 仅初始化常规引擎
        mock_session = MagicMock()
        test_driver._session_factory.return_value = mock_session

        # 尝试获取流式会话
        with test_driver.get_streaming_session() as session:
            # 由于无法初始化流式引擎，应该降级
            assert session == mock_session


@pytest.mark.unit
@pytest.mark.parametrize("stat_field", [
    "connections_created",
    "connections_closed",
    "active_connections",
    "health_check_failures",
])
class TestDatabaseDriverStatisticsFields:
    """测试统计字段"""

    def test_stats_field_exists(self, test_driver, stat_field):
        """测试统计字段存在"""
        assert stat_field in test_driver._connection_stats

    def test_stats_field_initial_value(self, test_driver, stat_field):
        """测试统计字段初始值"""
        if stat_field != "created_at":
            assert test_driver._connection_stats[stat_field] == 0


@pytest.mark.unit
class TestDatabaseDriverConfiguration:
    """测试驱动配置"""

    def test_driver_name_setting(self, test_driver):
        """测试驱动名称设置"""
        assert test_driver.driver_name == "TestDriver"

    def test_db_type_setting(self, test_driver):
        """测试数据库类型设置"""
        assert test_driver._db_type == "testdriver"

    def test_shared_logger_class_variable(self):
        """测试共享日志器类变量"""
        driver1 = ConcreteTestDriver()
        driver2 = ConcreteTestDriver()
        # 共享同一个数据库日志器
        assert ConcreteTestDriver._shared_database_logger is not None
