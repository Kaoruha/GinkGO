from sqlalchemy import Column, String, Integer, MetaData, Table
from sqlalchemy.orm import mapper
from sqlalchemy import create_engine
from app.models.base import Base, db
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import declarative_base

record_table_mapper = {}


# Base = declarative_base()
# metadata = MetaData()


class RecordBase(Base):
    __tablename__ = 'default'
    record_id = Column(Integer(), name='record_id', primary_key=True)
    name = Column(String(20), name='name')

    def __init__(self):
        pass

    def test(self):
        return self.name

    def create_table(self, code):
        # 获取db中的engine
        url = 'mysql+pymysql://calvin:qweasd123@47.102.46.64:3306/myquant'
        engine = create_engine(url, echo=False)

        # MetaData类主要用于保存表结构，连接字符串等数据，是一个多表共享的对象
        metadata = MetaData(engine)
        table_name = code
        table = Table(table_name, metadata,
                      Column(Integer(), name='record_id', primary_key=True),
                      Column(String(20), name='name')
                      )
        metadata.create_all(engine)

    @classmethod
    def get_stock(cls, name):
        if name not in record_table_mapper:
            url = 'mysql+pymysql://calvin:qweasd123@47.102.46.64:3306/myquant'
            t = type(name, (RecordBase,), {'__tablename__': name, })
            t.__tablename__ = name
            t.__class__.__name__ = name
            cls.getModel(name, create_engine(url, echo=False))
            record_table_mapper[name] = t
        # engine = db.get_engine()

        engine = create_engine(url, echo=False)
        metadata = MetaData(engine)

        # sb = metadata.tables.keys()
        # print(sb)

        table = Table(name, metadata,
                      Column(Integer(), name='record_id', primary_key=True),
                      Column(String(20), name='name')
                      )

        return record_table_mapper[name]

    @classmethod
    def getModel(name):
        url = 'mysql+pymysql://calvin:qweasd123@47.102.46.64:3306/myquant'
        engine = create_engine(url, echo=False)
        """根据name创建并return一个新的model类
        name:数据库表名
        engine:create_engine返回的对象，指定要操作的数据库连接，from sqlalchemy import create_engine
        """
        Base.metadata.reflect(engine)
        table = Base.metadata.tables[name]
        t = type(name, (object,), dict())
        mapper(t, table)
        Base.metadata.clear()
        return t
