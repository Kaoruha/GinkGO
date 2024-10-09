import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union

from ginkgo.data.models import MHandlerParam
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG


def add_handler_param(handler_id: str, index: int, value: str, *args, **kwargs) -> pd.Series:
    item = MHandlerParam(handler_id=handler_id, index=index, value=value)
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_handler_params(handlers: List[MHandlerParam], *args, **kwargs):
    l = []
    for i in handlers:
        if isinstance(i, MHandlerParam):
            l.append(i)
        else:
            GLOG.WANR("add handlers only support handler data.")
    return add_all(l)


def delete_handler_param(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MHandlerParam
    try:
        filters = [model.uuid == id]
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_handler_param(id: str, *argss, **kwargs):
    model = MHandlerParam
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


def delete_handler_params(handler_id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MHandlerParam
    try:
        filters = [model.handler_id == id]
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_handler_params(handler_id: str, *argss, **kwargs):
    model = MHandlerParam
    filters = [model.handler_id == id]
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


def update_handler_param(
    id: str,
    handler_id: Optional[str] = None,
    index: Optional[int] = None,
    value: Optional[str] = None,
    *argss,
    **kwargs,
):
    model = MHandlerParam
    filters = [model.uuid == id]
    session = get_mysql_connection().session
    updates = {"update_at": datetime.datetime.now()}
    if handler_id is not None:
        updates["handler_id"] = handler_id
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


def get_handler_param_by_id(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MHandlerParam
    filters = [model.uuid == id, model.is_del == False]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df.iloc[0]
    except Exception as e:
        session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        get_mysql_connection().remove_session()


def get_handler_params(
    handler_id: str,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MHandlerParam
    filters = [model.handler_id == handler_id, model.is_del == False]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df
    except Exception as e:
        session.rollback()
        print(e)
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()
