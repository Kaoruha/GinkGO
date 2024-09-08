from ginkgo.data.drivers import add, add_all, get_mysql_connection, GinkgoMysql
from ginkgo.data.models import MPortfolioFileMapping
from ginkgo.enums import FILE_TYPES
from sqlalchemy import and_


def add_portfolio_file_mapping(name: str, portfolio_id: str, file_id: str, type: FILE_TYPES, *args, **kwargs):
    item = MPortfolioFileMapping()
    item.set(name, portfolio_id, file_id, type)
    uuid = item.uuid
    add(item)
    return uuid


def delete_portfolio_file_mapping_by_id(id: str, connection: Optional[GinkgoMysql] = None, *args, **kwargs):
    conn = connection if connection else get_mysql_connection()
    model = MPortfolioFileMapping()
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


def softdelete_portfolio_file_mapping_by_id(id: str, connection: Optional[GinkgoMysql] = None, *args, **kwargs):
    delete_portfolio_file_mapping_by_id(id, connection, *args, **kwargs)


def delete_portfolio_file_mapping_by_portfolio_id_and_file_id(
    portfolio_id: str, file_id: Optional[str] = None, connection: Optional[GinkgoMysql] = None, *args, **kwargs
):
    conn = connection if connection else get_mysql_connection()
    model = MPortfolioFileMapping()
    filters = [model.portfolio_id == portfolio_id]
    if file_id:
        filters.append(model.file_id == file_id)
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


def update_portfolio_file_mapping():
    pass


def get_portfolio_file_mapping(
    portfolio_id: str, type: Optional[FILE_TYPES] = None, connection: Optional[GinkgoMysql] = None, *args, **kwargs
):
    conn = connection if connection else get_mysql_connection()
    model = MPortfolioFileMapping()
    filters = [model.portfolio_id == portfolio_id]
    if type:
        filters.append(model.type == type)
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.all()
        return res
    except Exception as e:
        conn.session.rollback()
        pritn(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()
