from typing import List, Optional, Union, Tuple
from sqlalchemy import and_

from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.backtest import Position
from ginkgo.data.models import MPositionRecord
from ginkgo.libs import datetime_normalize


def add_position_record(code: str, cost: float, volume: int, portfolio_id: str, timestamp: any, *args, **kwargs):
    item = MPositionRecord()
    item.set(portfolio_id, datetime_normalize(timestamp), code, volume, cost)
    uuid = item.uuid
    add(item)
    return uuid


def add_position_records(positions: List[Union[Position, MPositionRecord]], *args, **kwargs):
    l = []
    for i in positions:
        if isinstance(i, MPositionRecord):
            l.append(i)
            continue
        elif isinstance(i, Position):
            item = MPositionRecord()
            item.set(i.engine_id, datetime_normalize(i.timestamp), i.code, i.volume, i.cost)
            l.append(item)
            continue
        else:
            GLOG.WARN("add signals just support signal data.")
    return add_all(l)


def delete_position_record_by_id(id: str, connection: GinkgoClickhouse = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [
        MPositionRecord.uuid == id,
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


def softdelete_position_record_by_id(id: str, connection: GinkgoClickhouse = None, *args, **kwargs):
    GLOG.WARN("TransferRecord does not support soft delete, use the delete method instead.")
    return delete_position_record_by_id(id, connection, *args, **kwargs)


def delete_position_record_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any],
    end_date: Optional[any],
    connection: GinkgoClickhouse = None,
    *args,
    **kwargs
):
    conn = connection if connection else get_click_connection()
    filters = [
        MPositionRecord.engine_id == portfolio_id,
    ]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(MPositionRecord.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(MPositionRecord.timestamp <= end_date)
    try:
        query = conn.session.query(model).filter(and_(*filters))
    except Exception as e:
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


def softdelete_position_record_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any],
    end_date: Optional[any],
    connection: GinkgoClickhouse = None,
    *args,
    **kwargs
):
    GLOG.WARN("PositionRecord does not support soft delete, use the delete method instead.")
    return delete_position_record_by_portfolio_id(portfolio_id, start_date, end_date, connection, *args, **kwargs)


def update_position_record():
    # TODO no need
    pass


def get_position_record_by_portfolio_id_and_date_range(
    portfolio_id: str,
    start_date: Optional[any],
    end_date: Optional[any],
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: GinkgoClickhouse = None,
    *args,
    **kwargs
):
    conn = connection if connection else get_click_connection()
    filters = [MPositionRecord.portfolio_id == portfolio_id, MPositionRecord.isdel == False]

    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(MPositionRecord.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(MPositionRecord.timestamp <= end_date)

    try:
        query = conn.session.query(MPositionRecord).filter(and_(*filters))

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
                    item = Position(i.engine_id, i.code, i.cost, i.volume, 0)
                    res.append(item)
                return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return []
    finally:
        conn.close_session()
