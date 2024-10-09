import pandas as pd
from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.data.models import MTick, MClickBase
from ginkgo.backtest import Tick
from ginkgo.enums import TICKDIRECTION_TYPES
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import datetime_normalize


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
    name = f"{code}.Tick"
    newclass = type(
        name,
        (MTick,),
        {
            "__tablename__": name,
            "__abstract__": False,
        },
    )
    return newclass


def add_tick(
    code: str,
    price: float,
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
        price=price,
        volume=volume,
        direction=direction,
        timestamp=datetime_normalize(timestamp),
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_ticks(ticks: List[Union[MTick, Tick]] = None, *args, **kwargs):
    l = {}
    for i in ticks:
        code = i.code
        if code not in l.keys():
            l[code] = []
        model = get_tick_model(code)
        item = model(
            code=code,
            price=price,
            volume=volume,
            direction=direction,
            timestamp=datetime_normalize(timestamp),
            source=source,
        )
        l[code].append(item)
    for k, v in l.items():
        add_all(v)


def delete_tick_by_id(id: str, *args, **kwargs) -> int:
    session = get_click_connection().session
    model = get_tick_model(code)
    filters = [model.uuid == id]
    try:
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


def delete_tick_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    session = get_click_connection().session
    model = get_tick_model(code)
    filters = [model.code == code]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)
    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)
    try:
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


def get_tick(
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
    try:

        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            # stmt = select(model).where(and_(*filters))
            res = session.execute(stmt).scalars().all()
            return [Tick(code=code, price=price, volume=volume, direction=direction) for i in res]

    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_click_connection().remove_session()
