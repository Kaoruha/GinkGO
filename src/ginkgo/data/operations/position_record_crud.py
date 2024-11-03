import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.data.models import MPositionRecord
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG, Number, to_decimal


def add_position_record(
    portfolio_id: str,
    timestamp: any,
    code: str,
    volume: int,
    frozen: int,
    cost: Number,
    *args,
    **kwargs,
) -> pd.Series:
    item = MPositionRecord(portfolio_id=portfolio_id, code=code, volume=volume, frozen=frozen, cost=to_decimal(cost))
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_position_records(orders: List[MPositionRecord], *args, **kwargs):
    l = []
    for i in orders:
        if isinstance(i, MPositionRecord):
            l.append(i)
        else:
            GLOG.WANR("add position records only support position record data.")
    return add_all(l)


def delete_position_record(id: str, *argss, **kwargs):
    session = get_click_connection().session
    model = MPositionRecord
    try:
        filters = [model.uuid == id]
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
        get_click_connection().remove_session()


def softdelete_position_record(id: str, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_position_record(id, *argss, **kwargs)


def delete_position_records_by_portfolio_and_code(
    portfolio_id: str, code: str = None, start_date: any = None, end_date: any = None, *argss, **kwargs
):
    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    session = get_click_connection().session
    model = MPositionRecord
    sql = f"DELETE FROM {model.__tablename__} WHERE portfolio_id = :portfolio_id AND code = :code"
    params = {"portfolio_id": portfolio_id, "code": code}
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


def softdelete_position_records_by_portfolio_and_code(portfolio_id: str, code: str = None, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_position_records_by_portfolio_and_code(portfolio_id, code, *argss, **kwargs)


def get_position_record(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MPositionRecord
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
        get_click_connection().remove_session()


def get_position_records(
    portfolio_id: str,
    code: Optional[str] = None,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MPositionRecord
    filters = [model.portfolio_id == portfolio_id]
    if code is not None:
        filters.append(model.code == code)
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
            query = query.all()
            if len(query) == 0:
                return []
            else:
                res = []
                for i in query:
                    item = Transfer()
                    item.set(i)
                    res.append(item)
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_click_connection().remove_session()
