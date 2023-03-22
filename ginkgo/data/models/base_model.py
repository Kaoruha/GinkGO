import uuid
from ginkgo.data.drivers.ginkgo_clickhouse import Base, engine
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, DECIMAL, DateTime, Boolean


def gen_id():
    return uuid.uuid4().hex


class BaseModel(Base):
    __abstract__ = True
    __tablename__ = "BaseModel"
    __table_args__ = (engines.Memory(),)

    ID = Column(DECIMAL)
    UUID = Column(String(32), default=gen_id, primary_key=True)
    DATETIME = Column(DateTime)
    ISDEL = Column(Boolean)
