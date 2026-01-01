# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: 数据库驱动模块导出ClickHouse/MySQL/MongoDB/Redis等数据库驱动封装底层连接






import time
import datetime
import threading
from typing import List, Optional, Union, Any
from sqlalchemy import inspect, select, func

from ginkgo.data.drivers.base_driver import DatabaseDriverBase
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
from ginkgo.data.drivers.ginkgo_redis import GinkgoRedis
from ginkgo.libs import GLOG


class CircuitBreaker:
    """
    熔断器实现

    防止级联故障，当失败率过高时快速失败

    状态转换:
    - CLOSED → OPEN: 失败率超过阈值
    - OPEN → HALF_OPEN: 超时后尝试恢复
    - HALF_OPEN → CLOSED: 恢复成功
    - HALF_OPEN → OPEN: 恢复失败
    """

    def __init__(
        self,
        failure_threshold: int = 5,  # 失败阈值
        recovery_timeout: int = 30,   # 恢复超时（秒）
        expected_exception: Exception = Exception
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 触发熔断的失败次数阈值
            recovery_timeout: 熔断器打开后的恢复超时时间
            expected_exception: 需要捕获的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """
        通过熔断器调用函数

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值

        Raises:
            Exception: 熔断器打开时的异常
        """
        with self._lock:
            if self._state == "OPEN":
                # 检查是否可以尝试恢复
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = "HALF_OPEN"
                    GLOG.INFO("Circuit breaker entering HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN - blocking request")

        try:
            result = func(*args, **kwargs)

            # 成功，重置失败计数
            with self._lock:
                if self._state == "HALF_OPEN":
                    self._state = "CLOSED"
                    self._failure_count = 0
                    GLOG.INFO("Circuit breaker recovered to CLOSED state")
                elif self._state == "CLOSED":
                    self._failure_count = 0

            return result

        except self.expected_exception as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()

                if self._failure_count >= self.failure_threshold:
                    self._state = "OPEN"
                    GLOG.ERROR(f"Circuit breaker opened after {self._failure_count} failures: {e}")

                if self._state == "HALF_OPEN":
                    self._state = "OPEN"
                    GLOG.WARN("Circuit breaker re-opened after recovery failure")

            raise

    @property
    def state(self) -> str:
        """获取熔断器状态"""
        return self._state

    @property
    def failure_count(self) -> int:
        """获取失败计数"""
        return self._failure_count

    def reset(self):
        """手动重置熔断器"""
        with self._lock:
            self._state = "CLOSED"
            self._failure_count = 0
            self._last_failure_time = None
            GLOG.INFO("Circuit breaker manually reset")
from ginkgo.data.drivers.ginkgo_kafka import (
    GinkgoProducer,
    GinkgoConsumer,
    kafka_topic_llen,
)
from ginkgo.data.models import MClickBase, MMysqlBase, MMongoBase
from ginkgo.libs import try_wait_counter, GLOG, GCONF, time_logger, retry, skip_if_ran, cache_with_expiration

max_try = 5


class ConnectionManager:
    """统一的数据库连接管理器"""

    def __init__(self):
        self._mysql_conn = None
        self._click_conn = None
        self._mongo_conn = None
        self._lock = threading.Lock()
        # MongoDB熔断器：5次失败后打开，30秒后尝试恢复
        self._mongo_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            expected_exception=Exception
        )

    def get_mysql_connection(self) -> GinkgoMysql:
        """获取MySQL连接，带健康检查"""
        with self._lock:
            if self._mysql_conn is None:
                GLOG.DEBUG("Creating MySQL connection pool instance...")
                self._mysql_conn = create_mysql_connection()
            elif not self._mysql_conn.health_check():
                GLOG.WARN("MySQL connection unhealthy, recreating...")
                self._mysql_conn = create_mysql_connection()

        return self._mysql_conn

    def get_clickhouse_connection(self) -> GinkgoClickhouse:
        """获取ClickHouse连接，带健康检查"""
        with self._lock:
            if self._click_conn is None:
                GLOG.DEBUG("Creating ClickHouse connection pool instance...")
                self._click_conn = create_click_connection()
            elif not self._click_conn.health_check():
                GLOG.WARN("ClickHouse connection unhealthy, recreating...")
                self._click_conn = create_click_connection()

        return self._click_conn

    def get_mongo_connection(self) -> GinkgoMongo:
        """获取MongoDB连接，带熔断器保护、健康检查和错误恢复"""
        def _create_or_restore():
            """内部函数：创建或恢复连接"""
            with self._lock:
                if self._mongo_conn is None:
                    GLOG.DEBUG("Creating MongoDB connection pool instance...")
                    self._mongo_conn = create_mongo_connection()
                elif not self._mongo_conn.health_check():
                    # 连接不健康，尝试重新连接（带指数退避重试）
                    GLOG.WARN("MongoDB connection unhealthy, attempting recovery...")
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            # 指数退避：1s, 2s, 4s
                            if attempt > 0:
                                wait_time = 2 ** attempt
                                GLOG.INFO(f"Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                                time.sleep(wait_time)

                            self._mongo_conn = create_mongo_connection()
                            GLOG.INFO("MongoDB connection recovered successfully")
                            break
                        except Exception as e:
                            GLOG.ERROR(f"Recovery attempt {attempt + 1} failed: {e}")
                            if attempt == max_retries - 1:
                                GLOG.ERROR("MongoDB connection recovery failed after all retries")
                                raise

                return self._mongo_conn

        # 通过熔断器调用连接创建
        try:
            return self._mongo_circuit_breaker.call(_create_or_restore)
        except Exception as e:
            GLOG.ERROR(f"MongoDB circuit breaker blocked: {e}")
            raise

    @cache_with_expiration(expiration_seconds=30)
    def get_connection_status(self) -> dict:
        """获取连接状态信息（缓存30秒）"""
        status = {}

        if self._mysql_conn:
            try:
                mysql_healthy = self._mysql_conn.health_check()
                mysql_stats = self._mysql_conn.get_connection_stats()
                status["mysql"] = {"healthy": mysql_healthy, "stats": mysql_stats}
            except Exception as e:
                status["mysql"] = {"healthy": False, "error": str(e)}
        else:
            status["mysql"] = {"healthy": False, "status": "not_initialized"}

        if self._click_conn:
            try:
                click_healthy = self._click_conn.health_check()
                click_stats = self._click_conn.get_connection_stats()
                status["clickhouse"] = {"healthy": click_healthy, "stats": click_stats}
            except Exception as e:
                status["clickhouse"] = {"healthy": False, "error": str(e)}
        else:
            status["clickhouse"] = {"healthy": False, "status": "not_initialized"}

        if self._mongo_conn:
            try:
                mongo_healthy = self._mongo_conn.health_check()
                status["mongodb"] = {"healthy": mongo_healthy}
            except Exception as e:
                status["mongodb"] = {"healthy": False, "error": str(e)}
        else:
            status["mongodb"] = {"healthy": False, "status": "not_initialized"}

        return status


# 全局连接管理器实例
_connection_manager = ConnectionManager()

# 全局连接实例 - 向后兼容
_mysql_connection_instance = None
_click_connection_instance = None


def get_click_connection() -> GinkgoClickhouse:
    """获取ClickHouse连接（向后兼容）"""
    return _connection_manager.get_clickhouse_connection()


@retry(max_try=3)
@time_logger
def create_click_connection() -> GinkgoClickhouse:
    """创建ClickHouse连接实例"""
    try:
        conn = GinkgoClickhouse(
            user=GCONF.CLICKUSER,
            pwd=GCONF.CLICKPWD,
            host=GCONF.CLICKHOST,
            port=GCONF.CLICKPORT,
            db=GCONF.CLICKDB,
        )

        # 验证连接健康状态
        if not conn.health_check():
            raise RuntimeError("ClickHouse connection health check failed")

        GLOG.DEBUG("ClickHouse connection created successfully")
        return conn

    except Exception as e:
        GLOG.ERROR(f"Failed to create ClickHouse connection: {e}")
        raise


def get_mysql_connection() -> GinkgoMysql:
    """获取MySQL连接（向后兼容）"""
    return _connection_manager.get_mysql_connection()


@retry(max_try=3)
@time_logger
def create_mysql_connection() -> GinkgoMysql:
    """创建MySQL连接实例"""
    try:
        conn = GinkgoMysql(
            user=GCONF.MYSQLUSER,
            pwd=GCONF.MYSQLPWD,
            host=GCONF.MYSQLHOST,
            port=GCONF.MYSQLPORT,
            db=GCONF.MYSQLDB,
        )

        # 验证连接健康状态
        if not conn.health_check():
            raise RuntimeError("MySQL connection health check failed")

        GLOG.DEBUG("MySQL connection created successfully")
        return conn

    except Exception as e:
        GLOG.ERROR(f"Failed to create MySQL connection: {e}")
        raise


@retry(max_try=3)
@time_logger
def create_mongo_connection() -> GinkgoMongo:
    """创建MongoDB连接实例"""
    try:
        conn = GinkgoMongo(
            user=GCONF.MONGOUSER,
            pwd=GCONF.MONGOPWD,
            host=GCONF.MONGOHOST,
            port=int(GCONF.MONGOPORT),
            db=GCONF.MONGODB,
        )

        # 验证连接健康状态
        if not conn.health_check():
            raise RuntimeError("MongoDB connection health check failed")

        GLOG.DEBUG("MongoDB connection created successfully")
        return conn

    except Exception as e:
        GLOG.ERROR(f"Failed to create MongoDB connection: {e}")
        raise


def get_db_connection(value):
    if isinstance(value, type):
        if issubclass(value, MClickBase):
            return get_click_connection()
        elif issubclass(value, MMysqlBase):
            return get_mysql_connection()
        elif issubclass(value, MMongoBase):
            return _connection_manager.get_mongo_connection()
    else:
        if isinstance(value, MClickBase):
            return get_click_connection()
        elif isinstance(value, MMysqlBase):
            return get_mysql_connection()
        elif isinstance(value, MMongoBase):
            return _connection_manager.get_mongo_connection()

    GLOG.CRITICAL(f"Model {value} should be sub of MClickBase, MMysqlBase or MMongoBase.")


def create_redis_connection() -> GinkgoRedis:
    return GinkgoRedis(GCONF.REDISHOST, GCONF.REDISPORT).redis


@retry(max_try=5)
@time_logger
def add(value, *args, **kwargs) -> any:
    """
    Add a single data item.
    Args:
        value(Model): Data Model
    Returns:
        Added model with updated fields
    """
    if not isinstance(value, (MClickBase, MMysqlBase)):
        GLOG.ERROR(f"Can not add {value} to database.")
        return

    GLOG.DEBUG("Try add data to session.")
    conn = get_db_connection(value)

    # 使用上下文管理器改进会话管理
    try:
        with conn.get_session() as session:
            session.add(value)
            session.flush()  # 获取数据库生成的ID等信息
            session.refresh(value)  # 确保所有属性都被加载
            session.expunge(value)  # 将对象从session中分离，但保留属性
            # 上下文管理器会在退出时自动commit
            return value
    except Exception as e:
        GLOG.ERROR(f"Failed to add data to database: {e}")
        raise


@time_logger
@retry(max_try=5)
def add_all(values: List[Any], *args, **kwargs) -> None:
    """
    Add multi data into session.
    Args:
        values(Model): multi data models
    Returns:
        None
    """
    GLOG.DEBUG(f"Try add {len(values)} multi data to session.")

    click_list = []
    click_count = 0
    mysql_list = []
    mysql_count = 0
    for i in values:
        if isinstance(i, MClickBase):
            click_list.append(i)
        elif isinstance(i, MMysqlBase):
            mysql_list.append(i)
        else:
            GLOG.DEBUG(f"Just support clickhouse and mysql now. Ignore other type: {type(i)}")

    if len(click_list) > 0:
        try:
            click_conn = get_click_connection()

            # 使用上下文管理器改进会话管理
            with click_conn.get_session() as session:
                # 使用bulk_insert_mappings提高ClickHouse插入性能
                if click_list:
                    # 按模型类型分组进行批量插入
                    model_groups = {}
                    for item in click_list:
                        model_type = type(item)
                        if model_type not in model_groups:
                            model_groups[model_type] = []
                        model_groups[model_type].append(item)

                    # 为每个模型类型执行批量插入
                    for model_type, items in model_groups.items():
                        try:
                            # 将对象转换为字典
                            mappings = []
                            for item in items:
                                mapping = {}
                                for column in item.__table__.columns:
                                    mapping[column.name] = getattr(item, column.name)
                                mappings.append(mapping)

                            # 执行批量插入
                            session.bulk_insert_mappings(model_type, mappings)
                            GLOG.DEBUG(f"ClickHouse bulk inserted {len(mappings)} {model_type.__name__} records")

                        except Exception as bulk_error:
                            GLOG.WARN(
                                f"ClickHouse bulk insert failed for {model_type.__name__}, falling back to add_all: {bulk_error}"
                            )
                            # 回退到add_all方法
                            session.add_all(items)

                click_count = len(click_list)
                GLOG.DEBUG(f"Clickhouse committed {len(click_list)} records total.")

        except Exception as e:
            GLOG.ERROR(f"ClickHouse batch operation failed: {e}")
            click_count = 0

    if len(mysql_list) > 0:
        try:
            mysql_conn = get_mysql_connection()

            # 使用上下文管理器改进会话管理，支持对象解绑
            with mysql_conn.get_session() as session:
                session.add_all(mysql_list)
                mysql_count = len(mysql_list)
                # 上下文管理器会在退出时自动commit
                GLOG.DEBUG(f"MySQL will commit {len(mysql_list)} records.")

                # 在session关闭前进行批量解绑，创建干净的脱管对象
                # 常见做法：flush确保状态完整，expunge_all批量脱管
                session.flush()          # 确保最新状态写入数据库
                session.expunge_all()    # 批量脱管所有ORM实例

        except Exception as e:
            GLOG.ERROR(f"MySQL batch operation failed: {e}")
            mysql_count = 0

    return (click_count, mysql_count)


def is_table_exists(model) -> bool:
    """
    Check the whether the table exists in the database.
    Auto choose the database driver.
    Args:
        model(Model): model in sqlalchemy
    Returns:
        Whether the table exist
    """
    driver = get_db_connection(model)
    table_name = model.__tablename__
    inspector = inspect(driver.engine)
    return table_name in inspector.get_table_names()


@retry
@skip_if_ran
def create_table(model, no_log=True) -> None:
    """
    Create table with model.
    Support Clickhouse and Mysql now.
    Args:
        model(Model): model in sqlalchemy
    Returns:
        None
    """
    if model.__abstract__ == True:
        GLOG.DEBUG(f"Pass Model:{model}")
        return

    driver = get_db_connection(model)
    if driver is None:
        GLOG.ERROR(f"Can not get driver for {model}.")
        raise ValueError(f"Can not get driver for model {model}.")
    try:
        if is_table_exists(model):
            GLOG.DEBUG(f"No need to create {model.__tablename__} : {model}")
        else:
            model.metadata.create_all(driver.engine)
            GLOG.INFO(f"Create Table {model.__tablename__} : {model}")
    except Exception as e:
        driver.session.rollback()
        GLOG.ERROR(e)
    finally:
        driver.remove_session()


@time_logger
@retry
def drop_table(model, *args, **kwargs) -> None:
    """
    Drop table from Database.
    Support Clickhouse and Mysql now.
    Args:
        model(Model): model in sqlalchemy
    Returns:
        None
    """

    driver = get_db_connection(model)
    if driver is None:
        GLOG.ERROR(f"Can not get driver for {model}.")
        raise ValueError(f"Can not get driver for model {model}.")
    try:
        if is_table_exists(model):
            model.__table__.drop(driver.engine)
            # model.metadata.drop_all(driver.engine)
            GLOG.WARN(f"Drop Table {model.__tablename__} : {model}")
        else:
            GLOG.DEBUG(f"No need to drop {model.__tablename__} : {model}")
    except Exception as e:
        GLOG.ERROR(e)
        driver.session.rollback()
    finally:
        driver.remove_session()


@time_logger
@retry
def create_all_tables() -> None:
    """
    Create tables with all models without __abstract__ = True.

    NOTE: 导入 models 包以触发所有模型的导入和注册到 SQLAlchemy metadata。
    所有继承自 MClickBase 和 MMysqlBase 且 __abstract__ != True 的模型都会被创建。
    所有继承自 MMongoBase 的模型会创建 MongoDB 集合和索引。
    Args:
        None
    Returns:
        None
    """
    # 导入 models 包，触发所有子模块的导入，使模型类注册到 metadata
    import ginkgo.data.models

    # Create Tables in clickhouse
    MClickBase.metadata.create_all(get_click_connection().engine)
    # Create Tables in mysql
    MMysqlBase.metadata.create_all(get_mysql_connection().engine)

    # Create MongoDB collections and indexes
    _create_mongo_collections()

    GLOG.INFO(f"Create all tables.")


def _create_mongo_collections() -> None:
    """
    创建所有 MongoDB 集合和索引

    遍历所有继承自 MMongoBase 的模型类，创建对应的集合和索引。

    Returns:
        None
    """
    try:
        # 获取 MongoDB 连接
        mongo_conn = _connection_manager.get_mongo_connection()
        db = mongo_conn.database

        # 导入所有模型以触发模型注册
        import ginkgo.data.models as models_module
        import inspect

        created_collections = []
        created_indexes = []

        # 遍历 models 模块中的所有类
        for name, obj in inspect.getmembers(models_module):
            if inspect.isclass(obj) and issubclass(obj, MMongoBase) and obj != MMongoBase:
                try:
                    collection_name = obj.get_collection_name()

                    # 检查集合是否已存在
                    if not mongo_conn.is_collection_exists(collection_name):
                        # 创建集合（MongoDB 会自动创建集合，但我们可以显式创建）
                        db.create_collection(collection_name)
                        created_collections.append(collection_name)
                        GLOG.INFO(f"Created MongoDB collection: {collection_name}")
                    else:
                        GLOG.DEBUG(f"MongoDB collection already exists: {collection_name}")

                    # 创建索引（如果模型定义了）
                    collection = db[collection_name]

                    # 默认索引：uuid 字段唯一索引
                    try:
                        collection.create_index([("uuid", 1)], unique=True)
                        created_indexes.append(f"{collection_name}.uuid")
                    except Exception as idx_err:
                        GLOG.WARN(f"Failed to create uuid index for {collection_name}: {idx_err}")

                    # TTL 索引：通知记录 7 天后自动删除
                    if "notification_record" in collection_name.lower():
                        try:
                            # create_at + 7*24*3600 秒后自动删除
                            collection.create_index(
                                [("create_at", 1)],
                                expireAfterSeconds=7 * 24 * 3600,
                                name="ttl_auto_delete"
                            )
                            created_indexes.append(f"{collection_name}.ttl")
                            GLOG.INFO(f"Created TTL index for {collection_name}")
                        except Exception as ttl_err:
                            GLOG.WARN(f"Failed to create TTL index for {collection_name}: {ttl_err}")

                except Exception as e:
                    GLOG.WARN(f"Failed to create collection/index for {name}: {e}")

        if created_collections:
            GLOG.INFO(f"Created {len(created_collections)} MongoDB collections: {created_collections}")
        if created_indexes:
            GLOG.INFO(f"Created {len(created_indexes)} MongoDB indexes")

    except Exception as e:
        GLOG.ERROR(f"Failed to create MongoDB collections: {e}")
        # 不抛出异常，允许系统在没有 MongoDB 的情况下启动（优雅降级）


def drop_all_tables() -> None:
    """
    ATTENTION!!
    Just call the func in dev.
    This will drop all the tables in models.
    Args:
        None
    Returns:
        None
    """
    # Drop Tables in clickhouse
    MClickBase.metadata.reflect(get_click_connection().engine)
    MClickBase.metadata.drop_all(get_click_connection().engine)
    # Drop Tables in mysql
    MMysqlBase.metadata.reflect(get_mysql_connection().engine)
    MMysqlBase.metadata.drop_all(get_mysql_connection().engine)
    GLOG.DEBUG(f"Drop all tables.")


def get_table_size(model, *args, **kwargs) -> int:
    """
    Get the size of table.
    Support Clickhouse and Mysql now.
    Args:
        model(Model): model in sqlalchemy
    Returns:
        Size of table in database
    """
    driver = get_db_connection(model)
    count = driver.session.scalar(select(func.count()).select_from(model))
    return count


def get_connection_status() -> dict:
    """获取所有数据库连接状态"""
    return _connection_manager.get_connection_status()


__all__ = [
    "DatabaseDriverBase",
    "GinkgoClickhouse",
    "GinkgoMongo",
    "GinkgoMysql",
    "GinkgoRedis",
    "GinkgoProducer",
    "GinkgoConsumer",
    "ConnectionManager",
    "get_db_connection",
    "get_mysql_connection",
    "get_click_connection",
    "create_mysql_connection",
    "create_click_connection",
    "create_mongo_connection",
    "create_redis_connection",
    "get_connection_status",
    "kafka_topic_llen",
    "add",
    "add_all",
    "is_table_exists",
    "create_table",
    "drop_table",
    "create_all_tables",
    "drop_all_tables",
    "get_table_size",
]
