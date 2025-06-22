import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.data.models import MEngine
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG
from ginkgo.enums import ENGINE_STATUS


def add_engine(name: str, is_live: bool, *args, **kwargs) -> pd.Series:
    item = MEngine(name=name, is_live=is_live, status=ENGINE_STATUS.IDLE)
    res = add(item)
    if res is None:
        get_mysql_connection().remove_session()
        return
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_engines(files: List[MEngine], *args, **kwargs):
    l = []
    for i in files:
        if isinstance(i, MEngine):
            l.append(i)
        else:
            GLOG.WANR("add files only support file data.")
    # TODO Might have bugs.
    return add_all(l)


def upsert_engine():
    pass


def upsert_engines():
    pass


def delete_engine(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MEngine
    try:
        filters = [model.uuid == id]
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_engine: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
        return len(query)
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return
    finally:
        get_mysql_connection().remove_session()


def delete_engines(ids: List[str], *argss, **kwargs):
    session = get_mysql_connection().session
    model = MEngine
    filters = []
    filters.append(model.uuid.in_(ids))
    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_engine(id: str, *argss, **kwargs):
    model = MEngine
    filters = [model.uuid == id]
    session = get_mysql_connection().session
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


def update_engine(
    id: str,
    name: Optional[str] = None,
    status: Optional[ENGINE_STATUS] = None,
    is_live: Optional[bool] = None,
    *argss,
    **kwargs,
):
    model = MEngine
    filters = [model.uuid == id]
    session = get_mysql_connection().session
    updates = {"update_at": datetime.datetime.now()}
    if name is not None:
        updates["name"] = name
    if status is not None:
        updates["status"] = status
    if is_live is not None:
        updates["is_live"] = is_live
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_engine(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MEngine
    filters = [model.is_del == False]
    if id is not None:
        filters.append(model.uuid == id)
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


def get_engines_page_filtered(
    name: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MEngine
    filters = [model.is_del == False]
    if name is not None:
        filters.append(model.name.like(f"%{name}%"))
    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df.sort_values(by="update_at", ascending=False)
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()
