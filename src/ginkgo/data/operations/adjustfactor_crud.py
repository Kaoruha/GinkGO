from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.drivers import add, add_all, get_mysql_connection, GinkgoMysql
from ginkgo.data.models import MAdjustfactor
from ginkgo.backtest import Adjsutfactor


def add_adjustfactor(
    code: str,
    foreadjustfactor: float,
    backadjustfactor: float,
    adjustfactor: float,
    connection: Optional[GinkgoMysql] = None,
    *args,
    **kwargs
) -> str:
    item = MAdjustfactor()
    item.set(code, foreadjustfactor, backadjustfactor, adjustfactor)
    uuid = item.uuid
    add(item)
    return uuid


def add_adjustfactors(adjustfactors: List[Union[Adjsutfactor, MAdjustfactor]], *args, **kwargs) -> int:
    l = []
    for i in adjustfactors:
        if isinstance(i, MAdjustfactor):
            l.append(i)
        elif isinstance(i, Adjsutfactor):
            item = MAdjustfactor()
            item.set(i.code, i.foreadjustfactor, i.backadjustfactor, i.adjustfactor, i.timestamp)
            l.append(item)
        else:
            GLOG.WARN("add ticks only support tick data.")
    return add_all(l)


def delete_adjustfactor_by_id(id: str, connection: Optional[GinkgoMysql] = None, *args, **kwargs) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.uuid == id]
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


def softdelete_adjustfactor_by_id(id: str, connection: Optional[GinkgoMysql] = None, *args, **kwargs) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.uuid == id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        res.delete()
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        pritn(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()
    pass


def delete_adjustfactor_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoMysql] = None,
    *args,
    **kwargs
) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.code == code]
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


def softdelete_adjustfactor_by_code_and_date_range(
    code: str, start_date: any, end_date: any, connection: GinkgoMysql = None, *args, **kwargs
) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.code == code]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.all()
        for i in res:
            i.delete()
            conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def update_adjustfactor_by_id(
    id: str,
    code: str,
    foreadjustfactor: float,
    backadjustfactor: float,
    adjustfactor: float,
    timestamp: any,
    connection: GinkgoMysql = None,
    *args,
    **kwargs
) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.uuid == id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        res.code = code
        res.foreadjustfactor = foreadjustfactor
        res.backadjustfactor = backadjustfactor
        res.adjustfactor = adjustfactor
        res.timestamp = datetime_normalize(timestamp)
        conn.session.commit()
        return 1
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def update_adjustfactor_by_code_date(
    code: str,
    date: any,
    foreadjustfactor: float,
    backadjustfactor: float,
    adjustfactor: float,
    timestamp: any,
    connection: GinkgoMysql = None,
    *args,
    **kwargs
) -> int:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.uuid == id, model.code == code, model.timestamp == datetime_normalize(date)]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        res.code = code
        res.foreadjustfactor = foreadjustfactor
        res.backadjustfactor = backadjustfactor
        res.adjustfactor = adjustfactor
        res.timestamp = datetime_normalize(timestamp)
        conn.session.commit()
        return 1
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def get_adjustfactor_by_id(id: str, *args, connection: GinkgoMysql = None, **kwargs) -> Adjsutfactor:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.uuid == id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        item = Adjsutfactor()
        item.set(res)
        return item
    except Exception as e:
        conn.session.rollback()
        pritn(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()
    pass


def get_adjustfactor_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: GinkgoMysql = None,
    *args,
    **kwargs
) -> List[Adjsutfactor]:
    conn = connection if connection else get_mysql_connection()
    model = MAdjustfactor
    filters = [model.code == code, model.isdel == False]

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
                    item = Adjsutfactor(i.code, i.foreadjustfactor, i.backadjustfactor, i.adjustfactor, i.timestamp)
                    res.append(item)
                return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return []
    finally:
        conn.close_session()
