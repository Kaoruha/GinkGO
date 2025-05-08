import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union
from decimal import Decimal

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.data.models import MOrderRecord
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG, datetime_normalize, Number, to_decimal
from ginkgo.backtest import Order


def add_order_record(
    order_id: str,
    portfolio_id: str,
    engine_id: str,
    code: str,
    direction: DIRECTION_TYPES,
    order_type: ORDER_TYPES,
    status: ORDERSTATUS_TYPES,
    volume: int,
    limit_price: Number,
    frozen: Number,
    transaction_price: Number,
    remain: Number,
    fee: Number,
    timestamp: any,
    *args,
    **kwargs,
) -> pd.Series:
    item = MOrderRecord(
        order_id=order_id,
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
    get_click_connection().remove_session()
    return df.iloc[0]


def add_order_records(orders: List[MOrderRecord], *args, **kwargs):
    l = []
    for i in orders:
        if isinstance(i, MOrderRecord):
            l.append(i)
        else:
            GLOG.WANR("add orders only support order data.")
    return add_all(l)


def delete_order_record(id: str, *argss, **kwargs):
    session = get_click_connection().session
    model = MOrderRecord
    sql = f"DELETE FROM {model.__tablename__} WHERE uuid = :id"
    params = {"id": id}
    try:
        session.execute(text(sql), params)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def softdelete_order_record(id: str, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_order_record(id, *argss, **kwargs)


def delete_order_records_filtered(portfolio_id: str, start_date: any = None, end_date: any = None, *argss, **kwargs):
    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    session = get_click_connection().session
    model = MOrderRecord
    sql = f"DELETE FROM {model.__tablename__} WHERE portfolio_id = :portfolio_id"
    params = {"portfolio_id": portfolio_id}
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


def get_order_record(
    id: str,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MOrderRecord
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        return df.iloc[0]
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_click_connection().remove_session()


def get_order_records_page_filtered(
    portfolio_id: str,
    engine_id: Optional[str] = None,
    order_id: Optional[str] = None,
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
    session = get_click_connection().session
    model = MOrderRecord
    filters = [model.portfolio_id == portfolio_id]
    if engine_id is not None:
        filters.append(model.engine_id == engine_id)
    if order_id is not None:
        filters.append(model.order_id == order_id)
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
            return df.iloc[0]
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
                    uuid=i.order_id,
                    portfolio_id=i.portfolio_id,
                    engine_id=i.engine_id,
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
        get_click_connection().remove_session()
