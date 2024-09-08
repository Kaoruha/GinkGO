from sqlalchemy import and_
from ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.backtest import Bar
from ginkgo.data.models import MBar


def add_bar(
    code: str,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: int,
    frequency: FREQUENCY_TYPES,
    datetime: any,
    *args,
    **kwargs,
) -> None:
    item = MBar()
    item.set(code, open, high, low, close, volume, frequency, datetime_normalize(datetime))
    uuid = item.uuid
    add(item)
    return uuid


def add_bars(bars: List[Union[Bar, MBar]], *args, **kwargs):
    l = []
    for i in bars:
        if isinstance(i, MBar):
            l.append(i)
        elif isinstance(i, Bar):
            item = MBar()
            item.set(i.code, i.open, i.high, i.low, i.close, i.volume, i.frequency, i.datetime)
            l.append(item)
        else:
            GLOG.WARN("add ticks only support tick data.")
    return add_all(l)


def delete_bar_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs) -> int:
    conn = connection if connection else get_click_connection()
    model = MBar
    filters = [model.uuid == id]
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


def softdelete_bar_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs) -> int:
    delete_bar_by_id(id, connection, *args, **kwargs)


def delete_bar_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoMysql] = None,
    *args,
    **kwargs,
) -> int:
    conn = connection if connection else get_click_connection()
    model = MBar
    filters = [model.code == code]
    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.delete()
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def softdelete_bar_by_code_and_date_range(
    code: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoMysql] = None,
    *args,
    **kwargs,
) -> int:
    delete_bar_by_code_and_date_range(code, start_date, end_date, connection, *args, **kwargs)


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
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> Union[List[Tick], pd.DataFrame]:
    conn = connection if connection else get_click_connection()
    model = MBar
    filters = [model.code == code]

    if start_date:
        start_date = datetime_normalize(start_date)
        filters.append(model.timestamp >= start_date)

    if end_date:
        end_date = datetime_normalize(end_date)
        filters.append(model.timestamp <= end_date)

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
                    item.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
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
