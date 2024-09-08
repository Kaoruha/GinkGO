from ginkgo.data.drivers import add, add_all, get_mysql_connection, GinkgoMysql
from ginkgo.backtest import Portfolio
from ginkgo.data.models import MPortfolio
from sqlalchemy import and_


def add_portfolio(name: str, *args, **kwargs):
    item = MPortfolio()
    item.set(portfolio_id)
    uuid = item.uuid
    add(item)
    return uuid


def delete_portfolio_by_id(id: str, connection: Optional[GinkgoMysql] = None, *args, **kwargs):
    conn = connection if connection else get_mysql_connection()
    model = MPortfolio
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


def softdelete_portfolio_by_id(id: str, connection: Optional[GinkgoMysql] = None, *args, **kwargs):
    conn = connection if connection else get_mysql_connection()
    model = MPortfolio
    filters = [model.uuid == id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        res.delete()
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        pritn(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def update_portfolio():
    pass


def get_portfolio():
    pass
