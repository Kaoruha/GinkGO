from sqlalchemy import Column, String, Integer, SmallInteger
from werkzeug.security import generate_password_hash
from app.models.base import Base


class User(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    nickName = Column(String(50), unique=True, nullable=False)
    email = Column(String(50), unique=True, nullable=False)
    phone = Column(Integer)
    _password = Column('password', String(100))
    authority = Column(SmallInteger)
    status = Column(SmallInteger, default=1)

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, raw):
        self._password = generate_password_hash(raw)

    def delete(self):
        if self.status == 0:
            return
        else:
            self.status = 0
