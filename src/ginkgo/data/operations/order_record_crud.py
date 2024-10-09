import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.data.models import MOrderRecord
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG, datetime_normalize
from ginkgo.backtest import Order


def add_order_record(
    portfolio_id: str,
    order_id: str,
    code: str,
    direction: DIRECTION_TYPES,
    type: ORDER_TYPES,
    status: ORDERSTATUS_TYPES,
    volume: int,
    limit_price: float,
    frozen: float,
    transaction_price: float,
    remain: float,
    fee: float,
    timestamp: any,
    *args,
    **kwargs,
) -> pd.Series:
    item = MOrderRecord(
        portfolio_id=portfolio_id,
        order_id=order_id,
        code=code,
        direction=direction,
        type=type,
        status=status,
        volume=volume,
        limit_price=limit_price,
        frozen=frozen,
        transaction_price=transaction_price,
        remain=remain,
        fee=fee,
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


def softdelete_order_record(id: str, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_order_record(id, *argss, **kwargs)


def get_order_record_by_id(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MOrderRecord
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


def get_order_records(
    portfolio_id: str,
    code: Optional[str] = None,
    direction: Optional[DIRECTION_TYPES] = None,
    type: Optional[ORDER_TYPES] = None,
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
    if code is not None:
        filters.append(model.code == code)
    if direction is not None:
        filters.append(model.direction == direction)
    if type is not None:
        filters.append(model.type == type)
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
                    type=i.type,
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
