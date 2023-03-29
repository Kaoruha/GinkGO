import uuid
import datetime
from ginkgo.data import DBDRIVER as db
from ginkgo.libs.ginkgo_pretty import base_repr
from sqlalchemy import Column, String, DateTime, Boolean, func


def gen_id(self):
    return uuid.uuid4().hex


def get_datetime(self):
    return datetime.datetime.now()


class BaseModel(db.base):
    __abstract__ = True
    __tablename__ = "BaseModel"

    uuid = Column(String(32), primary_key=True)
    desc = Column(
        String(255),
        default="This man is lazy, there is no description.",
    )
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
        return base_repr(self, self.__tablename__, 12, 80)
