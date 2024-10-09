import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.data.models import MPosition
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG, datetime_normalize
from ginkgo.backtest import Position


def add_position(
    portfolio_id: str,
    code: str,
    volume: int,
    frozen: int,
    cost: float,
    *args,
    **kwargs,
) -> pd.Series:
    item = MPosition(
        portfolio_id=portfolio_id,
        code=code,
        volume=volume,
        frozen=frozen,
        cost=cost,
    )
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_positions(orders: List[MPosition], *args, **kwargs):
    l = []
    for i in orders:
        if isinstance(i, MPosition):
            l.append(i)
        else:
            GLOG.WANR("add orders only support position data.")
    return add_all(l)


def delete_position_by_id(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPosition
    try:
        filters = [model.uuid == id]
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_position_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_position_by_id(id: str, *argss, **kwargs):
    model = MPosition
    filters = [model.uuid == id]
    try:
        session = get_mysql_connection().session
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_adjustfactor_by_id: id {id} has more than one record.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def delete_position(portfolio_id: str, code: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.portfolio_id == portfolio_id, model.code == code]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_position_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_position(portfolio_id: str, code: str, *argss, **kwargs):
    model = MPosition
    filters = [model.portfolio_id == portfolio_id, model.code == code]
    try:
        session = get_mysql_connection().session
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"Portfolio:{portfolio_id} has more than one position about {code}.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def update_position_by_id(
    id: str,
    portfolio_id: Optional[str] = None,
    code: Optional[str] = None,
    volume: Optional[int] = None,
    frozen: Optional[int] = None,
    cost: Optional[float] = None,
    *args,
    **kwargs,
):
    model = MPosition
    session = get_mysql_connection().session
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if portfolio_id is not None:
        updates["portfolio_id"] = portfolio_id
    if code is not None:
        updates["code"] = code
    if volume is not None:
        updates["volume"] = volume
    if frozen is not None:
        updates["frozen"] = frozen
    if cost is not None:
        updates["cost"] = cost
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def update_position(
    portfolio_id: str,
    code: str,
    volume: Optional[int] = None,
    frozen: Optional[int] = None,
    cost: Optional[float] = None,
    *args,
    **kwargs,
):
    model = MPosition
    filters = [model.portfolio_id == portfolio_id, model.code == code]
    session = get_mysql_connection().session
    updates = {"update_at": datetime.datetime.now()}
    if volume is not None:
        updates["volume"] = volume
    if frozen is not None:
        updates["frozen"] = frozen
    if cost is not None:
        updates["cost"] = cost

    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_position_by_id(
    id: str,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            res = session.execute(stmt).scalars().first()
            return Position(
                portfolio_id=res.portfolio_id,
                code=res.code,
                volume=res.volume,
                frozen=res.frozen,
                cost=res.cost,
            )
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return None
    finally:
        get_mysql_connection().remove_session()


def get_positions(
    portfolio_id: str,
    code: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.portfolio_id == portfolio_id, model.is_del == False]
    if code is not None:
        filters.append(model.code == code)

    stmt = session.query(model).filter(and_(*filters))
    if page is not None and page_size is not None:
        stmt = stmt.offset(page * page_size).limit(page_size)

    try:
        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            res = session.execute(stmt).scalars().all()
            return [
                Position(
                    portfolio_id=i.portfolio_id,
                    code=i.code,
                    volume=i.volume,
                    frozen=i.frozen,
                    cost=i.cost,
                )
                for i in res
            ]
    except Exception as e:
        session.rollback()
        print(e)
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_mysql_connection().remove_session()
