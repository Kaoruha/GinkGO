import pandas as pd
from typing import List, Optional, Union
from sqlalchemy import and_, text

from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.data.models import MTick, MClickBase
from ginkgo.backtest import Tick
from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal

tick_model = {}


def get_tick_model(code: str, *args, **kwargs) -> type:
    """
    Tick data can not be stored in one table.
    Do database partitioning first.
    Class of Tick model will generate dynamically.
    Args:
        code(str): stock code
    Returns:
        Model of Tick
    """
    global tick_model
    name = f"{code.replace('.', '_')}_Tick"
    if name not in tick_model.keys():
        newclass = type(
            name,
            (MTick,),
            {
                "__tablename__": name,
                "__abstract__": False,
            },
        )
        tick_model[name] = newclass
    return tick_model[name]


def add_tick(
    code: str,
    price: Number,
    volume: int,
    direction: TICKDIRECTION_TYPES,
    timestamp: any,
    source: SOURCE_TYPES = SOURCE_TYPES.TDX,
    *args,
    **kwargs,
) -> str:
    model = get_tick_model(code)
    item = model(
        code=code,
        price=to_decimal(price),
        volume=volume,
        direction=direction,
        timestamp=datetime_normalize(timestamp),
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_ticks(ticks: List[Tick] = None, *args, **kwargs):
    l = {}
    for i in ticks:
        code = i.code
        if code not in l.keys():
            l[code] = []
        model = get_tick_model(code)
        item = model(
            code=code,
            price=i.price,
            volume=i.volume,
            direction=i.direction,
            timestamp=datetime_normalize(i.timestamp),
            source=i.source,
        )
        l[code].append(item)
    for k, v in l.items():
        add_all(v, *args, **kwargs)


def delete_ticks(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> None:
    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    session = get_click_connection().session
    model = get_tick_model(code)
    sql = f"DELETE FROM `{model.__tablename__}` WHERE code = :code"
    params = {"code": code}
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


def softdelete_tick_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    GLOG.WARN("Tick Data not support softdelete, run delete instead.")
    return delete_tick_by_code_and_date_range(code, start_date, end_date, connection, *args, **kwargs)


def update_tick(tick: Union[MTick, Tick], connection: Optional[GinkgoClickhouse] = None, *args, **kwargs):
    # TODO
    pass


def get_ticks(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> Union[List[Tick], pd.DataFrame]:
    session = get_click_connection().session
    model = get_tick_model(code)
    filters = [model.code == code]

    if start_date is not None:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date is not None:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    stmt = session.query(model).filter(and_(*filters))  # New api not work on dataframe convert
    if page is not None and page_size is not None:
        stmt = stmt.offset(page * page_size).limit(page_size)
    else:
        if start_date is None and end_date is None:
            GLOG.WARN("Get Ticks with out date range and pagination is not suggeted.")
            return pd.DataFrame() if as_dataframe else None
    try:

        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            # stmt = select(model).where(and_(*filters))
            res = session.execute(stmt).scalars().all()
            return [Tick(code=i.code, price=i.price, volume=i.volume, direction=i.direction) for i in res]

    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_click_connection().remove_session()
