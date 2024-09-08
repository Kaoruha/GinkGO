import pandas as pd
import datetime
from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.models import MTransferRecord
from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.backtest.transfer import Transfer
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, MARKET_TYPES


def add_transfer_record(
    portfolio_id: str,
    direction: DIRECTION_TYPES,
    market: MARKET_TYPES,
    money: float,
    timestamp: any,
    *args,
    **kwargs,
) -> str:
    item = MTransferRecord()
    item.set(
        portfolio_id,
        direction,
        market,
        money,
        datetime_normalize(timestamp),
    )
    uuid = item.uuid
    add(item)
    return uuid


def add_transfer_records(records: List[Union[Transfer, MTransferRecord]], *args, **kwargs):
    l = []
    for i in records:
        item = MTransferRecord()
        item.set(
            i.portfolio_id,
            i.direction,
            i.market,
            i.money,
            datetime_normalize(i.timestamp),
        )
        l.append(item)
    return add_all(l)


def delete_transfer_record_by_id(id: str, connection: GinkgoClickhouse = None, *args, **kwargs) -> int:
    conn = connection if connection else get_click_connection()
    model = MTransferRecord
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


def softdelete_transfer_record_by_id(id: str, connection: GinkgoClickhouse = None, *args, **kwargs) -> int:
    GLOG.WARN("TransferRecord does not support soft delete, use the delete method instead.")
    return delete_transfer_record_by_id(id, connection, *args, **kwargs)


def delete_transfer_record_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: GinkgoClickhouse = None,
    *args,
    **kwargs,
) -> int:
    conn = connection if connection else get_click_connection()
    model = MTransferRecord
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


def softdelete_transfer_record_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: GinkgoClickhouse = None,
    *args,
    **kwargs,
) -> int:
    GLOG.WARN("TransferRecord does not support soft delete, use the delete method instead.")
    return delete_transfer_record_by_portfolio_id(portfolio_id, start_date, end_date, connection, *args, **kwargs)


def get_transfer_record_by_id(
    id: str, as_dataframe: bool = False, connection: GinkgoClickhouse = None, *args, **kwargs
):
    conn = connection if connection else get_click_connection()
    model = MTransferRecord
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


def get_transfer_record_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> Union[List[MTransferRecord], pd.DataFrame]:
    conn = connection if connection else get_click_connection()
    model = MTransferRecord

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
                    item = Transfer(i.portfolio_id, i.direction, i.market, i.money, i.timestamp)
                    res.append(item)
                return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return []
    finally:
        conn.close_session()
