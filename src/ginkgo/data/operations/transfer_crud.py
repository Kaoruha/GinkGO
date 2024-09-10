import pandas as pd
import datetime
from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.models import MTransfer
from ginkgo.data.drivers import add, add_all, get_mysql_connection, GinkgoMysql
from ginkgo.backtest.transfer import Transfer
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES


def add_transfer(
    portfolio_id: str,
    direction: DIRECTION_TYPES,
    market: MARKET_TYPES,
    money: float,
    status: TRANSFERSTATUS_TYPES,
    timestamp: any,
    *args,
    **kwargs,
) -> str:
    item = MTransfer()
    item.set(portfolio_id, direction, market, money, status, datetime_normalize(timestamp))
    uuid = item.uuid
    add(item)
    return uuid


def add_transfers(transfers: List[Union[Transfer, MTransfer]], *args, **kwargs):
    l = []
    for i in transfers:
        if isinstance(i, MTransfer):
            l.append(i)
            continue
        elif isinstance(i, Transfer):
            item = MTransfer()
            item.set(
                i["portfolio_id"],
                i["direction"],
                i["market"],
                i["money"],
                i["status"],
                datetime_normalize(i["timestamp"]),
            )
            l.append(item)
        else:
            pass
    return add_all(l)


def delete_transfer_by_id(id: str, connection: GinkgoMysql = None, *args, **kwargs) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MTransfer
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


def softdelete_transfer_by_id(id: str, connection: GinkgoMysql = None, *args, **kwargs) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MTransfer
    filters = [model.uuid == id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        res.delete()
        conn.session.commit()
        return 1
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def delete_transfer_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: GinkgoMysql = None,
    *args,
    **kwargs,
) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MTransfer
    filters = [model.portfolio_id == portfolio_id]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

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


def softdelete_transfer_by_portfolio_id(portfolio_id: str, connection: GinkgoMysql = None, *args, **kwargs) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MTransfer
    filters = [model.portfolio_id == portfolio_id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.all()
        count = 0
        for i in res:
            count += 1
            i.delete()
            conn.session.commit()
        return 1
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def get_transfer_by_id(id: str, as_dataframe: bool = False, connection: GinkgoMysql = None, *args, **kwargs):
    conn = connection if connection else get_mysql_connection()
    model = MTransfer
    filters = [model.uuid == id, model.isdel == False]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        if as_dataframe:
            df = pd.read_sql(query.statement, conn.engine)
            if df.shape[0] > 1:
                GLOG.ERROR(f"Transfer about {id} should not have more than 1 record.")
            return df
        else:
            query = query.first()
            if query is None:
                return None
            else:
                item = Transfer(
                    portfolio_id=query.portfolio_id,
                    direction=query.direction,
                    market=query.market,
                    money=query.money,
                    timestamp=query.timestamp,
                )
                return item
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return None
    finally:
        conn.close_session()


def get_transfer_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: Optional[GinkgoMysql] = None,
    *args,
    **kwargs,
) -> Union[List[MTransfer], pd.DataFrame]:
    conn = connection if connection else get_mysql_connection()
    model = MTransfer
    filters = [model.portfolio_id == portfolio_id, model.isdel == False]

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
                    item = Transfer()
                    item.set(i)
                    res.append(item)
                return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return []
    finally:
        conn.close_session()
