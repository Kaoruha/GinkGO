from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.enums import CURRENCY_TYPES
from ginkgo.libs import datetime_normalize
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.data.models import MStockInfo
from ginkgo.backtest.stockinfo import StockInfo


def add_stockinfo(
    code: str,
    code_name: str,
    insdutry: str,
    currency: CURRENCY_TYPES,
    list_date: any,
    delist_date: any,
    *args,
    **kwargs,
):
    item = MStockInfo()
    item.set(code, code_name, insdutry, currency, datetime_normalize(list_date), datetime_normalize(delist_date))
    uuid = item.uuid
    add(item)
    return uuid


def add_stockinfos(stockinfos: List[Union[StockInfo, MStockInfo]], *args, **kwargs) -> None:
    l = []
    for i in stockinfos:
        if isinstance(i, MStockInfo):
            l.append(i)
        elif isinstance(i, StockInfo):
            item = MStockInfo()
            item.set(i.code, i.code_name, i.industry, i.currency, i.list_date, i.delist_date)
            l.append(item)
        else:
            GLOG.WARN("add stockinfos just support stockinfo data.")
    return add_all(l)


def delelte_stockinfo(
    code: str,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
):
    conn = connection if connection else get_click_connection()
    model = MStockInfo
    filters = [ model.code == code, ]
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


def softdelelte_stockinfo(
    code: str,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
):
    GLOG.WARN("Tick Data not support softdelete, run delete instead.")
    return delelte_stockinfo(code, connection, *args, **kwargs)


def update_stockinfo(
    code: str,
    code_name: str,
    insdutry: str,
    currency: CURRENCY_TYPES,
    list_date: any,
    delist_date: any,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
):
    pass


def get_stockinfo(
    code: Optional[str] = None,
    code_name: Optional[str] = None,
    industry: Optional[str] = None,
    currency: Optional[CURRENCY_TYPES] = None,
    list_date: Optional[any] = None,
    delist_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: Optional[bool] = False.
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
):
    conn = connection if connection else get_click_connection()
    model = MStockInfo
    filters = []
    if code:
        filters.append(model.code.like(f"%{code}%"))

    if code_name:
        filters.append(model.code_name.like(f"%{code_name}%"))

    if currency:
        filters.append(model.currency == currency)

    if list_date:
        list_date = datetime_normalize(list_date)
        filters.append(model.timestamp >= list_date)

    if delist_date:
        delist_date = datetime_normalize(delist_date)
        filters.append(model.timestamp <= delist_date)

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
