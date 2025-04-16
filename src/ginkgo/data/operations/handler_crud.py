import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.data.models import MHandler
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG
from ginkgo.enums import EVENT_TYPES


def add_handler(name: str, lib_path: str, func_name: str, *args, **kwargs) -> pd.Series:
    item = MHandler(name=name, lib_path=lib_path, func_name=func_name)
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_handlers(handlers: List[MHandler], *args, **kwargs):
    l = []
    for i in handlers:
        if isinstance(i, MHandler):
            l.append(i)
        else:
            GLOG.WANR("add handlers only support handler data.")
    return add_all(l)


def upsert_handler():
    pass


def upsert_handlers():
    pass


def delete_handler(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MHandler
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_handler(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MHandler
    filters = [model.uuid == id]
    updates = {"is_del": True, "update_at": datetime.datetime.now()}
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def update_handler(
    id: str,
    name: Optional[str] = None,
    lib_path: Optional[str] = None,
    func_name: Optional[str] = None,
    *argss,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MHandler
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if name is not None:
        updates["name"] = name
    if lib_path is not None:
        updates["lib_path"] = lib_path
    if func_name is not None:
        updates["func_name"] = func_name
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_handler(
    id: str = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MHandler
    filters = []
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        return df
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()


def get_handlers(
    type: EVENT_TYPES = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MHandler
    filters = [model.is_del == False]
    if type is not None:
        filters.append(model.type == type)

    try:
        stmt = session.query(model).filter(and_(*filters))
        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()
