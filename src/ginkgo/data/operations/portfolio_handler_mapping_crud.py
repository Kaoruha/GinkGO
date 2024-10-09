import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union

from ginkgo.enums import EVENT_TYPES
from ginkgo.data.models import MPortfolioHandlerMapping
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG


def add_portfolio_handler_mapping(
    portfolio_id: str, handler_id: str, type: EVENT_TYPES, name: str, *args, **kwargs
) -> pd.Series:
    item = MPortfolioHandlerMapping(portfolio_id=portfolio_id, handler_id=handler_id, type=type, name=name)
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_portfolio_handler_mappings(handlers: List[MPortfolioHandlerMapping], *args, **kwargs):
    l = []
    for i in handlers:
        if isinstance(i, MPortfolioHandlerMapping):
            l.append(i)
        else:
            GLOG.WANR("add handlers only support handler data.")
    return add_all(l)


def delete_portfolio_handler_mapping(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolioHandlerMapping
    try:
        filters = [model.uuid == id]
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
        get_mysql_connection().remove_session()


def delete_portfolio_handler_mappings(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MPortfolioHandlerMapping
    filters = [model.portfolio_id == i]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord_by_id: id {ids} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_portfolio_handler_mapping(id: str, *argss, **kwargs):
    model = MPortfolioHandlerMapping
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


def update_portfolio_handler_mapping(
    id: str,
    portfolio_id: Optional[str] = None,
    handler_id: Optional[str] = None,
    type: Optional[EVENT_TYPES] = None,
    name: Optional[str] = None,
    *argss,
    **kwargs,
):
    model = MPortfolioHandlerMapping
    filters = [model.uuid == id]
    session = get_mysql_connection().session
    updates = {"update_at": datetime.datetime.now()}
    if portfolio_id is not None:
        updates["portfolio_id"] = portfolio_id
    if handler_id is not None:
        updates["handler_id"] = handler_id
    if type is not None:
        updates["type"] = type
    if name is not None:
        updates["name"] = name
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_portfolio_handler_mapping_by_id(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPortfolioHandlerMapping
    filters = [model.uuid == id]

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df.iloc[0]
    except Exception as e:
        session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        get_mysql_connection().remove_session()


def get_portfolio_handler_mappings(
    portfolio_id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MPortfolioHandlerMapping
    filters = [model.portfolio_id == portfolio_id, model.is_del == False]

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
