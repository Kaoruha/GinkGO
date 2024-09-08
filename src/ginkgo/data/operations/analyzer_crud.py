from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.drivers import add, add_all, get_mysql_connection, GinkgoMysql
from ginkgo.data.models import MAnalyzer
from ginkgo.libs import datetime_normalize


def add_analyzer(portfolio_id:str, timestamp:any, value:float, name:str, analyzer_id:str="", *args, **kwargs):
    item = MAnalyzer()
    item.set(portfolio_id,datetime_normalize(timestamp), value, name, analyzer_id )
    uuid = item.uuid
    add(item)
    return uuid

def add_analyzers(List[Union[MAnalyzer]]):
    l = []
    for i in records:
        if isinstance(i, MAnalyzer):
            l.append(i)
    return add_all(l)


def delete_analyzer_by_id(id:str, *args,**kwargs):
    conn = connection if connection else get_click_connection()
    model = MAnalyzer
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

def softdelete_analyzer_by_id(id:str, *args, **kwargs):
    delete_analyzer_by_id(id, *args, **kwargs)

def delete_analyzer_by_portfolio_id_and_analyzer_id(portfolio_id:str, analyzer_id:Optional[str]=None, *args, **kwargs):
    conn = connection if connection else get_click_connection()
    model = MAnalyzer
    filters = [model.portfolio_id == portfolio_id]
    if analyzer_id:
        filters.append(model.analyzer_id == analyzer_id)
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


def softdelete_analyzer_by_portfolio_id_and_analyzer_id(portfolio_id:str, analyzer_id:Optional[str]=None, *args, **kwargs):
    delete_analyzer_by_portfolio_id_and_analyzer_id(portfolio_id, analyzer_id, *args, **kwargs)

def update_analyzer():
    pass


def get_analyzer_by_portfolio_id(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> Union[List[MTransfer], pd.DataFrame]:
    conn = connection if connection else get_click_connection()
    model = MAnalyzer
    filters = [model.portfolio_id == portfolio_id, model.isdel == False]

    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append( model.timestamp >=start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append( model.timestamp <= end_date)

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
            res = query.all()
            if len(query) == 0:
                return []
            else:
                return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return []
    finally:
        conn.close_session()
