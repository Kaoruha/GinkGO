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
from ginkgo.data.drivers.ginkgo_kafka import (
    GinkgoProducer,
    GinkgoConsumer,
    kafka_topic_llen,
)
from ginkgo.data.models import MClickBase, MMysqlBase
from ginkgo.libs import try_wait_counter, GLOG, GCONF, time_logger, retry, skip_if_ran, cache_with_expiration

max_try = 5


class ConnectionManager:
    """统一的数据库连接管理器"""

    def __init__(self):
        self._mysql_conn = None
        self._click_conn = None
        self._lock = threading.Lock()

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


def get_db_connection(value):
    if isinstance(value, type):
        if issubclass(value, MClickBase):
            return get_click_connection()
        elif issubclass(value, MMysqlBase):
            return get_mysql_connection()
    else:
        if isinstance(value, MClickBase):
            return get_click_connection()
        elif isinstance(value, MMysqlBase):
            return get_mysql_connection()

    GLOG.CRITICAL(f"Model {value} should be sub of clickbase or mysqlbase.")


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
    GLOG.DEBUG("Try add multi data to session.")
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
            GLOG.DEBUG("Just support clickhouse and mysql now. Ignore other type.")

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
                GLOG.DEBUG(f"MySQL committed {len(mysql_list)} records.")

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
    Args:
        None
    Returns:
        None
    """
    # Create Tables in clickhouse
    MClickBase.metadata.create_all(get_click_connection().engine)
    # Create Tables in mysql
    MMysqlBase.metadata.create_all(get_mysql_connection().engine)
    GLOG.INFO(f"Create all tables.")


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
