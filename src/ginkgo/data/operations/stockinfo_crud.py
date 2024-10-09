import pandas as pd
import datetime
from sqlalchemy import and_, delete, update, select, text, or_
from typing import List, Optional, Union

from ginkgo.enums import CURRENCY_TYPES, MARKET_TYPES
from ginkgo.data.models import MStockInfo
from ginkgo.data.drivers import add, add_all, get_mysql_connection
from ginkgo.libs import GLOG


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


def add_stockinfos(files: List[MStockInfo], *args, **kwargs):
    l = []
    for i in files:
        if isinstance(i, MStockInfo):
            l.append(i)
        else:
            GLOG.WANR("add files only support file data.")
    return add_all(l)


def delete_stockinfo(code: str, *argss, **kwargs):
    session = get_mysql_connection().session
    model = MStockInfo
    try:
        filters = [model.code == code]
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


def update_stockinfo(
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

    model = MStockInfo
    filters = [model.code == code]
    session = get_mysql_connection().session
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


def get_stockinfo(
    code: str = None,
    list_date: any = None,
    delist_date: any = None,
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
