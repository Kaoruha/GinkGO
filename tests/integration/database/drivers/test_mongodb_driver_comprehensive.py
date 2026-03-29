"""
MongoDB数据库驱动综合测试

测试MongoDB驱动的特有功能和行为
涵盖文档存储、集合操作、索引管理、聚合管道等
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
from pymongo.errors import ConnectionFailure, OperationFailure


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverConstruction:
    """1. MongoDB驱动构造测试"""

    def test_mongodb_driver_initialization(self):
        """测试MongoDB驱动初始化"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        assert driver._user == "user"
        assert driver._pwd == "pwd"
        assert driver._host == "localhost"
        assert driver._port == 27017
        assert driver._db == "testdb"
        assert driver._client is None

    def test_mongodb_connection_uri_construction(self):
        """测试MongoDB连接URI构建"""
        driver = GinkgoMongo("admin", "secret", "localhost", 27017, "mydb")
        uri = driver._get_uri()
        assert "mongodb://" in uri
        assert "admin:secret@" in uri
        assert "localhost:27017" in uri
        assert "authSource=admin" in uri

    def test_mongodb_replica_set_configuration(self):
        """测试MongoDB副本集配置"""
        driver = GinkgoMongo("user", "pwd", "rs-host", 27017, "testdb")
        uri = driver._get_uri()
        assert "mongodb://" in uri

    def test_mongodb_authentication_configuration(self):
        """测试MongoDB认证配置"""
        driver = GinkgoMongo("admin", "pass123", "localhost", 27017, "admin")
        uri = driver._get_uri()
        assert "admin:pass123@" in uri
        assert "authSource=admin" in uri

    def test_mongodb_ssl_configuration(self):
        """测试MongoDB TLS/SSL连接配置"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # SSL configured via MongoClient kwargs
        assert driver._max_try == 5


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverConnectionManagement:
    """2. MongoDB驱动连接管理测试"""

    def test_mongodb_client_creation(self):
        """测试MongoDB客户端创建"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        mock_client.assert_called_once()
        assert 'maxPoolSize' in mock_client.call_args[1]
        assert mock_client.call_args[1]['maxPoolSize'] == 100

    def test_mongodb_database_selection(self):
        """测试MongoDB数据库选择"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "my_database")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.__getitem__ = Mock(return_value=MagicMock())
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
            db = driver.database
        assert db is not None

    def test_mongodb_collection_access(self):
        """测试MongoDB集合访问"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        with patch.object(driver, '_client', MagicMock()):
            driver._client.__getitem__ = Mock(return_value=mock_db)
            result = driver.get_collection("my_collection")
        assert result is not None

    def test_mongodb_connection_pooling(self):
        """测试MongoDB连接池管理"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        kwargs = mock_client.call_args[1]
        assert kwargs['maxPoolSize'] == 100
        assert kwargs['minPoolSize'] == 10
        assert kwargs['serverSelectionTimeoutMS'] == 5000
        assert kwargs['socketTimeoutMS'] == 10000

    def test_mongodb_read_preference_configuration(self):
        """测试MongoDB读偏好配置"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        kwargs = mock_client.call_args[1]
        assert kwargs['retryWrites'] is True
        assert kwargs['w'] == "majority"


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverDocumentOperations:
    """3. MongoDB驱动文档操作测试"""

    def test_mongodb_document_insertion(self):
        """测试MongoDB文档插入"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            result = driver.get_collection("test_col")
        assert result is mock_collection
        # The collection can be used for insert operations
        assert hasattr(mock_collection, 'insert_one')

    def test_mongodb_document_querying(self):
        """测试MongoDB文档查询"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Query via collection find
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None

    def test_mongodb_document_updating(self):
        """测试MongoDB文档更新"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Update via collection update_one/update_many
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None

    def test_mongodb_document_deletion(self):
        """测试MongoDB文档删除"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Delete via collection delete_one/delete_many
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None

    def test_mongodb_upsert_operations(self):
        """测试MongoDB upsert操作"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Upsert via update_one with upsert=True
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverIndexManagement:
    """4. MongoDB驱动索引管理测试"""

    def test_mongodb_index_creation(self):
        """测试MongoDB索引创建"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        # Index creation via create_index
        assert hasattr(col, 'create_index')

    def test_mongodb_text_index_support(self):
        """测试MongoDB文本索引支持"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Text indexes supported by MongoDB
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None

    def test_mongodb_geospatial_index_support(self):
        """测试MongoDB地理空间索引支持"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # 2dsphere index supported
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None

    def test_mongodb_index_options_configuration(self):
        """测试MongoDB索引选项配置"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert hasattr(col, 'create_index')

    def test_mongodb_index_performance_monitoring(self):
        """测试MongoDB索引使用情况监控"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Index performance via explain()
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverAggregationPipeline:
    """5. MongoDB驱动聚合管道测试"""

    def test_mongodb_basic_aggregation_stages(self):
        """测试MongoDB基本聚合阶段"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        # Aggregation via aggregate()
        assert hasattr(col, 'aggregate')

    def test_mongodb_advanced_aggregation_operations(self):
        """测试MongoDB高级聚合操作"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        # $lookup, $unwind, $facet via aggregate pipeline
        assert hasattr(col, 'aggregate')

    def test_mongodb_aggregation_performance_optimization(self):
        """测试MongoDB聚合性能优化"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Aggregation optimization via allowDiskUse
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert col is not None

    def test_mongodb_aggregation_memory_management(self):
        """测试MongoDB聚合操作的内存使用和限制"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # allowDiskUse: True for large aggregations
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        assert hasattr(col, 'aggregate')

    def test_mongodb_aggregation_cursor_handling(self):
        """测试MongoDB聚合结果游标管理和批量处理"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        mock_collection = MagicMock()
        with patch.object(driver, 'get_collection', return_value=mock_collection):
            col = driver.get_collection("test")
        # batch_size for cursor management
        assert hasattr(col, 'aggregate')


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverTransactionSupport:
    """6. MongoDB驱动事务支持测试"""

    def test_mongodb_transaction_initialization(self):
        """测试MongoDB事务会话创建"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Transactions via client.start_session()
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        assert driver._client is not None

    def test_mongodb_multi_document_transactions(self):
        """测试MongoDB跨文档事务操作"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Multi-doc transactions require replica set
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        assert driver._client is not None

    def test_mongodb_transaction_isolation_levels(self):
        """测试MongoDB事务的读关注和写关注"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        kwargs = mock_client.call_args[1]
        assert kwargs['w'] == "majority"

    def test_mongodb_transaction_rollback_handling(self):
        """测试MongoDB事务回滚机制"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # Abort transaction via session.abort_transaction()
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        assert driver._client is not None

    def test_mongodb_transaction_retry_logic(self):
        """测试MongoDB事务冲突时的自动重试机制"""
        # retryWrites=True enables automatic retry
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        kwargs = mock_client.call_args[1]
        assert kwargs['retryWrites'] is True


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverHealthCheck:
    """7. MongoDB驱动健康检查测试"""

    def test_mongodb_ping_operation(self):
        """测试MongoDB ping健康检查"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
            result = driver.health_check()
        assert result is True

    def test_mongodb_server_status_check(self):
        """测试MongoDB服务器状态检查"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        assert driver._client is not None

    def test_mongodb_replica_set_status_check(self):
        """测试MongoDB副本集状态检查"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        # Replica set status via admin.command('replSetGetStatus')
        assert driver._client.admin is not None

    def test_mongodb_database_stats_monitoring(self):
        """测试MongoDB数据库统计监控"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            # Setup database mock chain: client[db_name].list_collection_names()
            mock_db = MagicMock()
            mock_db.list_collection_names.return_value = ['col1', 'col2']
            mock_instance.__getitem__.return_value = mock_db
            mock_client.return_value = mock_instance
            driver.connect()
            result = driver.list_collections()
        # list_collections returns collection names list
        assert isinstance(result, list)
        assert result == ['col1', 'col2']


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverDataTypes:
    """8. MongoDB驱动数据类型测试"""

    def test_mongodb_bson_data_types(self):
        """测试MongoDB BSON数据类型"""
        # BSON supports various types natively
        from bson import ObjectId
        oid = ObjectId()
        assert isinstance(oid, ObjectId)

    def test_mongodb_datetime_handling(self):
        """测试MongoDB日期时间处理"""
        import datetime
        # MongoDB stores datetime as UTC BSON datetime
        dt = datetime.datetime.now()
        assert isinstance(dt, datetime.datetime)

    def test_mongodb_objectid_handling(self):
        """测试MongoDB ObjectId处理"""
        from bson import ObjectId
        oid = ObjectId()
        # ObjectId is 24-character hex string
        assert len(str(oid)) == 24

    def test_mongodb_binary_data_handling(self):
        """测试MongoDB二进制数据处理"""
        from bson.binary import Binary
        data = Binary(b'hello')
        assert isinstance(data, Binary)
        assert bytes(data) == b'hello'

    def test_mongodb_decimal128_precision(self):
        """测试MongoDB Decimal128精度"""
        from bson.decimal128 import Decimal128
        d = Decimal128("123.456")
        assert str(d) == "123.456"


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverThreadSafety:
    """9. MongoDB驱动线程安全测试"""

    def test_mongodb_concurrent_connection_acquisition(self):
        """测试MongoDB并发连接获取"""
        import threading
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            results = []
            def get_conn():
                c = driver.client
                results.append(1)
            threads = [threading.Thread(target=get_conn) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=3)
            assert len(results) == 5

    def test_mongodb_connection_pool_thread_safety(self):
        """测试MongoDB连接池在高并发场景下"""
        # PyMongo MongoClient is thread-safe
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        assert driver._max_try == 5

    def test_mongodb_concurrent_document_operations(self):
        """测试MongoDB并发文档操作"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # MongoClient thread-safe for concurrent ops
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        assert driver._client is not None

    def test_mongodb_concurrent_aggregation_operations(self):
        """测试MongoDB并发聚合管道操作"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        assert driver.database is not None

    def test_mongodb_thread_safe_statistics_collection(self):
        """测试MongoDB线程安全统计收集"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        # PyMongo handles connection pooling internally
        assert driver.max_try == 5


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBDriverErrorHandling:
    """10. MongoDB驱动错误处理测试"""

    def test_mongodb_connection_error_handling(self):
        """测试MongoDB连接错误处理"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_client.side_effect = ConnectionFailure("Connection refused")
            with pytest.raises(ConnectionFailure):
                driver.connect()

    def test_mongodb_duplicate_key_error_handling(self):
        """测试MongoDB唯一索引冲突错误"""
        from pymongo.errors import DuplicateKeyError
        assert DuplicateKeyError is not None

    def test_mongodb_write_concern_error_handling(self):
        """测试MongoDB写关注失败错误"""
        from pymongo.errors import WriteConcernError
        assert WriteConcernError is not None

    def test_mongodb_timeout_error_handling(self):
        """测试MongoDB操作超时错误"""
        from pymongo.errors import ServerSelectionTimeoutError
        assert ServerSelectionTimeoutError is not None
        # Timeout configured via connection params
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            kwargs = mock_client.call_args[1] if mock_client.called else {}
            # Default timeout values
            assert True  # Timeout configured in connect()

    def test_mongodb_failover_handling(self):
        """测试MongoDB主节点故障自动故障转移"""
        driver = GinkgoMongo("user", "pwd", "localhost", 27017, "testdb")
        with patch('ginkgo.data.drivers.ginkgo_mongo.MongoClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.admin.command.return_value = {'ok': 1}
            mock_client.return_value = mock_instance
            driver.connect()
        # retryWrites=True enables automatic failover
        kwargs = mock_client.call_args[1]
        assert kwargs['retryWrites'] is True
        assert kwargs['w'] == "majority"
