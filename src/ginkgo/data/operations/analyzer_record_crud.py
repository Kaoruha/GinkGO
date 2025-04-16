import pandas as pd
from decimal import Decimal
from typing import List, Optional, Union
from sqlalchemy import and_, delete, update, select, text

from ginkgo.data.drivers import add, add_all, get_click_connection
from ginkgo.data.models import MAnalyzerRecord
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES


def add_analyzer_record(
    portfolio_id: str,
    timestamp: any,
    value: Number,
    name: str,
    analyzer_id: str = "",
    source=SOURCE_TYPES.TUSHARE,
    *args,
    **kwargs,
) -> pd.Series:
    item = MAnalyzerRecord(
        portfolio_id=portfolio_id,
        timestamp=datetime_normalize(timestamp),
        value=to_decimal(value),
        name=name,
        analyzer_id=analyzer_id,
        source=source,
    )
    res = add(item)
    df = res.to_dataframe()
    get_click_connection().remove_session()
    return df.iloc[0]


def add_analyzer_records(records: List[MAnalyzerRecord]) -> None:
    l = []
    for i in records:
        if isinstance(i, MAnalyzerRecord):
            l.append(i)
        else:
            GLOG.WARN("add analyzer records only support model_analyzer_record.")
    return add_all(l)


def delete_analyzer_record(id: str, *args, **kwargs) -> None:
    session = get_click_connection().session
    model = MAnalyzerRecord
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
        get_click_connection().remove_session()


def softdelete_analyzer_record(id: str, *args, **kwargs) -> None:
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    return delete_analyzer_record(id, *args, **kwargs)


def delete_analyzer_records_by_portfolio_analyzer_and_date_range(
    portfolio_id: str,
    analyzer_id: Optional[str] = None,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
) -> None:
    # Sqlalchemy ORM seems not work on clickhouse when multi delete.
    # Use sql
    session = get_click_connection().session
    model = MAnalyzerRecord
    sql = f"DELETE FROM {model.__tablename__} WHERE portfolio_id = :portfolio_id"
    params = {"portfolio_id": portfolio_id}
    if analyzer_id is not None:
        sql += " AND analyzer_id = :analyzer_id"
        params["analyzer_id"] = analyzer_id
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


def softdelete_analyzer_records_by_portfolio_analyzer_and_date_range(
    portfolio_id: str,
    analyzer_id: Optional[str] = None,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    *args,
    **kwargs,
):
    GLOG.WARN("Soft delete not work in clickhouse, use delete instead.")
    delete_analyzer_records_by_portfolio_analyzer_and_date_range(
        portfolio_id, analyzer_id, start_date, end_date, *args, **kwargs
    )


def update_analyzer_record(self, *args, **kwargs):
    # TODO
    # Remove
    # Reinsert
    pass

def get_analyzer_record():
    pass

def get_analyzer_records(
    portfolio_id: str,
    analyzer_id: Optional[str] = None,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    *args,
    **kwargs,
) -> pd.DataFrame:
    session = get_click_connection().session
    model = MAnalyzerRecord
    filters = [model.portfolio_id == portfolio_id]

    if analyzer_id is not None:
        filters.append(model.analyzer_id == analyzer_id)

    if start_date is not None:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date is not None:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        stmt = session.query(model).filter(and_(*filters))

        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size).limit(page_size)

        df = pd.read_sql(stmt.statement, session.connection())
        return df

    except Exception as e:
        session.rollback()
        GLOG.ERROR(e)
        return pd.DataFrame()
    finally:
        get_click_connection().remove_session()
