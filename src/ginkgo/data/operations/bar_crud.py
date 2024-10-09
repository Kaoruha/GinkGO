import pandas as pd
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union


from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.backtest import Bar
from ginkgo.data.models import MBar
from ginkgo.libs import datetime_normalize, GLOG


def add_bar(
    code: str,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: int,
    frequency: FREQUENCY_TYPES,
    timestamp: any,
    source: SOURCE_TYPES = SOURCE_TYPES.TUSHARE,
    *args,
    **kwargs,
) -> None:
    item = MBar(
        code=code,
        open=open,
        high=high,
        close=close,
        volume=volume,
        frequency=frequency,
        timestamp=datetime_normalize(timestamp),
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_bars(bars: List[Union[Bar, MBar]], *args, **kwargs):
    l = []
    for i in bars:
        if isinstance(i, MBar):
            l.append(i)
        elif isinstance(i, Bar):
            item = MBar(i.code, i.open, i.high, i.low, i.close, i.volume, i.frequency, i.datetime)
            l.append(item)
        else:
            GLOG.WARN("add ticks only support tick data.")
    return add_all(l)


def delete_bar_by_id(id: str, *args, **kwargs) -> None:
    session = get_click_connection().session
    model = MBar
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
        get_click_connection().remove_session()


def softdelete_bar_by_id(id: str, *args, **kwargs) -> None:
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_bar_by_id(id, *args, **kwargs)


def delete_bar_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> None:
    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    model = MBar
    sql = f"DELETE FROM {model.__tablename__} WHERE code = :code"
    params = {"code": code}
    session = get_click_connection().session
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


def softdelete_bar_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    return delete_bar_by_code_and_date_range(code, start_date, end_date, *args, **kwargs)


def update_bar():
    # TODO Remove
    # TODO Reinsert
    pass


def get_bar(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    as_dataframe: bool = False,
    *args,
    **kwargs,
) -> Union[List[Bar], pd.DataFrame]:
    session = get_click_connection().session
    model = MBar
    filters = [model.code == code]

    if start_date is not None:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date is not None:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        stmt = session.query(model).filter(and_(*filters))  # New api not work on dataframe convert

        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)
        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            return df
        else:
            # stmt = select(model).where(and_(*filters))
            res = session.execute(stmt).scalars().all()
            return [
                Bar(
                    code=i.code,
                    open=i.open,
                    high=i.high,
                    low=i.low,
                    close=i.close,
                    volume=i.volume,
                    frequency=i.frequency,
                    timestamp=i.timestamp,
                )
                for i in res
            ]

    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        if as_dataframe:
            return pd.DataFrame()
        else:
            return []
    finally:
        get_click_connection().remove_session()
