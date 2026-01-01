# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: MongoDB Collections, CRUD Operations
# Role: GinkgoMongo驱动提供MongoDB连接池和文档操作支持文档存储支持通知系统和交易功能


import time
from typing import Optional, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from ginkgo.libs import GLOG, GinkgoLogger, time_logger, retry

data_logger = GinkgoLogger("ginkgo_data", ["ginkgo_data.log"])


class GinkgoMongo(object):
    """
    Ginkgo MongoDB 驱动

    基于 pymongo 实现，支持连接池、健康检查和自动重试

    Attributes:
        _client: pymongo MongoClient 实例
        _uri: MongoDB 连接 URI
        _host: MongoDB 主机地址
        _port: MongoDB 端口
        _user: MongoDB 用户名
        _pwd: MongoDB 密码
        _db: 默认数据库名称
        _max_try: 最大重试次数
    """

    def __init__(self, user: str, pwd: str, host: str, port: int, db: str) -> None:
        """
        初始化 GinkgoMongo 驱动

        Args:
            user: MongoDB 用户名
            pwd: MongoDB 密码
            host: MongoDB 主机地址
            port: MongoDB 端口
            db: 默认数据库名称
        """
        self._client: Optional[MongoClient] = None
        self._uri: Optional[str] = None
        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db
        self._max_try = 5

    @property
    def max_try(self) -> int:
        """获取最大重试次数"""
        return self._max_try

    @property
    def client(self) -> MongoClient:
        """
        获取 MongoClient 实例

        如果连接未建立，自动调用 connect() 方法

        Returns:
            MongoClient: pymongo 客户端实例
        """
        if self._client is None:
            self.connect()
        return self._client

    @property
    def database(self):
        """
        获取默认数据库

        Returns:
            Database: MongoDB 数据库实例
        """
        return self.client[self._db]

    def _get_uri(self) -> str:
        """
        构建 MongoDB 连接 URI

        Returns:
            str: MongoDB 连接字符串

        Examples:
            >>> # 带认证的连接
            >>> # mongodb://username:password@host:port/?authSource=admin
            >>> # 不带认证的连接
            >>> # mongodb://host:port/
        """
        if self._user and self._pwd:
            return f"mongodb://{self._user}:{self._pwd}@{self._host}:{self._port}/?authSource=admin"
        return f"mongodb://{self._host}:{self._port}/"

    @time_logger
    @retry
    def connect(self) -> None:
        """
        建立 MongoDB 连接

        创建 MongoClient 实例并配置连接池：
        - maxPoolSize: 连接池最大连接数（100）
        - minPoolSize: 连接池最小连接数（10）
        - serverSelectionTimeoutMS: 服务器选择超时（5秒）
        - connectTimeoutMS: 连接超时（5秒）
        - socketTimeoutMS: Socket 超时（10秒）
        - retryWrites: 自动重试写操作
        - w: 写确认（majority）

        Raises:
            ConnectionFailure: 连接失败
            ServerSelectionTimeoutError: 服务器选择超时
        """
        if self._client is not None:
            self._client.close()

        self._uri = self._get_uri()

        self._client = MongoClient(
            self._uri,
            maxPoolSize=100,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            retryWrites=True,
            w="majority"
        )

        # 验证连接
        self._client.admin.command('ping')
        GLOG.DEBUG(f"Connected to MongoDB at {self._host}:{self._port}")

    @time_logger
    @retry
    def health_check(self) -> bool:
        """
        检查 MongoDB 连接健康状态

        执行 ping 命令验证连接是否正常

        Returns:
            bool: 连接正常返回 True，否则返回 False

        Examples:
            >>> if mongo.health_check():
            ...     print("MongoDB is healthy")
        """
        try:
            result = self.client.admin.command('ping')
            is_ok = result.get('ok') == 1
            if is_ok:
                GLOG.DEBUG("MongoDB health check passed")
            return is_ok
        except (ConnectionFailure, OperationFailure) as e:
            GLOG.ERROR(f"MongoDB health check failed: {e}")
            return False

    @time_logger
    def get_collection(self, collection_name: str, db_name: str = None):
        """
        获取指定集合

        Args:
            collection_name: 集合名称
            db_name: 数据库名称（默认使用初始化时的数据库）

        Returns:
            Collection: MongoDB 集合实例，连接失败时返回 None

        降级策略: 连接失败时返回 None，调用方应检查返回值
        """
        try:
            db = self._client[db_name] if db_name else self.database
            return db[collection_name]
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            GLOG.ERROR(f"Failed to get collection '{collection_name}': {e}")
            return None

    @time_logger
    def list_collections(self, db_name: str = None) -> List[str]:
        """
        列出数据库中的所有集合

        Args:
            db_name: 数据库名称（默认使用初始化时的数据库）

        Returns:
            List[str]: 集合名称列表，连接失败时返回空列表

        降级策略: 连接失败时返回空列表
        """
        try:
            db = self._client[db_name] if db_name else self.database
            return db.list_collection_names()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            GLOG.ERROR(f"Failed to list collections: {e}")
            return []

    @time_logger
    def is_collection_exists(self, collection_name: str, db_name: str = None) -> bool:
        """
        检查集合是否存在

        Args:
            collection_name: 集合名称
            db_name: 数据库名称（默认使用初始化时的数据库）

        Returns:
            bool: 集合存在返回 True，否则返回 False，连接失败时返回 False

        降级策略: 连接失败时返回 False
        """
        try:
            collections = self.list_collections(db_name)
            return collection_name in collections
        except Exception as e:
            GLOG.ERROR(f"Failed to check collection existence '{collection_name}': {e}")
            return False

    @time_logger
    def get_collection_size(self, collection_name: str, db_name: str = None) -> int:
        """
        获取集合文档数量

        Args:
            collection_name: 集合名称
            db_name: 数据库名称（默认使用初始化时的数据库）

        Returns:
            int: 文档数量，连接失败时返回 0

        降级策略: 连接失败时返回 0
        """
        try:
            collection = self.get_collection(collection_name, db_name)
            if collection is None:
                return 0
            count = collection.estimated_document_count()
            GLOG.DEBUG(f"Collection {collection_name} size is {count}")
            return count
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            GLOG.ERROR(f"Failed to get collection size '{collection_name}': {e}")
            return 0

    def __del__(self):
        """析构函数，关闭 MongoDB 连接"""
        try:
            if self._client is not None:
                self._client.close()
        except Exception:
            # Python 关闭时忽略所有错误（sys.meta_path 可能已是 None）
            pass
