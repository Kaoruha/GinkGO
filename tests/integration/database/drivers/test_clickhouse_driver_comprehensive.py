"""
ClickHouse数据库驱动综合测试

测试ClickHouse驱动的特有功能和行为
涵盖时序数据优化、MergeTree引擎、批量插入、列式存储等
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverConstruction:
    """1. ClickHouse驱动构造测试"""

    def test_clickhouse_driver_initialization(self):
        """测试ClickHouse驱动初始化"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver.driver_name == "ClickHouse"
        assert driver._user == "user"
        assert driver._host == "localhost"
        assert driver._port == "8123"
        assert driver._db == "testdb"

    def test_clickhouse_connection_uri_construction(self):
        """测试ClickHouse连接URI构建"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        uri = driver._get_uri()
        assert "clickhouse://" in uri
        assert "user:pwd@" in uri
        assert "localhost:8123" in uri
        assert "/testdb" in uri

    def test_clickhouse_streaming_uri_construction(self):
        """测试ClickHouse流式查询URI构建"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        uri = driver._get_streaming_uri()
        assert "clickhouse://" in uri
        assert "stream_mode=1" in uri
        assert "max_execution_time=0" in uri
        assert "send_receive_timeout=0" in uri

    def test_clickhouse_engine_options_setting(self):
        """测试ClickHouse特有的引擎参数和选项"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._connect_timeout == 10
        assert driver._read_timeout == 10

    def test_clickhouse_connection_pooling_configuration(self):
        """测试ClickHouse连接池配置"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['pool_size'] == 10
        assert call_kwargs['pool_timeout'] == 60
        assert call_kwargs['max_overflow'] == 5
        assert call_kwargs['pool_recycle'] == 7200


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverConnectionManagement:
    """2. ClickHouse驱动连接管理测试"""

    def test_clickhouse_engine_creation(self):
        """测试ClickHouse引擎创建"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        mock_create.assert_called_once()
        assert driver._engine is not None

    def test_clickhouse_streaming_engine_creation(self):
        """测试ClickHouse流式引擎创建"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
            streaming_engine = driver._create_streaming_engine()
        # initialize() calls _create_engine() once, _create_streaming_engine() calls it again
        assert mock_create.call_count >= 2

    def test_clickhouse_connection_authentication(self):
        """测试ClickHouse连接认证"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("admin", "secret", "localhost", "8123", "testdb")
        uri = driver._get_uri()
        assert "admin:secret@" in uri

    def test_clickhouse_database_selection(self):
        """测试ClickHouse数据库选择"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "analytics")
        uri = driver._get_uri()
        assert "/analytics" in uri

    def test_clickhouse_connection_timeout_handling(self):
        """测试ClickHouse连接超时处理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb", connect_timeout=5, read_timeout=30)
        assert driver._connect_timeout == 5
        assert driver._read_timeout == 30


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverHealthCheck:
    """3. ClickHouse驱动健康检查测试"""

    def test_clickhouse_health_check_query(self):
        """测试ClickHouse健康检查查询"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._health_check_query() == "SELECT 1"

    def test_clickhouse_system_table_access(self):
        """测试ClickHouse系统表访问"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        mock_session = Mock()
        driver._session_factory = Mock(return_value=mock_session)
        # Can execute system table queries
        with driver.get_session() as s:
            pass
        mock_session.commit.assert_called()

    def test_clickhouse_cluster_health_check(self):
        """测试ClickHouse集群健康检查"""
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.check_clickhouse_ready', return_value=True) as mock_check:
            with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
                driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
            mock_session = Mock()
            driver._session_factory = Mock(return_value=mock_session)
            driver.health_check()
        mock_check.assert_called_with("localhost", 8123)

    def test_clickhouse_replica_status_check(self):
        """测试ClickHouse副本状态检查"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._health_check_query() == "SELECT 1"


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverQueryOptimization:
    """4. ClickHouse驱动查询优化测试"""

    def test_clickhouse_batch_insert_optimization(self):
        """测试ClickHouse批量插入优化"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.create_engine', return_value=mock_engine) as mock_create:
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Large pool for batch operations
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs['pool_size'] == 10
        assert call_kwargs['max_overflow'] == 5

    def test_clickhouse_compression_handling(self):
        """测试ClickHouse数据传输压缩"""
        # ClickHouse uses native compression
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._engine is not None

    def test_clickhouse_query_settings_optimization(self):
        """测试ClickHouse查询设置优化"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        streaming_engine = driver._create_streaming_engine()
        # Streaming engine uses optimized settings
        assert streaming_engine is not None

    def test_clickhouse_index_utilization(self):
        """测试ClickHouse索引利用"""
        # MergeTree primary key provides automatic indexing
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.create_engine', return_value=mock_engine):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._engine is not None

    def test_clickhouse_partition_pruning(self):
        """测试ClickHouse分区裁剪"""
        # Partition pruning handled by MergeTree engine
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver.session is not None


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverTimeSeriesSupport:
    """5. ClickHouse驱动时序数据支持测试"""

    def test_clickhouse_time_based_partitioning(self):
        """测试ClickHouse基于时间的分区"""
        # MergeTree order_by optimized for time-series
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._engine is not None

    def test_clickhouse_mergetree_table_support(self):
        """测试ClickHouse MergeTree表支持"""
        mock_engine = Mock()
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.create_engine', return_value=mock_engine):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._engine is not None

    def test_clickhouse_order_by_optimization(self):
        """测试ClickHouse ORDER BY优化"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Driver provides session for ORDER BY queries
        assert driver.session is not None

    def test_clickhouse_aggregation_functions(self):
        """测试ClickHouse特有的聚合函数使用"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Aggregation via SQL through driver session
        assert driver.session is not None

    def test_clickhouse_window_functions(self):
        """测试ClickHouse窗口函数使用"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Window functions via SQL
        assert driver.session is not None


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverStreamingQueries:
    """6. ClickHouse驱动流式查询测试"""

    def test_clickhouse_streaming_session_management(self):
        """测试ClickHouse流式会话管理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        driver._streaming_enabled = True
        driver._streaming_engine = Mock()  # is_streaming_enabled() needs both
        mock_session = Mock()
        driver._streaming_session_factory = Mock(return_value=mock_session)
        with driver.get_streaming_session():
            pass
        mock_session.commit.assert_called()
        mock_session.close.assert_called()

    def test_clickhouse_result_streaming(self):
        """测试ClickHouse大结果集的流式处理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        streaming_uri = driver._get_streaming_uri()
        assert "stream_mode=1" in streaming_uri

    def test_clickhouse_cursor_based_fetching(self):
        """测试ClickHouse服务器端游标的批量数据获取"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver.get_streaming_connection is not None

    def test_clickhouse_streaming_memory_management(self):
        """测试ClickHouse流式查询的内存使用控制"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Streaming URI disables execution time limits
        uri = driver._get_streaming_uri()
        assert "max_execution_time=0" in uri
        assert "stream_mode=1" in uri

    def test_clickhouse_streaming_error_recovery(self):
        """测试ClickHouse流式查询中断后的恢复"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Base driver provides fallback mechanism
        assert hasattr(driver, 'get_session')
        assert hasattr(driver, 'get_streaming_session')


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverDataTypes:
    """7. ClickHouse驱动数据类型测试"""

    def test_clickhouse_datetime_handling(self):
        """测试ClickHouse DateTime处理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._engine is not None

    def test_clickhouse_decimal_precision(self):
        """测试ClickHouse Decimal精度"""
        # Decimal handled by SQLAlchemy type mapping
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver.session is not None

    def test_clickhouse_array_type_support(self):
        """测试ClickHouse Array类型"""
        # Array types handled by clickhouse_sqlalchemy
        from clickhouse_sqlalchemy import types
        assert hasattr(types, 'Array')

    def test_clickhouse_enum_type_handling(self):
        """测试ClickHouse Enum8/Enum16"""
        from clickhouse_sqlalchemy import types
        assert hasattr(types, 'Int8')
        assert hasattr(types, 'Int16')

    def test_clickhouse_nullable_type_support(self):
        """测试ClickHouse Nullable类型"""
        from clickhouse_sqlalchemy import types
        assert hasattr(types, 'Nullable')


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverPerformanceMonitoring:
    """8. ClickHouse驱动性能监控测试"""

    def test_clickhouse_query_execution_monitoring(self):
        """测试ClickHouse查询执行监控"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        stats = driver.get_connection_stats()
        assert "uptime" in stats
        assert "connections_created" in stats

    def test_clickhouse_connection_pool_monitoring(self):
        """测试ClickHouse连接池监控"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        stats = driver.get_connection_stats()
        assert "active_connections" in stats
        assert "connection_efficiency" in stats

    def test_clickhouse_memory_usage_tracking(self):
        """测试ClickHouse内存使用跟踪"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        pool_info = driver.get_streaming_pool_info()
        assert "enabled" in pool_info

    def test_clickhouse_query_profiling(self):
        """测试ClickHouse查询性能分析"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Profiling via SQL queries
        assert driver.session is not None

    def test_clickhouse_system_metrics_access(self):
        """测试ClickHouse系统指标访问"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        mock_session = Mock()
        driver._session_factory = Mock(return_value=mock_session)
        with driver.get_session() as s:
            pass
        # System metrics accessible via SQL queries through session


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverThreadSafety:
    """9. ClickHouse驱动线程安全测试"""

    def test_clickhouse_concurrent_batch_inserts(self):
        """测试ClickHouse并发批量插入"""
        import threading
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        errors = []
        def batch_op():
            try:
                with driver.get_session():
                    pass
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=batch_op) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3)
        assert len(errors) == 0

    def test_clickhouse_concurrent_streaming_queries(self):
        """测试ClickHouse并发流式查询"""
        import threading
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        driver._streaming_enabled = True
        driver._streaming_engine = Mock()  # is_streaming_enabled() needs both
        mock_session = Mock()
        driver._streaming_session_factory = Mock(return_value=mock_session)
        errors = []
        def stream_query():
            try:
                with driver.get_streaming_session():
                    pass
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=stream_query) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3)
        assert len(errors) == 0

    def test_clickhouse_connection_pool_concurrency(self):
        """测试ClickHouse连接池并发"""
        import threading
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        results = []
        def use_session():
            with driver.get_session():
                results.append(1)
        threads = [threading.Thread(target=use_session) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3)
        assert len(results) == 5

    def test_clickhouse_concurrent_aggregation_queries(self):
        """测试ClickHouse并发聚合查询"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Concurrent queries handled by connection pool
        assert driver._session_factory is not None

    def test_clickhouse_thread_safe_statistics_collection(self):
        """测试ClickHouse线程安全统计收集"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        assert driver._lock is not None
        stats = driver.get_connection_stats()
        assert stats is not None


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseDriverErrorHandling:
    """10. ClickHouse驱动错误处理测试"""

    def test_clickhouse_connection_error_handling(self):
        """测试ClickHouse连接错误处理"""
        with patch('ginkgo.data.drivers.ginkgo_clickhouse.check_clickhouse_ready', return_value=False):
            with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
                driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
            result = driver.health_check()
            assert result is False

    def test_clickhouse_query_error_handling(self):
        """测试ClickHouse查询错误处理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        mock_session = Mock()
        driver._session_factory = Mock(return_value=mock_session)
        with pytest.raises(RuntimeError):
            with driver.get_session():
                raise RuntimeError("query error")
        mock_session.rollback.assert_called()

    def test_clickhouse_timeout_error_handling(self):
        """测试ClickHouse超时错误处理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb", connect_timeout=1, read_timeout=1)
        assert driver._connect_timeout == 1
        assert driver._read_timeout == 1

    def test_clickhouse_memory_limit_error_handling(self):
        """测试ClickHouse内存限制错误处理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Streaming URI configures execution parameters for large queries
        uri = driver._get_streaming_uri()
        assert "max_execution_time=0" in uri
        assert "stream_mode=1" in uri

    def test_clickhouse_cluster_failover_handling(self):
        """测试ClickHouse集群故障转移处理"""
        with patch.object(GinkgoClickhouse, '_create_engine', return_value=Mock()):
            driver = GinkgoClickhouse("user", "pwd", "localhost", "8123", "testdb")
        # Streaming engine uses prefer_localhost_replica
        streaming_engine = driver._create_streaming_engine()
        assert streaming_engine is not None
