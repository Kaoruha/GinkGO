import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union

from ginkgo.enums import MARKET_TYPES
from ginkgo.data.models import MTradeDay
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG


def add_trade_day(market: MARKET_TYPES, is_open: bool, timestamp: any, *args, **kwargs) -> pd.Series:
    item = MTradeDay(market=market, is_open=is_open, timestamp=datetime_normalize(timestamp))
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_trade_days(files: List[MTradeDay], *args, **kwargs):
    l = []
    for i in files:
        if isinstance(i, MTradeDay):
            l.append(i)
        else:
            GLOG.WANR("add files only support file data.")
    return add_all(l)


def delete_trade_day(id: str, *argss, **kwargs):
    session = get_click_connection().session
    model = MTradeDay
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
        get_click_connection().remove_session()


def delete_trade_days(ids: List[str], *argss, **kwargs):
    session = get_click_connection().session
    model = MTradeDay
    filters = []
    for i in ids:
        filters.append(model.uuid == i)
    try:
        query = session.query(model).filter(or_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord_by_id: id {ids} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_click_connection().remove_session()


def delete_trade_days_by_market_and_date_range(
    market: MARKET_TYPES, start_date: any = None, end_date: any = None, *argss, **kwargs
):
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
        get_click_connection().remove_session()


def softdelete_trade_day(id: str, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    delete_trade_day(id, *argss, **kwargs)


def update_trade_day(
    *argss,
    **kwargs,
):
    pass


def get_trade_day_by_id(
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
        return df.iloc[0]
    except Exception as e:
        session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        get_click_connection().remove_session()


def get_trade_days(market: MARKET_TYPES, start_date: Optional[any] = None,end_date:Optional[any], *args, **kwargs) -> pd.DataFrame:
    session = get_click_connection().session
    model = MTradeDay
    filters = [model.market=market]
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

        return df

    except Exception as e:
        session.rollback()
        print(e)
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_click_connection().remove_session()
