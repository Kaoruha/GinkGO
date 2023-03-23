import uuid
import datetime
from ginkgo.data.drivers.ginkgo_clickhouse import GINKGOCLICK as gc
from ginkgo.libs.ginkgo_pretty import pretty_repr
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, DateTime, Boolean, func


def gen_id(self):
    return uuid.uuid4().hex


def get_datetime(self):
    return datetime.datetime.now()


class BaseModel(gc.base):
    __abstract__ = True
    __tablename__ = "BaseModel"
    __table_args__ = (engines.Memory(),)

    UUID = Column(String(32), primary_key=True)
    DATETIME = Column(DateTime)
    CREATE = Column(DateTime)
    UPDATE = Column(DateTime)
    ISDEL = Column(Boolean)

    def __init__(self):
        self.UUID = uuid.uuid4().hex
        self.DATETIME = datetime.datetime.now()
        self.CREATE = datetime.datetime.now()
        self.UPDATE = datetime.datetime.now()

    def delete(self):
        self.ISDEL = True

    def query(cls):
        print(cls)

    def __repr__(self):
        methods = ["delete", "query", "registry", "metadata"]
        r = []
        count = 8
        for param in self.__dir__():
            if param in methods:
                continue

            if param.startswith("_"):
                continue
            tmp = f"{str(param)}"
            tmp += " " * (count - len(str(param)))
            tmp += f" : {self.__getattribute__(param)}"
            r.append(tmp)

        return pretty_repr(self.__tablename__, r, 60)
