from sqlalchemy import Column, String, Integer
from app.models.base import Base, db


class Book(Base):
    __tablename__ = 'BOOK'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)

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
