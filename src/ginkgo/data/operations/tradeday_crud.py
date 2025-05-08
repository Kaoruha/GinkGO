import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import MARKET_TYPES
from ginkgo.data.models import MTradeDay
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG, datetime_normalize


def add_tradeday(market: MARKET_TYPES, is_open: bool, timestamp: any, *args, **kwargs) -> pd.Series:
    item = MTradeDay(market=market, is_open=is_open, timestamp=datetime_normalize(timestamp))
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
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
    model = MTradeDay
    try:
        filters = [model.uuid == id]
        session = get_mysql_connection().session
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_tradeday_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_tradeday(id: str, *argss, **kwargs):
    model = MTradeDay
    filters = [model.uuid == id]
    try:
        session = get_mysql_connection().session
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_tradeday_by_id: id {id} has more than one record.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def delete_tradedays_filtered(market: MARKET_TYPES, start_date: any = None, end_date: any = None, *argss, **kwargs):

    model = MTradeDay
    filters = [model.is_del == False, model.market == market]
    if start_date is not None:
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        filters.append(model.timestamp <= end_date)
    try:
        session = get_mysql_connection().session
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_tradedays_filtered(market: MARKET_TYPES, start_date: any = None, end_date: any = None, *argss, **kwargs):
    model = MTradeDay
    filters = [model.is_del == False, model.market == market]
    if start_date is not None:
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        filters.append(model.timestamp <= end_date)
    try:
        # TODO use update directly
        session = get_mysql_connection().session
        query = session.query(model).filter(and_(*filters)).all()
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def update_tradeday(
    *argss,
    **kwargs,
):
    pass


def get_tradeday(
    id: str,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    model = MTradeDay
    filters = [model.uuid == id]

    try:
        session = get_mysql_connection().session
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
        get_mysql_connection().remove_session()


def get_tradedays_page_filtered(
    market: MARKET_TYPES,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.DataFrame:
    model = MTradeDay
    filters = [model.market == market, model.is_del == False]
    if start_date is not None:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)
    if end_date is not None:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)
    try:
        session = get_mysql_connection().session
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
