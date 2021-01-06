from contextlib import contextmanager
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy
from sqlalchemy import Column, Integer, SmallInteger, String
from datetime import datetime


class SQLAlchemy(_SQLAlchemy):
    @contextmanager
    def auto_commit(self):
        try:
            yield
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e


db = SQLAlchemy()


class Base(db.Model):
    __abstract__ = True  # 变成抽象类，只声明不实现
    create_time = Column(String(20), name='created_time')
    is_delete = Column(SmallInteger, default=1)

    def __init__(self):
        self.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @property
    def create_time(self):
        if self.create_time:
            return datetime.fromtimestamp(self.create_time)
        else:
            return None

    def delete(self):
        if self.is_delete == 0:
            return
        else:
            self.is_delete = 0

    @classmethod
    def add_all(cls, items=[]):
        """
        :param items: 一个由多条股票记录组成的list
        :return:
        """
        try:
            if not items:
                return
            t = []
            for item in items:
                t.append(item)
            db.session.add_all(t)
        except Exception as e:
            db.session.rollback()
            raise e
