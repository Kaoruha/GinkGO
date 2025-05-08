import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union
from decimal import Decimal

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.data.models import MOrder
from ginkgo.backtest import Order
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG, datetime_normalize, Number, to_decimal


def add_order(
    portfolio_id: str,
    engine_id: str,
    code: str,
    direction: DIRECTION_TYPES,
    order_type: ORDER_TYPES,
    status: ORDERSTATUS_TYPES,
    volume: int,
    limit_price: Number,
    frozen: int,
    transaction_price: Number,
    remain: float,
    fee: float,
    timestamp: any,
    *args,
    **kwargs,
) -> pd.Series:
    item = MOrder(
        portfolio_id=portfolio_id,
        engine_id=engine_id,
        code=code,
        direction=direction,
        order_type=order_type,
        status=status,
        volume=volume,
        limit_price=to_decimal(limit_price),
        frozen=frozen,
        transaction_price=to_decimal(transaction_price),
        remain=to_decimal(remain),
        fee=to_decimal(fee),
        timestamp=datetime_normalize(timestamp),
    )
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_orders(orders: List[MOrder], *args, **kwargs):
    l = []
    for i in orders:
        if isinstance(i, MOrder):
            l.append(i)
        else:
            GLOG.WANR("add orders only support order data.")
    return add_all(l)


def delete_order(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MOrder
    filters = [model.uuid == id]
    try:
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
        get_mysql_connection().remove_session()


def delete_orders_filtered(portfolio_id: str = None, engine_id: str = None, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MOrder
    filters = [model.is_del == False]

    if (portfolio_id is None) and (engine_id is None):
        # TODO Log
        return

    if portfolio_id is not None:
        filters.append(model.portfolio_id == portfolio_id)
    if engine_id is not None:
        filters.append(model.engine_id == engine_id)
    try:
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
        get_mysql_connection().remove_session()


# def delete_orders_by_engine(engine_id: str, *argss, **kwargs):
#     session = get_mysql_connection().session
#     model = MOrder
#     filters = [model.engine_id == engine_id]
#     try:
#         query = session.query(model).filter(and_(*filters)).all()
#         if len(query) > 1:
#             GLOG.WARN(f"delete_analyzerrecord: id {id} has more than one record.")
#         for i in query:
#             session.delete(i)
#             session.commit()
#     except Exception as e:
#         session.rollback()
#         GLOG.ERROR(e)
#     finally:
#         get_mysql_connection().remove_session()


def softdelete_order(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MOrder
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_adjustfactor: id {id} has more than one record.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def update_order(
    id: str,
    portfolio_id: Optional[str] = None,
    engine_id: Optional[str] = None,
    code: Optional[str] = None,
    direction: Optional[DIRECTION_TYPES] = None,
    order_type: Optional[ORDER_TYPES] = None,
    status: Optional[ORDERSTATUS_TYPES] = None,
    volume: Optional[int] = None,
    limit_price: Optional[float] = None,
    frozen: Optional[float] = None,
    transaction_price: Optional[float] = None,
    remain: Optional[float] = None,
    fee: Optional[float] = None,
    timestamp: Optional[any] = None,
    *args,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MOrder
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if portfolio_id is not None:
        updates["portfolio_id"] = portfolio_id
    if engine_id is not None:
        updates["engine_id"] = portfolio_id
    if code is not None:
        updates["code"] = code
    if direction is not None:
        updates["direction"] = direction
    if order_type is not None:
        updates["order_type"] = order_type
    if status is not None:
        updates["status"] = status
    if volume is not None:
        updates["volume"] = volume
    if limit_price is not None:
        updates["limit_price"] = limit_price
    if frozen is not None:
        updates["frozen"] = frozen
    if transaction_price is not None:
        updates["transaction_price"] = transaction_price
    if remain is not None:
        updates["remain"] = remain
    if fee is not None:
        updates["fee"] = fee
    if timestamp is not None:
        updates["timestamp"] = datetime_normalize(timestamp)
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_order(
    id: str,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MOrder
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        return df
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame().iloc[0]
    finally:
        get_mysql_connection().remove_session()


def get_orders_page_filtered(
    portfolio_id: str,
    engine_id: str,
    code: Optional[str] = None,
    direction: Optional[DIRECTION_TYPES] = None,
    order_type: Optional[ORDER_TYPES] = None,
    status: Optional[ORDERSTATUS_TYPES] = None,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MOrder
    filters = [model.portfolio_id == portfolio_id, model.engine_id == engine_id, model.is_del == False]
    if code is not None:
        filters.append(model.code == code)
    if direction is not None:
        filters.append(model.direction == direction)
    if order_type is not None:
        filters.append(model.order_type == order_type)
    if status is not None:
        filters.append(model.status == status)
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
            return [
                Order(
                    code=i.code,
                    direction=i.direction,
                    order_type=i.order_type,
                    status=i.status,
                    volume=i.volume,
                    limit_price=i.limit_price,
                    frozen=i.frozen,
                    transaction_price=i.transaction_price,
                    remain=i.remain,
                    fee=i.fee,
                    timestamp=i.timestamp,
                    uuid=i.uuid,
                    portfolio_id=i.portfolio_id,
                    source=i.source,
                )
                for i in res
            ]
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_mysql_connection().remove_session()
