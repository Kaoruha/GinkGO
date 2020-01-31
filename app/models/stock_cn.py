from app.models.base import Base
from sqlalchemy import Column, String, Integer, SmallInteger


# 单只股票的基类
class Stock(Base):
    __abstract__ = True  # 变成抽象类，只声明不实现
    __tablename__ = 'STORK1'
    timestamp = Column(String(20), unique=True, nullable=False, primary_key=True)
    mkt_value = Column(String(20), nullable=False)
    value_change = Column(String(20), nullable=False)
    volume = Column(String(20), nullable=False)
    total_volume = Column(SmallInteger, nullable=False)
    buy_or_sale = Column(SmallInteger, nullable=False)

    def __init__(self, code):
        self.__tablename__ = code
