import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.data.models import MParam
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG


def add_param(mapping_id: str, index: int, value: str, *args, **kwargs) -> pd.Series:
    item = MParam(mapping_id=mapping_id, index=index, value=value)
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_params(handlers: List[MParam], *args, **kwargs):
    l = []
    for i in handlers:
        if isinstance(i, MParam):
            l.append(i)
        else:
            GLOG.WANR("add handlers only support handler data.")
    return add_all(l)


def upsert_param():
    pass


def upsert_params():
    pass


def delete_param(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MParam
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


def softdelete_param(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MParam
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


def delete_params(mapping_id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MParam
    filters = [model.mapping_id == mapping_id]
    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_params(mapping_id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MParam
    filters = [model.mapping_id == id]
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


def update_param(
    id: str,
    mapping_id: Optional[str] = None,
    index: Optional[int] = None,
    value: Optional[str] = None,
    *argss,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MParam
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if mapping_id is not None:
        updates["mapping_id"] = mapping_id
    if index is not None:
        updates["index"] = index
    if value is not None:
        updates["value"] = value
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_param(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MParam
    filters = [model.uuid == id, model.is_del == False]

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


def get_params(
    mapping_id: str = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MParam
    if mapping_id is not None:
        filters = [model.mapping_id == mapping_id, model.is_del == False]
    else:
        filters = []

    try:
        stmt = session.query(model).filter(and_(*filters))

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
