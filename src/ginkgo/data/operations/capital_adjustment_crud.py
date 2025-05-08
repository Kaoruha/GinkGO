import pandas as pd
from typing import List, Optional, Union
from sqlalchemy import and_, text

from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.data.models import MCapitalAdjustment
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES, CAPITALADJUSTMENT_TYPES


def add_capital_adjustment(
    code: str,
    timestamp: any,
    type: CAPITALADJUSTMENT_TYPES = None,
    fenhong: Optional[Number] = None,
    peigujia: Optional[Number] = None,
    songzhuangu: Optional[Number] = None,
    peigu: Optional[Number] = None,
    suogu: Optional[Number] = None,
    panqianliutong: Optional[Number] = None,
    panhouliutong: Optional[Number] = None,
    qianzongguben: Optional[Number] = None,
    houzongguben: Optional[Number] = None,
    fenshu: Optional[Number] = None,
    xingquanjia: Optional[Number] = None,
    source: SOURCE_TYPES = SOURCE_TYPES.TDX,
    *args,
    **kwargs,
) -> pd.Series:
    model = MCapitalAdjustment
    item = model(
        code=code,
        timestamp=datetime_normalize(timestamp),
        type=type,
        fenhong=fenhong,
        peigujia=peigujia,
        songzhuangu=songzhuangu,
        peigu=peigu,
        suogu=suogu,
        panqianliutong=panqianliutong,
        panhouliutong=panhouliutong,
        qianzongguben=qianzongguben,
        houzongguben=houzongguben,
        fenshu=fenshu,
        xingquanjia=xingquanjia,
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_capital_adjustments(capital_adjustments: List[MCapitalAdjustment], *args, **kwargs):
    model = MCapitalAdjustment
    l = []
    for i in capital_adjustments:
        l.append(i)
    return add_all(l)


def delete_capital_adjustment(id: str, *args, **kwargs) -> None:
    session = get_click_connection().session
    model = MCapitalAdjustment
    sql = f"DELETE FROM {model.__tablename__} WHERE uuid = :id"
    params = {"id": id}
    try:
        session.execute(text(sql), params)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def softdelete_capital_adjustment(id: str, *args, **kwargs) -> None:
    GLOG.WARN("TickSummary Data not support softdelete, run delete instead.")
    return delete_capital_adjustment(id=id, *args, **kwargs)


def delete_capital_adjustments_filtered(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    session = get_click_connection().session
    model = MCapitalAdjustment
    sql = f"DELETE FROM {model.__tablename__} WHERE code = :code"
    params = {"code": code}
    if start_date is not None:
        sql += " AND timestamp >= :start_date"
        params["start_date"] = datetime_normalize(start_date)
    if end_date is not None:
        sql += " AND timestamp <= :end_date"
        params["end_date"] = datetime_normalize(end_date)
    try:
        session.execute(text(sql), params)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def softdelete_capital_adjustments_filtered(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    GLOG.WARN("TickSummary Data not support softdelete, run delete instead.")
    return delete_capital_adjustments_by_code_and_date_range(code, start_date, end_date, connection, *args, **kwargs)


def update_capital_adjustment(capital_adjustment, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs):
    # TODO Remove
    # TODO Reinsert
    pass


def get_capital_adjustments_page_filtered(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_click_connection().session
    model = MCapitalAdjustment
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
        df = pd.read_sql(stmt.statement, session.connection())
        return df
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_click_connection().remove_session()
