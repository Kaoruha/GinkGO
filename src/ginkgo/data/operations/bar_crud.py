import pandas as pd
from sqlalchemy import and_, delete, update, select, text
from typing import List, Optional, Union
from decimal import Decimal


from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.backtest import Bar
from ginkgo.data.models import MBar
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal

from rich.console import Console

console = Console()


def add_bar(
    code: str,
    open: Number,
    high: Number,
    low: Number,
    close: Number,
    volume: int,
    amount: Number,
    frequency: FREQUENCY_TYPES,
    timestamp: any,
    source: SOURCE_TYPES = SOURCE_TYPES.TUSHARE,
    *args,
    **kwargs,
) -> pd.Series:
    item = MBar(
        code=code,
        open=to_decimal(open),
        high=to_decimal(high),
        low=to_decimal(low),
        close=to_decimal(close),
        volume=volume,
        amount=to_decimal(amount),
        frequency=frequency,
        timestamp=datetime_normalize(timestamp),
        source=source,
    )
    res = add(item, *args, **kwargs)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_bars(bars: List[Union[Bar, MBar]], *args, **kwargs):
    l = []
    for i in bars:
        if isinstance(i, MBar):
            l.append(i)
        elif isinstance(i, Bar):
            item = MBar(i.code, i.open, i.high, i.low, i.close, i.volume, i.amount, i.frequency, i.datetime)
            l.append(item)
        else:
            GLOG.WARN("add bars only support bar data.")
    return add_all(l, *args, **kwargs)


def upsert_bars(bars: List[MBar], *args, **kwargs):
    date_list = []
    for i in bars:
        date_list.append(pd.Timestamp(i.timestamp))
    pass


def delete_bar(id: str, *args, **kwargs) -> None:
    session = get_click_connection().session
    model = MBar
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
        get_click_connection().remove_session()


def softdelete_bar(id: str, *args, **kwargs) -> None:
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_bar(id, *args, **kwargs)


def delete_bars_by_code_and_dates(code: str, dates: List[any], *args, **kwargs) -> None:
    session = get_click_connection().session
    model = MBar
    sql = f"DELETE FROM {model.__tablename__} WHERE code = :code"
    params = {"code": code}
    sql += " AND timestamp IN :dates"
    params["dates"] = [pd.Timestamp(datetime_normalize(i)) for i in dates]
    try:
        session.execute(text(sql), params)
        session.commit()
    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
    finally:
        get_click_connection().remove_session()


def delete_bars_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> None:
    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    session = get_click_connection().session
    model = MBar
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


def softdelete_bars_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> int:
    return delete_bars_by_code_and_date_range(code, start_date, end_date, *args, **kwargs)


def update_bar(code, timestamp, *args, **kwargs):
    # TODO Remove
    # TODO Reinsert
    pass


def get_bars(
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
        stmt = (
            session.query(model).filter(and_(*filters)).order_by(model.timestamp)
        )  # New api not work on dataframe convert

        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)

        if as_dataframe:
            df = pd.read_sql(stmt.statement, session.connection())
            console.print(f"[bold green]:flags: Got {df.shape[0]} records about {code} from clickhouse.[/]")
            if df.shape[0] > 0:
                df["source"] = SOURCE_TYPES.DATABASE
                df["code"] = df["code"].str.replace("\x00", "", regex=False)
            return df
        else:
            res = session.execute(stmt).scalars().all()
            console.print(f"[bold green]:flags: Got {len(res)} records about {code} from clickhouse.[/]")
            return [
                Bar(
                    code=i.code,
                    open=i.open,
                    high=i.high,
                    low=i.low,
                    close=i.close,
                    volume=i.volume,
                    amount=i.amount,
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
