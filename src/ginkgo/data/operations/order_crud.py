from sqlalchemy import and_


def add_order(
    portfolio_id: str,
    code: str,
    direction: DIRECTION_TYPES,
    order_type: ORDER_TYPES,
    transaction_price: float,
    volume: int,
    remain: float,
    fee: float,
    timestamp: any,
    *args,
    **kwargs,
):
    item = MOrder()
    item.set(
        portfolio_id,
        code,
        direction,
        order_type,
        volume,
        transaction_price,
        remain,
        fee,
        timestamp,
    )
    uuid = item.uuid
    add(item)
    return uuid


def add_orders(orders: List[Union[Order, MOrder]], *args, **kwargs):
    l = []
    for i in orders:
        if isinstance(i, MOrder):
            l.append(i)
        elif isinstance(i, Order):
            item = MOrder()
            item.set(
                i.portfolio_id,
                i.code,
                i.direction,
                i.order_type,
                i.volume,
                i.transaction_price,
                i.remain,
                i.fee,
                i.timestamp,
            )
            l.append(item)
        else:
            GLOG.WARN("add ticks only support tick data.")
    return add_all(l)


def delete_order_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs) -> int:
    conn = connection if connection else get_click_connection()
    model = MOrder
    filters = [
        model.uuid == id,
    ]
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


def softdelete_order_by_id(id: str, connection: Optional[GinkgoClickhouse] = None, *args, **kwargs) -> int:
    delete_order_by_id(id, connection, *args, **kwargs)


def delete_order_by_portfolio_id_and_date_range(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    conn = connection if connection else get_click_connection()
    model = MOrder
    filters = [
        model.portfolio_id == portfolio_id,
    ]
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
        pritn(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def softdelete_order_by_portfolio_id_and_date_range(
    portfolio_id: str,
    start_date: Optional[any] = None,
    end_date: Optional[any] = None,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> int:
    delete_order_by_portfolio_id_and_date_range(portfolio_id, start_date, end_date, connection, *args, **kwargs)


def update_order():
    pass


def get_order(
    portfolio_id: str,
    code: Optional[str] = None,
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
    model = MOrder
    filters = [
        model.portfolio_id == portfolio_id,
    ]
    if code:
        filters.append(model.code == code)

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
                    item = Order()
                    item.set(i)
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
