import pandas as pd
from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.drivers import add,add_all, get_click_connection, GinkgoClickhouse
from ginkgo.data.models import MTick
from ginkgo.backtest import Tick
from ginkgo.enums import TICKDIRECTION_TYPES,
from ginkgo.libs.ginkgo_logger import GLOG


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
        *args,
        **kwargs,
        ) -> str:
    model = get_tick_model(code)
    item = model()
    item.set(code,price,volume, direction, timestamp)
    uuid = item.uuid
    add(item)
    return uuid

def add_ticks(ticks:List[Uniton[MTick,Tick]] = None, *args, **kwargs):
    l = []
    for i in ticks:
        if isinstance(i, MTick):
            l.append(i)
        elif isinstance(i, Tick):
            item = MTick()
            item.set(i.code,i.price,i.volume, i.direction, i.timestamp)
            l.append(item)
        else:
            GLOG.WARN("add ticks only support tick data.")
    return add_all(l)


def delete_tick_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs) -> int:
    conn = connection if connection else get_click_connection()
    model = get_tick_model(code)
    filters = [ model.uuid == id, ]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.delete()
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        pritn(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()

def delete_tick_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    conn = connection if connection else get_click_connection()
    model = get_tick_model(code)
    filters = [ model.code == code, ]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >=start_date)
    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <=end_date)
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


def softdelete_tick_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
        ) -> int:
    GLOG.WARN("Tick Data not support softdelete, run delete instead.")
    return delete_tick_by_codeanddate(code,start_date,end_date,connection,*args,**kwargs)


def update_tick(tick: Union[MTick, Tick], connection: Optional[GinkgoClickhouse] = None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    model = get_tick_model(code)
    code = tick.code
    time = datetime_normalize(tick.timestamp)
    filters = [
            model.code == code,
            model.timestamp == time
        ]
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

    add_tick(tick.code, tick.price, tick.volume, tick.direction, datetime_normalize(tick.timestamp))

def get_tick(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> Union[List[Tick], pd.DataFrame]:
    conn = connection if connection else get_click_connection()
    model = get_tick_model(code)
    filters = [
            model.code == code,
        ]

    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >=start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <=end_date)

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
                    item = Tick()
                    item.set(i['code'],i['price'],i['volume'],i['direction'],i['timestamp'])
                    res.append(item)
                return res
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()
