from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.backtest import Position
from ginkgo.data.models import MPosition
from ginkgo.libs import datetime_normalize


def add_position(engine_id: str, timestamp: any, code: str, volume: int, cost: float, *args, **kwargs):
    item = MPosition(engine_id, datetime_normalize(timestamp), code, volume, cost)
    uuid = item.uuid
    add(item)
    return uuid


def add_positions(positions: List[Union[Position, MPosition]]):
    l = []
    for i in positions:
        if isinstance(i, MPosition):
            l.append(i)
        elif isinstance(i, Position):
            item = MTransferRecord()
            item.set(i.code, i.engine_id, i.volume, i.cost)
            l.append(item)
        else:
            pass
    return add_all(l)


def delete_position_by_id(id: str, connection: GinkgoClickhouse = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [MPosition.uuid == id]
    try:
        query = conn.session.query(MPosition).filter(and_(*filters))
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


def softdelete_position_by_id(id: str, connection: GinkgoClickhouse = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [MPosition.uuid == id]
    try:
        query = conn.session.query(MPosition).filter(and_(*filters))
        item = query.first()
        item.delete()
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def delete_position_by_portfolio_id(portfolio_id: str, connection: GinkgoClickhouse = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [MPosition.engine_id == portfolio_id]
    try:
        query = conn.session.query(MPosition).filter(and_(*filters))
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


def softdelete_position_by_portfolio_id(portfolio_id: str, connection: GinkgoClickhouse = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [MPosition.engine_id == portfolio_id]
    try:
        query = conn.session.query(MPosition).filter(and_(*filters))
        res = query.all()
        for i in res:
            i.delete()
            conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def update_position(id: str, code: str, engine_id: str, volume: int, cost: float, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    filters = [MPosition.uuid == id]
    try:
        query = conn.session.query(MPosition).filter(and_(*filters))
        res = query.first()
        i.code = code
        i.engine_id = engine_id
        i.volume = volume
        i.cost = cost
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def get_position_by_portfolio_id_and_date_range(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
):
    conn = connection if connection else get_click_connection()
    filters = [MPosition.portfolio_id == portfolio_id, MPosition.isdel == False]

    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(MPosition.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(MPosition.timestamp <= end_date)

    try:
        query = conn.session.query(MPosition).filter(and_(*filters))

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
