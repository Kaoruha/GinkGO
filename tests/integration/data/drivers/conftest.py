"""
数据库驱动测试共享fixtures

提供跨驱动测试文件共享的pytest fixtures
"""
import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture
def mock_logger():
    """模拟日志器"""
    logger = MagicMock()
    logger.logger_name = "test_logger"
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def mock_engine():
    """模拟数据库引擎"""
    engine = MagicMock()
    engine.connect = MagicMock()
    engine.raw_connection = MagicMock()
    engine.pool = MagicMock()
    engine.url = "test://localhost"
    return engine


@pytest.fixture
def mock_session_factory():
    """模拟会话工厂"""
    factory = MagicMock()
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.execute = MagicMock()
    factory.return_value = session
    factory.remove = MagicMock()
    return factory, session


@pytest.fixture
def connection_stats():
    """连接统计信息"""
    return {
        "created_at": time.time(),
        "connections_created": 0,
        "connections_closed": 0,
        "active_connections": 0,
        "last_health_check": 0,
        "health_check_failures": 0,
        "streaming_connections_created": 0,
        "streaming_connections_closed": 0,
        "active_streaming_connections": 0,
        "streaming_sessions_active": 0,
    }


@pytest.fixture
def mock_health_check_result():
    """模拟健康检查结果"""
    return True


@pytest.fixture
def database_config():
    """数据库配置"""
    return {
        "host": "localhost",
        "port": 3306,
        "database": "test_db",
        "username": "test_user",
        "password": "test_pass",
    }


@pytest.fixture
def streaming_config():
    """流式查询配置"""
    return {
        "enabled": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 3600,
    }


# 参数化测试数据
@pytest.fixture
def valid_database_names():
    """有效数据库名称"""
    return [
        "clickhouse",
        "mysql",
        "mongodb",
        "redis",
    ]


@pytest.fixture
def invalid_database_names():
    """无效数据库名称"""
    return [
        "",
        None,
        123,
        "invalid_db",
    ]


@pytest.fixture
def connection_timeout_values():
    """连接超时值"""
    return [
        (5, "short_timeout"),
        (30, "normal_timeout"),
        (300, "long_timeout"),
        (None, "no_timeout"),
    ]


@pytest.fixture
def pool_size_values():
    """连接池大小值"""
    return [
        (1, "min_pool"),
        (10, "normal_pool"),
        (100, "large_pool"),
        (None, "default_pool"),
    ]


@pytest.fixture
def error_scenarios():
    """错误场景"""
    return [
        ("ConnectionError", "connection_failed"),
        ("TimeoutError", "query_timeout"),
        ("OperationalError", "database_unavailable"),
        ("InterfaceError", "driver_error"),
    ]


@pytest.fixture
def query_types():
    """查询类型"""
    return [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "DROP",
    ]


@pytest.fixture
def isolation_levels():
    """事务隔离级别"""
    return [
        "READ_UNCOMMITTED",
        "READ_COMMITTED",
        "REPEATABLE_READ",
        "SERIALIZABLE",
    ]


@pytest.fixture
def mock_transaction():
    """模拟事务"""
    transaction = MagicMock()
    transaction.commit = MagicMock()
    transaction.rollback = MagicMock()
    transaction.begin = MagicMock()
    return transaction


@pytest.fixture
def thread_pool():
    """线程池"""
    threads = []
    results = []

    def worker(func):
        def wrapper(*args, **kwargs):
            t = threading.Thread(target=func, args=args, kwargs=kwargs)
            threads.append(t)
            return t
        return wrapper

    yield worker, results, threads

    # 清理
    for t in threads:
        if t.is_alive():
            t.join(timeout=1)


@pytest.fixture
def mock_cache():
    """模拟缓存"""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    cache.delete = MagicMock()
    cache.clear = MagicMock()
    return cache


@pytest.fixture
def performance_metrics():
    """性能指标"""
    return {
        "query_time": 0.1,
        "connection_time": 0.05,
        "rows_affected": 100,
        "bytes_transferred": 1024,
    }


@pytest.fixture
def retry_config():
    """重试配置"""
    return {
        "max_try": 3,
        "delay": 1,
        "backoff": 2,
        "exceptions": (Exception,),
    }
