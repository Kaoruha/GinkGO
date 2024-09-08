import pandas as pd
import datetime
from typing import List, Optional, Union, Tuple
from sqlalchemy import and_

from ginkgo.data.models import MTradeDay
from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.backtest.tradeday import TradeDay
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, MARKET_TYPES


def add_tradeday(
    market: MARKET_TYPES,
    is_open: bool,
    timestamp: any,
    *args,
    **kwargs,
) -> str:
    item = MTradeDay()
    item.set(market, is_open, timestamp)
    uuid = item.uuid
    add(item)
    return uuid


def add_tradedays(tradedays: List[Union[TradeDay, MTradeDay]], *args, **kwargs):
    l = []
    for i in tradedays:
        if isinstance(i, MTradeDay):
            l.append(i)
            continue
        elif isinstance(i, TradeDay):
            item = MTradeDay()
            item.set(i["market"], i["is_open"], datetime_normalize(i["timestamp"]))
            l.append(item)
            continue
        else:
            GLOG.WARN("add tradedays just support tradeday data.")
    return add_all(l)


def delete_tradeday_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs) -> int:
    # Seems no need
    conn = connection if connection else get_click_connection()
    model = MTradeDay
    filters = [model.uuid == id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.delete()

        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def softdelete_tradeday_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs) -> int:
    delete_tradeday_by_id(id, connection, *args, **kwargs)


def delete_tradeday_by_date_range(
    start_date: any,
    end_date: any,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    conn = connection if connection else get_click_connection()
    start_date = datetime_normalize(start_date)
    end_date = datetime_normalize(end_date)
    model = MTradeDay
    filters = [
        model.timestamp >= start_date,
        model.timestamp <= end_date,
    ]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.delete()
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def softdelete_tradeday_by_date_range(
    start_date: any,
    end_date: any,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    delete_tradeday_by_date_range(start_date, end_date, connection, *args, **kwargs)


def get_tradeday_by_market_and_date_range(
    market: MARKET_TYPES,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> Union[List[Tuple[datetime.datetime, bool]], pd.DataFrame]:
    conn = connection if connection else get_click_connection()
    model = MTradeDay
    filters = [model.isdel == False, model.market == market]

    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        query = conn.session.query(model).filter(and_(*filters))

        if page is not None and page_size is not None:
            query = query.offset(page * page_size).limit(page_size)

        if as_dataframe:
            if len(query.all()) > 0:
                df = pd.read_sql(query.statement, conn.engine)
                return df
            else:
                return pd.DataFrame()
        else:
            query = query.all()
            if len(query) == 0:
                return []
            else:
                res = []
                for i in query:
                    item = (i.timestamp, i.is_open)
                    res.append(item)
                return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return []
    finally:
        conn.close_session()
