import pandas as pd
import datetime
from typing import List, Optional, Union
from sqlalchemy import and_, delete, update, select

from ginkgo.enums import SOURCE_TYPES
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.data.models import MAdjustfactor
from ginkgo.libs import datetime_normalize
from ginkgo.libs import GLOG


def add_adjustfactor(
    timestamp: any,
    code: str,
    foreadjustfactor: float,
    backadjustfactor: float,
    adjustfactor: float,
    source=SOURCE_TYPES.TUSHARE,
    *args,
    **kwargs,
) -> pd.DataFrame:
    item = MAdjustfactor(
        timestamp=datetime_normalize(timestamp),
        code=code,
        foreadjustfactor=foreadjustfactor,
        backadjustfactor=backadjustfactor,
        adjustfactor=adjustfactor,
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_adjustfactors(adjustfactors: List[MAdjustfactor], *args, **kwargs) -> None:
    l = []
    for i in adjustfactors:
        if isinstance(i, MAdjustfactor):
            l.append(i)
        else:
            GLOG.WARN("add adjustfactors only support model_adjustfactor.")
    return add_all(l)


def delete_adjustfactor_by_id(id: str, *args, **kwargs) -> int:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_adjustfactor_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_adjustfactor_by_id(id: str, *args, **kwargs) -> None:
    model = MAdjustfactor
    filters = [model.uuid == id]
    try:
        session = get_mysql_connection().session
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_adjustfactor_by_id: id {id} has more than one record.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def delete_adjustfactor_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    model = MAdjustfactor
    filters = [model.code == code]
    if start_date is not None:
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        filters.append(model.timestamp <= end_date)
    session = get_mysql_connection().session
    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_adjustfactor_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    model = MAdjustfactor
    filters = [model.code == code]
    if start_date is not None:
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        filters.append(model.timestamp <= end_date)
    session = get_mysql_connection().session
    updates = {"is_del": True}
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def update_adjustfactor_by_id(
    id: str,
    code: str = None,
    foreadjustfactor: float = None,
    backadjustfactor: float = None,
    adjustfactor: float = None,
    timestamp: any = None,
    *args,
    **kwargs,
) -> None:
    model = MAdjustfactor
    filters = [model.uuid == id]
    session = get_mysql_connection().session
    updates = {}
    if code is not None:
        updates["code"] = code
    if foreadjustfactor is not None:
        updates["foreadjustfactor"] = foreadjustfactor
    if backadjustfactor is not None:
        updates["backadjustfactor"] = backadjustfactor
    if adjustfactor is not None:
        updates["adjustfactor"] = adjustfactor
    if timestamp is not None:
        updates["timestamp"] = datetime_normalize(timestamp)

    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def update_adjustfactor_by_code_and_date_range(
    code: str,
    start_date: any,
    end_date: any,
    foreadjustfactor: float = None,
    backadjustfactor: float = None,
    adjustfactor: float = None,
    timestamp: any = None,
    *args,
    **kwargs,
) -> None:
    model = MAdjustfactor
    filters = [model.code == code]
    start_date = datetime_normalize(start_date)
    filters.append(model.timestamp >= start_date)
    end_date = datetime_normalize(end_date)
    filters.append(model.timestamp <= end_date)

    session = get_mysql_connection().session
    updates = {}
    if foreadjustfactor is not None:
        updates["foreadjustfactor"] = foreadjustfactor
    if backadjustfactor is not None:
        updates["backadjustfactor"] = backadjustfactor
    if adjustfactor is not None:
        updates["adjustfactor"] = adjustfactor
    if timestamp is not None:
        updates["timestamp"] = datetime_normalize(timestamp)

    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_adjustfactor_by_id(id: str, *args, **kwargs) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MAdjustfactor
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


def get_adjustfactor_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.code == code, model.is_del == False]

    if start_date is not None:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date is not None:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        # stmt = select(model).where(and_(*filters))
        stmt = session.query(model).filter(and_(*filters))

        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)

        df = pd.read_sql(stmt.statement, session.connection())
        return df

    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()
