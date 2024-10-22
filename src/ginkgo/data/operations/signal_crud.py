import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data.models import MSignal
from ginkgo.backtest import Signal
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG, datetime_normalize


def add_signal(
    portfolio_id: str,
    timestamp: any,
    code: str,
    direction: DIRECTION_TYPES,
    reason: str,
    source: SOURCE_TYPES = SOURCE_TYPES.SIM,
    *args,
    **kwargs,
) -> pd.Series:
    item = MSignal(
        portfolio_id=portfolio_id,
        timestamp=datetime_normalize(timestamp),
        code=code,
        direction=direction,
        reason=reason,
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_signals(signals: List[Union[MSignal, Signal]], *args, **kwargs):
    l = []
    for i in signals:
        if isinstance(i, MSignal):
            l.append(i)
        elif isinstance(i, Signal):
            item = MSignal(
                portfolio_id=i.portfolio_id,
                timestamp=i.timestamp,
                code=i.code,
                direction=i.direction,
                reason=i.reason,
                source=i.source,
            )
            l.append(item)
        else:
            GLOG.WANR("add signals only support signal data.")
    return add_all(l)


def delete_signal(id: str, *argss, **kwargs):
    session = get_click_connection().session
    model = MSignal
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_signal_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def softdelete_signal(id: str, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_signal(id, *argss, **kwargs)


def delete_signal_by_portfolio_and_date_range(
    portfolio_id: str, start_date: any = None, end_date: any = None, *argss, **kwargs
):
    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    session = get_click_connection().session
    model = MSignal
    sql = f"DELETE FROM {model.__tablename__} WHERE portfolio_id = :portfolio_id"
    params = {"portfolio_id": portfolio_id}
    if start_date is not None:
        sql += " AND timestamp >= :start_date"
        params["start_date"] = datetime_normalize(start_date)
    if end_date is not None:
        sql += " AND timestamp <= :end_date"
        params["end_date"] = datetime_normalize(end_date)
    try:
        session.execute(text(sql), params)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def softdelete_signal_by_portfolio_and_date_range(
    portfolio_id: str, start_date: any = None, end_date: any = None, *argss, **kwargs
):
    return delete_signal_by_portfolio_and_date_range(portfolio_id, start_date, end_date, *argss, **kwargs)


def get_signal(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MSignal
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df.iloc[0]
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_click_connection().remove_session()


def get_signals(
    portfolio_id: str,
    code: Optional[str] = None,
    direction: Optional[DIRECTION_TYPES] = None,
    reason: Optional[str] = None,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_click_connection().session
    model = MSignal
    filters = [model.portfolio_id == portfolio_id]
    if code is not None:
        filters.append(model.code == code)
    if direction is not None:
        filters.append(model.direction == direction)
    if reason is not None:
        filters.append(model.reason.like(f"%{reason}%"))

    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)
    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        stmt = session.query(model).filter(and_(*filters))
        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)

        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            if df.shape[0] == 0:
                return pd.DataFrame()
            return df
        else:
            res = session.execute(stmt).scalars().all()
            return [Signal(i.portfolio_id, i.timestamp, i.code, i.direction, i.reason, i.source) for i in res]
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_click_connection().remove_session()
