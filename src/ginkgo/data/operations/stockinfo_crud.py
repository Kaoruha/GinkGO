import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union
from rich.console import Console

from ginkgo.enums import CURRENCY_TYPES, MARKET_TYPES, SOURCE_TYPES
from ginkgo.data.models import MStockInfo
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG, datetime_normalize, GCONF

console = Console()


def add_stockinfo(
    code: str,
    code_name: str,
    industry: str,
    currency: CURRENCY_TYPES,
    market: MARKET_TYPES,
    list_date: any,
    delist_date: any,
    *args,
    **kwargs,
) -> pd.Series:
    item = MStockInfo(
        code=code,
        code_name=code_name,
        industry=industry,
        currency=currency,
        market=market,
        list_date=datetime_normalize(list_date),
        delist_date=datetime_normalize(delist_date),
    )
    res = add(item)
    df = res.to_dataframe()
    get_mysql_connection().remove_session()
    return df.iloc[0]


def add_stockinfos(infos: List[MStockInfo], *args, **kwargs):
    l = []
    for i in infos:
        if isinstance(i, MStockInfo):
            l.append(i)
        else:
            GLOG.WANR("add stockinfos only support stockinfo data.")
    return add_all(l)


def upsert_stockinfo(
    code: str,
    code_name: str,
    industry: str,
    currency: CURRENCY_TYPES,
    market: MARKET_TYPES,
    list_date: any,
    delist_date: any,
    source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MStockInfo
    filters = []
    filters.append(model.is_del == False)
    filters.append(model.code == code)

    try:
        stmt = select(model).where(and_(*filters))
        res = session.execute(stmt).scalars().all()
        if len(res) == 0:
            # Insert
            return add_stockinfo(
                code=code,
                code_name=code_name,
                industry=industry,
                currency=currency,
                market=market,
                list_date=datetime_normalize(list_date),
                delist_date=datetime_normalize(delist_date) if delist_date else GCONF.DEFAULTEND,
                source=source,
            )
        else:
            # Update
            for i in res:
                i.update(
                    code,
                    code_name=code_name,
                    industry=industry,
                    currency=currency,
                    market=market,
                    list_date=list_date if list_date else GCONF.DEFAULTSTART,
                    delist_date=delist_date if delist_date else GCONF.DEFAULTEND,
                    source=source,
                )
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()


def upsert_stockinfos(infos: List[MStockInfo], *args, **kwargs):
    # TODO
    pass


def delete_stockinfo(code: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MStockInfo
    filters = [model.code == code]
    try:
        query = session.query(model).filter(and_(*filters)).all()
        if len(query) > 1:
            GLOG.WARN(f"delete_analyzerrecord_by_id: id {id} has more than one record.")
        for i in query:
            session.delete(i)
            session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def softdelete_stockinfo(code: str, *argss, **kwargs):
    model = MStockInfo
    filters = [model.code == code]
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


def update_stockinfo_filtered(
    code: str,
    code_name: Optional[str] = None,
    industry: Optional[str] = None,
    currency: Optional[CURRENCY_TYPES] = None,
    market: Optional[MARKET_TYPES] = None,
    list_date: Optional[any] = None,
    delist_date: Optional[any] = None,
    *argss,
    **kwargs,
):
    session = get_mysql_connection().session
    model = MStockInfo
    filters = [model.code == code]
    updates = {"update_at": datetime.datetime.now()}

    if code_name:
        updates["code_name"] = code_name
    if industry:
        updates["industry"] = industry
    if currency:
        updates["currency"] = currency
    if market:
        updates["market"] = market
    if list_date:
        updates["list_date"] = datetime_normalize(list_date)
    if delist_date:
        updates["delist_date"] = datetime_normalize(delist_date)

    try:
        stmt = update(model).where(and_(*filters)).values(updates)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_mysql_connection().remove_session()


def get_stockinfo(code: str, page_size: Optional[int] = None, *args, **kwargs):
    session = get_mysql_connection().session
    model = MStockInfo
    filters = []
    filters.append(model.is_del == False)
    filters.append(model.code == code)
    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        return df.iloc[0]
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()


def get_stockinfos_filtered(
    code: str = None,
    list_date: any = None,
    delist_date: any = None,
    industry:str =None,
    *args,
    **kwargs,
) -> pd.Series:
    session = get_mysql_connection().session
    model = MStockInfo
    filters = [model.is_del == False]
    if code is not None:
        filters.append(model.code == code)
    if list_date:
        list_date = datetime_normalize(list_date)
        filters.append(model.list_date == list_date)
    if delist_date:
        delist_date = datetime_normalize(delist_date)
        filters.append(model.delist_date == delist_date)
    if industry is not None:
        filters.append(model.industry == industry)

    try:
        stmt = session.query(model).filter(and_(*filters))

        df = pd.read_sql(stmt.statement, session.connection())
        console.print(f":moyai: [bold green]Got {df.shape[0]} records about StockInfo from mysql.[/]")
        if df.shape[0] == 0:
            return pd.DataFrame()
        return df.sort_values(by="code")
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_mysql_connection().remove_session()


def fget_stockinfos(filter: str = None, *args, **kwargs) -> pd.DataFrame:
    session = get_mysql_connection().session
    model = MStockInfo
    filters = [model.is_del == False]
    filters.append(or_(model.code.like(f"%{filter}%"), model.code_name.like(f"%{filter}%"), model.industry.like(f"%{filter}%")))
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
