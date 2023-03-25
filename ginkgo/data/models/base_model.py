import uuid
import datetime
from ginkgo.data import DBDRIVER as db
from ginkgo.libs.ginkgo_pretty import pretty_repr
from sqlalchemy import Column, String, DateTime, Boolean, func

# from infi.clickhouse_orm import Model


def gen_id(self):
    return uuid.uuid4().hex


def get_datetime(self):
    return datetime.datetime.now()


class BaseModel(db.base):
    __abstract__ = True
    __tablename__ = "BaseModel"

    uuid = Column(String(32), primary_key=True)
    datetime = Column(DateTime)
    create = Column(DateTime)
    update = Column(DateTime)
    isdel = Column(Boolean)

    def __init__(self):
        self.uuid = uuid.uuid4().hex
        self.datetime = datetime.datetime.now()
        self.create = datetime.datetime.now()
        self.update = datetime.datetime.now()

    def delete(self):
        self.isdel = True

    def __repr__(self):
        methods = ["delete", "query", "registry", "metadata"]
        r = []
        count = 9
        for param in self.__dir__():
            if param in methods:
                continue

            if param.startswith("_"):
                continue
            tmp = f"{str(param).upper()}"
            tmp += " " * (count - len(str(param)))
            s = self.__getattribute__(param)
            s = str(s).strip(b"\x00".decode())
            tmp += f" : {s}"
            r.append(tmp)

        return pretty_repr(self.__tablename__, r, 60)
