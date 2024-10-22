import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import MARKET_TYPES
from ginkgo.data.models import MTradeDay
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG, datetime_normalize


def add_tradeday(market: MARKET_TYPES, is_open: bool, timestamp: any, *args, **kwargs) -> pd.Series:
    item = MTradeDay(market=market, is_open=is_open, timestamp=datetime_normalize(timestamp))
    res = add(item)
    df = res.to_dataframe()
    df["is_open"] = df["is_open"].apply(lambda x: True if x.lower() == "true" else False)
    get_click_connection().remove_session()
    return df.iloc[0]


def add_tradedays(files: List[MTradeDay], *args, **kwargs):
    l = []
    for i in files:
        if isinstance(i, MTradeDay):
            l.append(i)
        else:
            GLOG.WANR("add files only support file data.")
    return add_all(l)


def delete_tradeday(id: str, *argss, **kwargs):
    session = get_click_connection().session
    model = MTradeDay
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def softdelete_tradeday(id: str, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    delete_tradeday(id, *argss, **kwargs)


def delete_tradedays(market: MARKET_TYPES, start_date: any = None, end_date: any = None, *argss, **kwargs):

    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    session = get_click_connection().session
    model = MTradeDay
    sql = f"DELETE FROM `{model.__tablename__}` WHERE market = :market"
    params = {"market": market}
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


def softdelete_tradedays(market: MARKET_TYPES, start_date: any = None, end_date: any = None, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    delete_tradedays(market, start_date, end_date, *argss, **kwargs)


def update_tradeday(
    *argss,
    **kwargs,
):
    pass


def get_tradeday(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MTradeDay
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        df["is_open"] = df["is_open"].apply(lambda x: True if x.lower() == "true" else False)
        return df.iloc[0]
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_click_connection().remove_session()


def get_tradedays(
    market: MARKET_TYPES, start_date: Optional[any] = None, end_date: Optional[any] = None, *args, **kwargs
) -> pd.DataFrame:
    session = get_click_connection().session
    model = MTradeDay
    filters = [model.market == market]
    if start_date is not None:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)
    try:
        stmt = session.query(model).filter(and_(*filters))
        df = pd.read_sql(stmt.statement, session.connection())

        if df.shape[0] == 0:
            return pd.DataFrame()

        df["is_open"] = df["is_open"].apply(lambda x: True if x.lower() == "true" else False)
        return df

    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_click_connection().remove_session()
