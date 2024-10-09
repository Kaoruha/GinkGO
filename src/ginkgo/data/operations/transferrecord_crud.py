import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES
from ginkgo.data.models import MTransferRecord
from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.libs import GLOG
from ginkgo.backtest import Transfer


def add_transfer_record(
    portfolio_id: str,
    code: str,
    direction: TRANSFERDIRECTION_TYPES,
    market: MARKET_TYPES,
    money: float,
    status: TRANSFERSTATUS_TYPES,
    timestamp: any,
    *args,
    **kwargs,
) -> pd.Series:
    item = MTransferRecord(
        portfolio_id=portfolio_id,
        code=code,
        direction=direction,
        market=market,
        money=money,
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


def delete_transfer_record(id: str, *argss, **kwargs):
    session = get_click_connection().session
    model = MTransferRecord
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


def softdelete_transfer_record(id: str, *argss, **kwargs):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    delete_transfer_record(id, *args, **kwargs)


def update_transfer_record(
    id: str,
    portfolio_id: str = None,
    code: str = None,
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
    if code is not None:
        updates["code"] = code
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
    *args,
    **kwargs,
) -> pd.Series:
    session = get_click_connection().session
    model = MTransferRecord
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


def get_transfer_records(
    portfolio_id: str,
    code: Optional[str] = None,
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
