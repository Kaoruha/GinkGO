import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.data.models import MPortfolio
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG, datetime_normalize


def add_portfolio(
    name: str,
    backtest_start_date: any,
    backtest_end_date: any,
    is_live: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    item = MPortfolio(
        name=name,
        backtest_start_date=datetime_normalize(backtest_start_date),
        backtest_end_date=datetime_normalize(backtest_end_date),
        is_live=is_live,
    )
    res = add(item)
    get_mysql_connection().remove_session()
    return res


def add_portfolios(orders: List[MPortfolio], *args, **kwargs):
    l = []
    for i in orders:
        if isinstance(i, MPortfolio):
            l.append(i)
        else:
            GLOG.WANR("add orders only support order data.")
    return add_all(l)


def delete_portfolio(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolio
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
        return len(query)
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def delete_portfolios(ids: List[str], *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolio
    filters = []
    filters.append(model.uuid.in_(ids))
    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_portfolio(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolio
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
        print(e)
    finally:
        get_mysql_connection().remove_session()


def update_portfolio(
    id: str,
    name: str = None,
    backtest_start_date: any = None,
    backtest_end_date: any = None,
    description: str = None,
    is_live: bool = None,
    *args,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MPortfolio
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if name is not None:
        updates["name"] = name
    if backtest_start_date is not None:
        updates["backtest_start_date"] = datetime_normalize(backtest_start_date)
    if backtest_end_date is not None:
        updates["backtest_end_date"] = datetime_normalize(backtest_end_date)
    if description is not None:
        updates["desc"] = description
    if is_live is not None:
        updates["is_live"] = bool(is_live)
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_portfolio(
    id: str,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPortfolio
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        return df
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()


def get_portfolios_page_filtered(
    name: Optional[str] = None,
    is_live: Optional[bool] = None,
    backtest_start_date: Optional[any] = None,
    backtest_end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPortfolio
    filters = [model.is_del == False]
    if name is not None:
        filters.append(model.name.like(f"%{name}%"))
    if is_live is not None:
        filters.append(model.is_live == is_live)
    if backtest_start_date:
        backtest_start_date = datetime_normalize(backtest_start_date)
        filters.append(model.backtest_start_date >= backtest_start_date)
    if backtest_end_date:
        backtest_end_date = datetime_normalize(backtest_end_date)
        filters.append(model.backtest_end_date <= backtest_end_date)

    try:
        stmt = session.query(model).filter(and_(*filters))
        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()
