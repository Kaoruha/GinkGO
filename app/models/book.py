from sqlalchemy import Column, String, Integer, Table, MetaData
from sqlalchemy.orm import mapper
from app.models.base import Base, db


class Book(Base):
    __tablename__ = 'BOOK'
    id = Column(Integer, name='id', primary_key=True)
    name = Column(String(50), name='name', nullable=False)

    def __init__(self, name):
        self.name = name

    # 查询和动态变更查询的目标数据库Ok TODO 把方法挪到stock类里去
    @classmethod
    def test(cls):
        # cls.__table__.name = 'BOOK'
        user = db.session.query(Book).filter().all()
        return user

    @classmethod
    def set_base(cls, num):
        if num == 0:
            cls.__table__.name = 'BOOK'
        elif num == 1:
            cls.__table__.name = 'BOOK1'

    @classmethod
    def remapping(cls, table_name):

        engine = db.get_engine()

        # MetaData类主要用于保存表结构，连接字符串等数据，是一个多表共享的对象
        metadata = MetaData(engine)
        table = Table(table_name, metadata,
                      Column(Integer, name='id', primary_key=True),
                      Column(String(50), name='name', nullable=False)
                      )
        mapper(Book, table)

