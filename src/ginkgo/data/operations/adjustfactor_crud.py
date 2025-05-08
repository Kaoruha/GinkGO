import pandas as pd
import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import and_, delete, update, select

from ginkgo.enums import SOURCE_TYPES
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.data.models import MAdjustfactor
from ginkgo.libs import datetime_normalize, Number, to_decimal
from ginkgo.libs import GLOG


def add_adjustfactor(
    timestamp: any,
    code: str,
    foreadjustfactor: Number,
    backadjustfactor: Number,
    adjustfactor: Number,
    source=SOURCE_TYPES.TUSHARE,
    *args,
    **kwargs,
) -> pd.Series:
    item = MAdjustfactor(
        timestamp=datetime_normalize(timestamp),
        code=code,
        foreadjustfactor=to_decimal(foreadjustfactor),
        backadjustfactor=to_decimal(backadjustfactor),
        adjustfactor=to_decimal(adjustfactor),
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


def upsert_adjustfactor() -> pd.Series:
    pass


def upsert_adjustfactors() -> pd.Series:
    pass


def delete_adjustfactor(id: str, *args, **kwargs) -> int:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_adjustfactor: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_adjustfactor(id: str, *args, **kwargs) -> None:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_adjustfactor: id {id} has more than one record.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def delete_adjustfactors_filtered(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.code == code]
    if start_date is not None:
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        filters.append(model.timestamp <= end_date)
    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_adjustfactors_filtered(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.code == code]
    if start_date is not None:
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        filters.append(model.timestamp <= end_date)

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


def update_adjustfactor(
    id: str,
    code: str = None,
    foreadjustfactor: Number = None,
    backadjustfactor: Number = None,
    adjustfactor: Number = None,
    timestamp: any = None,
    *args,
    **kwargs,
) -> None:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.uuid == id]
    updates = {}
    if code is not None:
        updates["code"] = code
    if foreadjustfactor is not None:
        updates["foreadjustfactor"] = to_decimal(foreadjustfactor)
    if backadjustfactor is not None:
        updates["backadjustfactor"] = to_decimal(backadjustfactor)
    if adjustfactor is not None:
        updates["adjustfactor"] = to_decimal(adjustfactor)
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


def update_adjustfactors_filtered(
    code: str,
    start_date: any,
    end_date: any,
    foreadjustfactor: Number = None,
    backadjustfactor: Number = None,
    adjustfactor: Number = None,
    timestamp: any = None,
    *args,
    **kwargs,
) -> None:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.code == code]
    filters.append(model.timestamp >= datetime_normalize(start_date))
    filters.append(model.timestamp <= datetime_normalize(end_date))

    updates = {}
    if foreadjustfactor is not None:
        updates["foreadjustfactor"] = to_decimal(foreadjustfactor)
    if backadjustfactor is not None:
        updates["backadjustfactor"] = to_decimal(backadjustfactor)
    if adjustfactor is not None:
        updates["adjustfactor"] = to_decimal(adjustfactor)
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


def get_adjustfactor(id: str, as_dataframe: bool = True, *args, **kwargs) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.uuid == id, model.is_del == False]

    try:
        stmt = session.query(model).filter(and_(*filters))
        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            res = session.execute(stmt).scalars().first()
            if res is not None:
                session.refresh(res)
            return Adjustactor(
                code=res.code,
                timestamp=res.timestamp,
                fore_adjustfactor=res.foreadjustfactor,
                back_adjustfactor=res.backadjustfactor,
                adjustfactor=res.adjustfactor,
            )
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_mysql_connection().remove_session()


def get_adjustfactors_page_filtered(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = True,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MAdjustfactor
    filters = [model.code == code, model.is_del == False]

    if start_date is not None:
        filters.append(model.timestamp >= datetime_normalize(start_date))

    if end_date is not None:
        filters.append(model.timestamp <= datetime_normalize(end_date))

    try:
        stmt = session.query(model).filter(and_(*filters))
        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)

        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            res = session.execute(stmt).scalars().all()
            session.refresh(res)
            return [
                Adjustactor(
                    code=i.code,
                    timestamp=i.timestamp,
                    fore_adjustfactor=i.foreadjustfactor,
                    back_adjustfactor=i.backadjustfactor,
                    adjustfactor=i.adjustfactor,
                )
                for i in res
            ]

    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_mysql_connection().remove_session()
