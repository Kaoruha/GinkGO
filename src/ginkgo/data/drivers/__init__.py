import time


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
from ginkgo.libs import try_wait_counter, GLOG, GCONF

mysql_connection = None
click_connection = None
redis_connection = None
max_try = 5


def get_click_connection() -> GinkgoClickhouse:
    global click_connection
    if click_connection is None:
        click_connection = create_click_connection()
    return click_connection


def create_click_connection() -> GinkgoClickhouse:
    return GinkgoClickhouse(
        user=GCONF.CLICKUSER,
        pwd=GCONF.CLICKPWD,
        host=GCONF.CLICKHOST,
        port=GCONF.CLICKPORT,
        db=GCONF.CLICKDB,
    )


def get_mysql_connection() -> GinkgoMysql:
    global mysql_connection
    if mysql_connection is None:
        mysql_connection = create_mysql_connection()
    return mysql_connection


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


def create_redis_connection(self) -> GinkgoRedis:
    return GinkgoRedis(GCONF.REDISHOST, GCONF.REDISPORT).redis


def create_kafka_producer_driver(self) -> GinkgoProducer:
    return GinkgoProducer()


def add(value, max_try: int = 5, *args, **kwargs) -> any:
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
    for i in range(max_try):
        conn = get_db_connection(value)
        try:
            session = conn.session
            session.add(value)
            session.commit()
            return value
        except Exception as e:
            print(e)
            conn.session.rollback()
            GLOG.CRITICAL(f"{type(value)} add failed {i+1}/{max_try}")
        finally:
            pass
            # conn.remove_session()


def add_all(values: List[Any], max_try: int = 5, *args, **kwargs) -> tuple[int, int]:
    """
    Add multi data into session.
    Args:
        values(Model): multi data models
    Returns:
        None
    """
    global mysql_connection, click_connection
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

    for i in range(max_try):
        try:
            if len(click_list) > 0:
                session = get_click_connection().session
                session.add_all(click_list)
                session.commit()
                click_count = len(click_list)
                GLOG.DEBUG(f"Clickhouse commit {len(click_list)} records.")
                break
        except Exception as e:
            session.rollback()
            GLOG.CRITICAL(f"ClickHouse add failed {i+1}/{max_try}")
            print(e)
        finally:
            pass
            # click_d.remove_session()

    for i in range(max_try):
        try:
            if len(mysql_list) > 0:
                session = get_mysql_connection().session
                session.add_all(mysql_list)
                session.commit()
                mysql_count = len(mysql_list)
                GLOG.DEBUG(f"Mysql commit {len(mysql_list)} records.")
        except Exception as e:
            session.rollback()
            GLOG.CRITICAL(f"Mysql add failed {i+1}/{self.max_try}")
        finally:
            pass
            # mysql_d.remove_session()

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


def create_table(model) -> None:
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

    for i in range(max_try):
        driver = get_db_connection(model)
        if driver is None:
            GLOG.ERROR(f"Can not get driver for {model}.")
            GLOG.WARN(f"{type(model)} create table failed {i+1}/{max_try}")
            continue
        try:
            if is_table_exsists(model):
                GLOG.DEBUG(f"No need to drop {model.__tablename__} : {model}")
            else:
                model.metadata.create_all(driver.engine)
                GLOG.DEBUG(f"Create Table {model.__tablename__} : {model}")
            return
        except Exception as e:
            GLOG.ERROR(e)
            driver.session.rollback()
            GLOG.WARN(f"{type(model)} drop table failed {i+1}/{max_try}")
            time.sleep(try_wait_counter(i))
        finally:
            driver.remove_session()


def drop_table(model) -> None:
    """
    Drop table from Database.
    Support Clickhouse and Mysql now.
    Args:
        model(Model): model in sqlalchemy
    Returns:
        None
    """

    for i in range(max_try):
        driver = get_db_connection(model)
        if driver is None:
            GLOG.ERROR(f"Can not get driver for {model}.")
            GLOG.WARN(f"{type(model)} drop table failed {i+1}/{max_try}")
            continue
        try:
            if is_table_exsists(model):
                model.metadata.drop_all(driver.engine)
                GLOG.DEBUG(f"Drop Table {model.__tablename__} : {model}")
            else:
                GLOG.DEBUG(f"No need to drop {model.__tablename__} : {model}")
            return
        except Exception as e:
            GLOG.ERROR(e)
            driver.session.rollback()
            GLOG.WARN(f"{type(model)} drop table failed {i+1}/{max_try}")
            time.sleep(try_wait_counter(i))
        finally:
            driver.remove_session()


def create_all_tables() -> None:
    """
    Create tables with all models without __abstract__ = True.
    Args:
        None
    Returns:
        None
    """
    global click_connection
    global mysql_connection
    # Create Tables in clickhouse
    MClickBase.metadata.create_all(click_connection.engine)
    # Create Tables in mysql
    MMysqlBase.metadata.create_all(mysql_connection.engine)
    GLOG.DEBUG(f"Create all tables.")


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
    global click_connection
    global mysql_connection
    # Drop Tables in clickhouse
    MClickBase.metadata.drop_all(click_connection.engine)
    # Drop Tables in mysql
    MMysqlBase.metadata.drop_all(mysql_connection.engine)
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
    "create_kafka_producer_driver",
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
