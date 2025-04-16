import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import FILE_TYPES
from ginkgo.data.models import MFile
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG


def add_file(type: FILE_TYPES, name: str, data: bytes, *args, **kwargs) -> MFile:
    item = MFile(type=type, name=name, data=data)
    res = add(item)
    get_mysql_connection().remove_session()
    return res


def add_files(files: List[MFile], *args, **kwargs):
    l = []
    for i in files:
        if isinstance(i, MFile):
            l.append(i)
        else:
            GLOG.WANR("add files only support file data.")
    return add_all(l)


def upsert_file():
    pass


def upsert_files():
    pass


def delete_file(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MFile
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord: id {id} has more than one record.")
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


def delete_files(ids: List[str], *argss, **kwargs):
    session = get_mysql_connection().session
    model = MFile
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


def softdelete_file(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MFile
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


def update_file(
    id: str,
    type: Optional[FILE_TYPES] = None,
    name: Optional[str] = None,
    data: Optional[bytes] = None,
    *argss,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MFile
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if type is not None:
        updates["type"] = type
    if name is not None:
        updates["name"] = name
    if data is not None:
        updates["data"] = data
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_file(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MFile
    filters = [model.uuid == id]
    try:
        stmt = session.query(model).filter(and_(*filters))
        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] > 0:
            return df.iloc[0]
        else:
            return pd.DataFrame()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()


def get_file_content(id: str, *args, **kwargs) -> bytes:
    session = get_mysql_connection().session
    model = MFile
    filters = [model.uuid == id]
    try:
        stmt = session.query(model).filter(and_(*filters))
        res = session.execute(stmt).scalars().first()
        return res.data if res else b""
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return b""
    finally:
        get_mysql_connection().remove_session()


def get_files(
    type: Optional[FILE_TYPES] = None,
    name: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MFile
    filters = [model.is_del == False]

    if type is not None:
        filters.append(model.type == type)

    if name is not None:
        filters.append(model.name.like(f"%{name}%"))

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
