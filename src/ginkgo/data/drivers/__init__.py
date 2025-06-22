import time
import datetime


from typing import List, Optional, Union, Any
from sqlalchemy import inspect, select, func


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
from ginkgo.libs import try_wait_counter, GLOG, GCONF, time_logger, retry, skip_if_ran

max_try = 5


def get_click_connection() -> GinkgoClickhouse:
    return create_click_connection()


def create_click_connection() -> GinkgoClickhouse:
    return GinkgoClickhouse(
        user=GCONF.CLICKUSER,
        pwd=GCONF.CLICKPWD,
        host=GCONF.CLICKHOST,
        port=GCONF.CLICKPORT,
        db=GCONF.CLICKDB,
    )


def get_mysql_connection() -> GinkgoMysql:
    return create_mysql_connection()


def create_mysql_connection() -> GinkgoMysql:
    return GinkgoMysql(
        user=GCONF.MYSQLUSER,
        pwd=GCONF.MYSQLPWD,
        host=GCONF.MYSQLHOST,
        port=GCONF.MYSQLPORT,
        db=GCONF.MYSQLDB,
    )


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
def add(value, *args, **kwargs) -> any:
    """
    Add a single data item.
    Args:
        value(Model): Data Model
    Returns:
        None
    """
    if not isinstance(value, (MClickBase, MMysqlBase)):
        GLOG.ERROR(f"Can not add {value} to database.")
        return
    GLOG.DEBUG("Try add data to session.")
    conn = get_db_connection(value)
    try:
        session = conn.session
        session.add(value)
        session.commit()
        session.refresh(value)
        return value
    except Exception as e:
        print(e)
        conn.session.rollback()
    finally:
        conn.remove_session()


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
            GLOG.WARN("Just support clickhouse and mysql now. Ignore other type.")

    if len(click_list) > 0:
        try:
            click_conn = get_click_connection()
            session = click_conn.session
            session.add_all(click_list)
            session.commit()
            click_count = len(click_list)
            GLOG.DEBUG(f"Clickhouse commit {len(click_list)} records.")
        except Exception as e:
            session.rollback()
            GLOG.ERROR(e)
        finally:
            click_conn.remove_session()

    if len(mysql_list) > 0:
        try:
            mysql_conn = get_mysql_connection()
            session = mysql_conn.session
            session.add_all(mysql_list)
            session.commit()
            mysql_count = len(mysql_list)
            GLOG.DEBUG(f"Mysql commit {len(mysql_list)} records.")
        except Exception as e:
            session.rollback()
            GLOG.ERROR(e)
            mysql_connection = create_mysql_connection()
        finally:
            mysql_conn.remove_session()

    return (click_count, mysql_count)


def is_table_exsists(model) -> bool:
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
        raise ValueException(f"Can not get driver for model {model}.")
    try:
        if is_table_exsists(model):
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
def drop_table(model) -> None:
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
        raise ValueException(f"Can not get driver for model {model}.")
    try:
        if is_table_exsists(model):
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


__all__ = [
    "GinkgoClickhouse",
    "GinkgoMongo",
    "GinkgoMysql",
    "GinkgoRedis",
    "GinkgoProducer",
    "GinkgoConsumer",
    "get_db_connection",
    "get_mysql_connection",
    "get_click_connection",
    "create_mysql_connection",
    "create_click_connection",
    "create_redis_connection",
    "kafka_topic_llen",
    "add",
    "add_all",
    "is_table_exsists",
    "create_table",
    "drop_table",
    "create_all_tables",
    "drop_all_tables",
    "get_table_size",
]
