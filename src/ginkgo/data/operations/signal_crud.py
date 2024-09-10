from typing import List, Optional, Union, Tuple
from sqlalchemy import and_

from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.backtest import Signal
from ginkgo.data.models import MSignal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import datetime_normalize


def add_signal(
    portfolio_id: str, timestamp: any, code: str, direction: DIRECTION_TYPES, reason: str = "", *args, **kwargs
):
    item = MSignal()
    item.set(portfolio_id, datetime_normalize(timestamp), code, direction, reason)
    uuid = item.uuid
    add(item)
    return uuid


def add_signals(signals: List[Union[Signal, MSignal]]):
    l = []
    for i in signals:
        if isinstance(i, MSignal):
            l.append(i)
            continue
        elif isinstance(i, Signal):
            item = MSignal()
            item.set(i.portfolio_id, i.timestamp, i.code, i.direction, i.reason)
            l.append(item)
            continue
        else:
            GLOG.WARN("add signals just support signal data.")
    return add_all(l)


def delete_signal_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [
        MSignal.uuid == id,
    ]
    try:
        query = conn.session.query(MSignal).filter(and_(*filters))
        query.delete()
    except Exception as e:
        print(e)
        conn.session.rollback()
    finally:
        conn.close_session()


def softdelete_signal_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs):
    GLOG.WARN("Signal does not support soft delete, use the delete method instead.")
    delete_signal_by_id(id, connection, *args, **kwargs)


def delete_signal_by_portfolio_id(
    portfolio_id: str,
    start_date: any = None,
    end_date: any = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs
):
    conn = connection if connection else get_click_connection()
    filters = [
        MSignal.portfolio_id == portfolio_id,
    ]
    if start_date is not None and end_date is not None:
        start_date = datetime_normalize(start_date)
        end_date = datetime_normalize(end_date)
        filters.append(MSignal.timestamp >= start_date)
        filters.append(MSignal.timestamp <= end_date)

    try:
        query = conn.session.query(MSignal).filter(and_(*filters))
        res = query.delete()
        return res
    except Exception as e:
        print(e)
        conn.session.rollback()
    finally:
        conn.close_session()


def softdelete_signal(
    portfolio_id: str,
    start_date: any = None,
    end_date: any = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs
):
    GLOG.WARN("Signal does not support soft delete, use the delete method instead.")
    delete_signal_by_portfolio_id(portfolio_id, start_date, end_date, connection, *args, **kwargs)


def update_signal():
    # TODO Remove and reinsert
    pass


def get_signal_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [
        MSignal.uuid == id,
    ]
    try:
        query = conn.session.query(MSignal).filter(and_(*filters))
        res = query.first()
        item = Signal()
        item.set(res)
        return item
    except Exception as e:
        print(e)
        conn.session.rollback()
    finally:
        conn.close_session()


def get_signal_by_portfolio_id_and_date_range(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    as_dataframe: Optional[bool] = False,
    connection: Optional[GinkgoClickhouse] = None,
):
    conn = connection if connection else get_click_connection()
    filters = [
        MSignal.portfolio_id == portfolio_id,
    ]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(MSignal.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(MSignal.timestamp <= end_date)

    try:
        query = conn.session.query(MSignal).filter(and_(*filters))

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
                    item = Signal()
                    item.set(i)
                    res.append(item)
                return res
    except Exception as e:
        print(e)
        conn.session.rollback()
    finally:
        conn.close_session()
