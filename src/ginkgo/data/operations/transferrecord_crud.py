import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES, MARKET_TYPES
from ginkgo.data.models import MTransferRecord
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG, datetime_normalize, Number, to_decimal
from ginkgo.backtest import Transfer


def add_transfer_record(
    portfolio_id: str,
    direction: TRANSFERDIRECTION_TYPES,
    market: MARKET_TYPES,
    money: Number,
    status: TRANSFERSTATUS_TYPES,
    timestamp: any,
    *args,
    **kwargs,
) -> pd.Series:
    item = MTransferRecord(
        portfolio_id=portfolio_id,
        direction=direction,
        market=market,
        money=to_decimal(money),
        status=status,
        timestamp=datetime_normalize(timestamp),
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_transfer_records(orders: List[MTransferRecord], *args, **kwargs):
    l = []
    for i in orders:
        if isinstance(i, MTransferRecord):
            l.append(i)
        else:
            GLOG.WANR("add orders only support order data.")
    return add_all(l)


def delete_transfer_record(id: str, *args, **kwargs):
    session = get_click_connection().session
    model = MTransferRecord
    sql = f"DELETE FROM `{model.__tablename__}` WHERE uuid = :id"
    params = {"uuid": id}
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


def softdelete_transfer_record(id: str, *args, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    delete_transfer_record(id, *args, **kwargs)


def delete_transfer_records_filtered(portfolio_id: str, start_date: any = None, end_date: any = None, *args, **kwargs):
    session = get_click_connection().session
    model = MTransferRecord
    sql = f"DELETE FROM `{model.__tablename__}` WHERE portfolio_id = :portfolio_id"
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


def softdelete_transfer_records_filtered(
    portfolio_id: str, start_date: any = None, end_date: any = None, *args, **kwargs
):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    delete_transfer_records_by_portfolio(portfolio_id, start_date, end_date, *args, **kwargs)


def update_transfer_record(
    id: str,
    portfolio_id: str = None,
    direction: TRANSFERDIRECTION_TYPES = None,
    market: MARKET_TYPES = None,
    money: float = None,
    status: TRANSFERSTATUS_TYPES = None,
    timestamp: any = None,
    *args,
    **kwargs,
):
    model = MTransferRecord
    session = get_click_connection().session
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if portfolio_id is not None:
        updates["portfolio_id"] = portfolio_id
    if direction is not None:
        updates["direction"] = direction
    if market is not None:
        updates["market"] = market
    if money is not None:
        updates["money"] = money
    if status is not None:
        updates["status"] = status
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
        get_click_connection().remove_session()


def get_transfer_record(
    id: str,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MTransferRecord
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))
        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            query = stmt.first()
            return Transfer(
                uuid=query.uuid,
                portfolio_id=query.portfolio_id,
                direction=query.direction,
                market=query.market,
                money=query.money,
                status=query.status,
                timestamp=query.timestamp,
            )
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return None
    finally:
        get_click_connection().remove_session()


def get_transfer_records_filtered(
    portfolio_id: str,
    direction: Optional[TRANSFERDIRECTION_TYPES] = None,
    status: Optional[TRANSFERSTATUS_TYPES] = None,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MTransferRecord
    filters = [model.portfolio_id == portfolio_id]
    if direction is not None:
        filters.append(model.direction == direction)
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
                Transfer(
                    portfolio_id=i.portfolio_id,
                    direction=i.direction,
                    market=i.market,
                    money=i.money,
                    status=i.status,
                    timestamp=i.timestamp,
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
