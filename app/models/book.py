from sqlalchemy import Column, String, Integer, SmallInteger
from werkzeug.security import generate_password_hash

from models.base import Base


class Book(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    nickName = Column(String(50), unique=True, nullable=False)
    summary = Column(String(200))
    status = Column(SmallInteger, default=1)

    def delete(self):
        if self.status == 0:
            return
        else:
            self.status = 0
