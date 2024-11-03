import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union

from ginkgo.enums import EVENT_TYPES
from ginkgo.data.models import MEnginePortfolioMapping
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG


def add_engine_portfolio_mapping(engine_id: str, portfolio_id: str, *args, **kwargs) -> pd.Series:
    item = MEnginePortfolioMapping(engine_id=engine_id, portfolio_id=portfolio_id)
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_engine_portfolio_mappings(files: List[MEnginePortfolioMapping], *args, **kwargs):
    l = []
    for i in files:
        if isinstance(i, MEnginePortfolioMapping):
            l.append(i)
        else:
            GLOG.WANR("add files only support file data.")
    return add_all(l)


def upsert_engine_portfolio_mapping():
    pass


def upsert_engine_handler_mappings():
    pass


def delete_engine_portfolio_mapping(id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MEnginePortfolioMapping
    try:
        filters = [model.uuid == id]
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


def delete_engine_portfolio_mapping_by_engine_and_portfolio(engine_id: str, portfolio_id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MEnginePortfolioMapping
    filters = []
    filters.append(model.engine_id == engine_id)
    filters.append(model.portfolio_id == portfolio_id)
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


def delete_engine_portfolio_mappings(engine_id: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MEnginePortfolioMapping
    filters = [model.engine_id == engine_id]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord: id {ids} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_engine_portfolio_mapping(id: str, *argss, **kwargs):
    model = MEnginePortfolioMapping
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


def update_engine_portfolio_mapping(
    id: str,
    engine_id: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    *argss,
    **kwargs,
):
    model = MEnginePortfolioMapping
    filters = [model.uuid == id]
    session = get_mysql_connection().session
    updates = {"update_at": datetime.datetime.now()}
    if engine_id is not None:
        updates["engine_id"] = engine_id
    if portfolio_id is not None:
        updates["portfolio_id"] = portfolio_id
    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_engine_portfolio_mapping(
    id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MEnginePortfolioMapping
    filters = [model.uuid == id, model.is_del == False]

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


def get_engine_portfolio_mappings(
    engine_id: str,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MEnginePortfolioMapping
    filters = [model.engine_id == engine_id]

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
