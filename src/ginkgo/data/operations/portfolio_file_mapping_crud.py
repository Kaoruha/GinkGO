import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import EVENT_TYPES, FILE_TYPES
from ginkgo.data.models import MPortfolioFileMapping
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG


def add_portfolio_file_mapping(
    portfolio_id: str, file_id: str, name: str, type: FILE_TYPES, *args, **kwargs
) -> pd.Series:
    item = MPortfolioFileMapping(portfolio_id=portfolio_id, file_id=file_id, type=type, name=name)
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_portfolio_file_mappings(files: List[MPortfolioFileMapping], *args, **kwargs):
    l = []
    for i in files:
        if isinstance(i, MPortfolioFileMapping):
            l.append(i)
        else:
            GLOG.WANR("add files only support file data.")
    return add_all(l)


def delete_portfolio_file_mapping(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolioFileMapping
    filters = [model.uuid == id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_portfolio_file_mapping(id: str, *argss, **kwargs):
    model = MPortfolioFileMapping
    filters = [model.uuid == id]
    session = get_mysql_connection().session
    updates = {"is_del": True, "update_at": datetime.datetime.now()}
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def delete_portfolio_file_mappings_by_portfolio(portfolio_id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolioFileMapping
    filters = [model.portfolio_id == portfolio_id]
    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_portfolio_file_mappings_by_portfolio(portfolio_id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolioFileMapping
    filters = [model.portfolio_id == portfolio_id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord: id {ids} has more than one record.")
        for i in query:
            i.is_del = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def update_portfolio_file_mapping(
    id: str,
    portfolio_id: Optional[str] = None,
    file_id: Optional[str] = None,
    name: Optional[str] = None,
    type: Optional[FILE_TYPES] = None,
    *argss,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MPortfolioFileMapping
    filters = [model.uuid == id]
    updates = {"update_at": datetime.datetime.now()}
    if portfolio_id is not None:
        updates["portfolio_id"] = portfolio_id
    if file_id is not None:
        updates["file_id"] = file_id
    if name is not None:
        updates["name"] = name
    if type is not None:
        updates["type"] = type
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_portfolio_file_mapping(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPortfolioFileMapping
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


def get_portfolio_file_mappings(
    portfolio_id: str,
    type: Optional[FILE_TYPES] = None,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPortfolioFileMapping
    filters = [model.portfolio_id == portfolio_id, model.is_del == False]
    if type is not None:
        filters.append(model.type == type)

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df
    except Exception as e:
        session.rollback()
        print(e)
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()


def get_portfolio_file_mappings_fuzzy(
    name: str = None,
    type: FILE_TYPES = None,
    *args,
    **kwargs,
) -> pd.Series:
    # TODO Unittest
    session = get_mysql_connection().session
    model = MPortfolioFileMapping
    filters = [model.is_del == False]
    if name is not None:
        filters.append(model.name.like(f"%{name}%"))
    if type is not None:
        filters.append(model.type == type)

    try:
        stmt = session.query(model).filter(and_(*filters))

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
