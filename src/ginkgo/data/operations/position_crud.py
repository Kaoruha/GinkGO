import pandas as pd
import datetime
from decimal import Decimal
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.data.models import MPosition
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG, datetime_normalize, Number, to_decimal
from ginkgo.backtest import Position


def add_position(
    portfolio_id: str,
    engine_id: str,
    code: str,
    cost: Number,
    volume: int,
    frozen_volume: int,
    frozen_money: Number,
    price: Union[float, Decimal],
    fee: Union[float, Decimal],
    *args,
    **kwargs,
) -> pd.Series:
    item = MPosition(
        portfolio_id=portfolio_id,
        engine_id=engine_id,
        code=code,
        volume=volume,
        frozen_volume=frozen_volume,
        frozen_money=to_decimal(frozen_volume),
        cost=to_decimal(cost),
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
            GLOG.WANR("add positions only support position data.")
    return add_all(l)


def delete_position(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_position: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_position(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPosition
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


def delete_positions_filtered(portfolio_id: str, engine_id: str = None, code: str = None, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.portfolio_id == portfolio_id]

    if engine_id is not None:
        filters.append(model.engine_id == engine_id)
    if code is not None:
        filters.append(model.code == code)

    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_positions_filtered(portfolio_id: str, engine_id: str = None, code: str = None, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.portfolio_id == portfolio_id]
    if engine_id is not None:
        filters.append(model.engine_id == engine_id)
    if code is not None:
        filters.append(model.code == code)
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"Portfolio:{portfolio_id} has more than one position about {code}.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def update_position(
    id: str,
    portfolio_id: Optional[str] = None,
    engine_id: Optional[str] = None,
    code: Optional[str] = None,
    cost: Optional[float] = None,
    volume: Optional[int] = None,
    frozen_volume: Optional[int] = None,
    frozen_money: Optional[Number] = None,
    price: Union[float, Decimal] = None,
    fee: Union[float, Decimal] = None,
    *args,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}

    if portfolio_id is not None:
        updates["portfolio_id"] = portfolio_id
    if engine_id is not None:
        updates["engine_id"] = engine_id
    if code is not None:
        updates["code"] = code
    if cost is not None:
        updates["cost"] = cost
    if volume is not None:
        updates["volume"] = volume
    if frozen_volume is not None:
        updates["frozen_volume"] = frozen_volume
    if frozen_money is not None:
        updates["frozen_money"] = to_decimal(frozen_money)
    if price is not None:
        updates["price"] = to_decimal(price)
    if fee is not None:
        updates["fee"] = to_decimal(fee)

    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


# TODO Upgrade
def update_position_filtered(
    portfolio_id: str,
    engine_id: str = None,
    code: str = None,
    cost: Optional[float] = None,
    volume: Optional[int] = None,
    frozen_volume: Optional[int] = None,
    frozen_money: Optional[Number] = None,
    price: Union[float, Decimal] = None,
    fee: Union[float, Decimal] = None,
    *args,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MPosition
    filters = [model.portfolio_id == portfolio_id]
    updates = {"update_at": datetime.datetime.now()}

    if engine_id is not None:
        filters.append(model.engine_id == engine_id)
    if code is not None:
        filters.append(model.code == code)

    if cost is not None:
        updates["cost"] = cost
    if volume is not None:
        updates["volume"] = volume
    if frozen_volume is not None:
        updates["frozen_volume"] = frozen_volume
    if frozen_money is not None:
        updates["frozen_money"] = to_decimal(frozen_money)
    if price is not None:
        updates["price"] = to_decimal(price)
    if fee is not None:
        updates["fee"] = to_decimal(fee)

    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_position(
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
                engine_id=res.engine_id,
                code=res.code,
                cost=res.cost,
                volume=res.volume,
                frozen_volume=res.frozen_volume,
                frozen_money=res.frozen_money,
                fee=res.fee,
                uuid=res.uuid,
            )
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        import pdb

        pdb.set_trace()
        if as_dataframe:
            return pd.DataFrame()
        else:
            return None
    finally:
        get_mysql_connection().remove_session()


def get_positions_page_filtered(
    portfolio_id: str,
    engine_id: Optional[str] = None,
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
    if engine_id is not None:
        filters.append(model.engine_id == engine_id)
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
                    engine_id=engine_id,
                    code=i.code,
                    cost=i.cost,
                    volume=i.volume,
                    frozen_volume=i.frozen_volume,
                    frozen_money=i.frozen_money,
                    fee=i.fee,
                    uuid=i.uuid,
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
