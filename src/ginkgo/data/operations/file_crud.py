from sqlalchemy import and_

from ginkgo.enums import FILE_TYPES
from ginkgo.data.models import MFile
from ginkgo.data.drivers import add, add_all, get_mysql_connection, GinkgoMysql


def add_file(type: FILE_TYPES, file_name: str, content: bytes):
    item = MFile()
    item.set(type, file_name, content)
    uuid = item.uuid
    add(item)
    return uuid


def add_files():
    pass


def delete_file_by_id(id: str, connection: GinkgoMysql, *argss, **kwargs):
    conn = connection if connection else get_mysql_connection()
    model = MFile
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


def softdelete_file_by_id(id: str, connection: GinkgoMysql, *argss, **kwargs):
    delete_file_by_id(id, connection, *args, **kwargs)


def update_file(
    id: str,
    type: Optional[FILE_TYPES] = None,
    file_name: Optional[str] = None,
    content: Optional[bytes] = None,
    connection: Optional[GinkgoMysql] = None,
    *argss,
    **kwargs,
):
    conn = connection if connection else get_mysql_connection()
    model = MFile
    filters = [model.uuid == id]
    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        if type:
            res.type = type
        if file_name:
            res.file_name = file_name
        if content:
            res.content = content
        res.update_time()
        conn.session.commit()
        return res
    except Exception as e:
        conn.session.rollback()
        pritn(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()


def get_file_by_id(
    id: str,
    connection: Optional[GinkgoClickhouse] = None,
    *args,
    **kwargs,
) -> Union[List[Tick], pd.DataFrame]:
    conn = connection if connection else get_click_connection()
    model = MFile
    filters = [model.uuid == id]

    try:
        query = conn.session.query(model).filter(and_(*filters))
        res = query.first()
        return res
    except Exception as e:
        conn.session.rollback()
        print(e)
        GLOG.ERROR(e)
        return 0
    finally:
        conn.close_session()
