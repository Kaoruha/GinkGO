from app.models.base import Base, db
from sqlalchemy import Column, String, SmallInteger, MetaData, Table


# 单只股票的基类
class Stock(Base):
    __abstract__ = True  # 变成抽象类，只声明不实现
    __tablename__ = 'STOCK'
    timestamp = Column(String(20), name='timestamp', unique=True, nullable=False, primary_key=True)
    mkt_value = Column(String(20), name='mkt_value')
    value_change = Column(String(20), name='value_change')
    volume = Column(String(20), name='volume')
    total_volume = Column(SmallInteger, name='total_volume')
    buy_or_sale = Column(SmallInteger, name='buy_or_sale')

    def __init__(self, code):
        self.__tablename__ = code

    @classmethod
    def create_table(cls, code):
        # 获取db中的engine
        engine = db.get_engine()

        # MetaData类主要用于保存表结构，连接字符串等数据，是一个多表共享的对象
        metadata = MetaData(engine)
        table_name = code
        table = Table(table_name, metadata,
                      Column(String(20), name='timestamp', unique=True, nullable=False, primary_key=True),
                      Column(String(20), name='mkt_value'),
                      Column(String(20), name='value_change'),
                      Column(String(20), name='volume'),
                      Column(SmallInteger, name='total_volume'),
                      Column(SmallInteger, name='buy_or_sale')
                      )
        metadata.create_all(engine)

    def get_stock(self, name):
        table_name = name
        if table_name not in record_table_mapper:
            t = type(table_name, (Stock,), {'__tablename__': table_name})
            record_table_mapper[name] = t
        return record_table_mapper[name]

    def show_table_name(self):
        return self.__tablename__


record_table_mapper = {}
