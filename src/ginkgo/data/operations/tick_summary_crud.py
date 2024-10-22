import pandas as pd
from typing import List, Optional, Union
from sqlalchemy import and_

from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.data.models import MTickSummary
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES


def add_tick_summary(
    code: str,
    price: Number,
    volume: int,
    timestamp: any,
    source: SOURCE_TYPES = SOURCE_TYPES.TDX,
    *args,
    **kwargs,
) -> str:
    model = MTickSummary
    item = model(
        code=code,
        price=to_decimal(price),
        volume=volume,
        timestamp=datetime_normalize(timestamp),
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_tick_summarys(tick_summarys: List[MTickSummary] = None, *args, **kwargs):
    model = MTickSummary
    l = []
    for i in tick_summarys:
        l.append(i)
    return add_all(l)


def delete_tick_summary_by_id(id: str, *args, **kwargs) -> int:
    session = get_click_connection().session
    model = MTickSummary
    filters = [model.uuid == id]
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
        get_click_connection().remove_session()


def softdelete_tick_summary_by_id(id: str, *args, **kwargs) -> int:
    GLOG.WARN("Tick Summary not support softdelete, run delete instead.")
    return delete_tick_summary_by_id(id)


def delete_tick_summary_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    session = get_click_connection().session
    model = MTickSummary
    filters = [model.code == code]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)
    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        stmt = delete(model).where(and_(*filters))
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def softdelete_tick_summary_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    GLOG.WARN("TickSummary Data not support softdelete, run delete instead.")
    return delete_tick_summary_by_code_and_date_range(code, start_date, end_date, connection, *args, **kwargs)


def update_tick_summary(tick_summary, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs):
    # TODO
    pass


def get_tick_summarys(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_click_connection().session
    model = MTickSummary
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
