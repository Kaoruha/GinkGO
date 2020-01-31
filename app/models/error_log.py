from sqlalchemy import Column, String, Integer, SmallInteger
from app.models.base import Base


class ErrorLog(Base):
    __abstract__ = True  # 暂时先不生成库
    id = Column(Integer, primary_key=True, autoincrement=True)
    caption = Column(String(2000), unique=True, nullable=False)
    status = Column(SmallInteger, default=1)

    def delete(self):
        if self.status == 0:
            return
        else:
            self.status = 0
