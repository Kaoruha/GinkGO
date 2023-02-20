import datetime
import uuid

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    inspect,
    create_engine,
    Sequence,
    Column,
    Integer,
    String,
    Boolean,
    MetaData,
    DateTime,
    inspect,
)
from sqlalchemy.orm import sessionmaker
from clickhouse_sqlalchemy import engines
from ginkgo.config.secure import USERNAME, PASSWORD, HOST, DATABASE
from ginkgo.libs import GINKGOLOGGER as gl


uri = f"clickhouse+native://{USERNAME}:{PASSWORD}@{HOST}/{DATABASE}"
engine = create_engine(uri)
session = sessionmaker(engine)()
metadata = MetaData(bind=engine)
Base = declarative_base(metadata=metadata)


class BaseModel(Base):
    """
    数据Model的基类，用来设置一些的属性与方法
    """

    # set abstract true will ignore the table creation
    __abstract__ = True

    __tablename__ = "basetest"

    __table_args__ = (engines.MergeTree(order_by=["uuid"]),)

    uuid = Column(String, primary_key=True)
    create_time = Column(DateTime)
    last_update = Column(DateTime)
    is_delete = Column(Boolean, default=False)
    # meta = {"allow_inheritance": True, "abstract": True}

    def __init__(self, *args, **kwargs):
        self.uuid = str(uuid.uuid4())
        self.create_time = datetime.datetime.now()
        self.last_update = datetime.datetime.now()
        self.is_delete = False

    def __repr__(self):
        s = self.__tablename__.lower()
        s += f"\nuuid: {self.uuid}"
        s += f"\ncreate: {self.create_time}"
        s += f"\nupdate: {self.last_update}"
        s += f"\nis_del: {self.is_delete}"
        return s

    @classmethod
    def create_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create()

    def delete(self):
        """
        soft delete
        """
        if self.is_delete is True:
            return
        else:
            self.is_delete = True

    def update_time(self):
        """
        update the updatetime
        """
        self.last_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
