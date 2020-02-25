import datetime

from sqlalchemy import Column, String, SmallInteger, MetaData, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, sessionmaker
from app.config.secure import SQLALCHEMY_DATABASE_URI

"""
Stock类，封装了与数据库的一系列操作，实现动态创建表以及动态重映射
目前设计仅针对国内A股，在结合回测框架与美股信息后会有一波更新
2020-02-08
"""


class Stock(object):
    __engine = create_engine(SQLALCHEMY_DATABASE_URI)
    __Base = declarative_base()
    __metadata = MetaData()
    __session_factory = sessionmaker(bind=__engine)
    __session = __session_factory()
    __stock_mapper = {}

    @classmethod
    def __create_table(cls, code):
        # MetaData类主要用于保存表结构，连接字符串等数据，是一个多表共享的对象
        metadata = MetaData(cls.__engine)
        table_name = code
        table = Table(table_name, metadata,
                      Column(String(50), name='timestamp', unique=True, nullable=False, primary_key=True),
                      Column(String(20), name='mkt_value'),
                      Column(String(20), name='value_change'),
                      Column(String(20), name='transaction_volume'),
                      Column(SmallInteger, name='transaction_amount'),
                      Column(String(10), name='buy_or_sale'),
                      Column(String(50), name='update_time')
                      )
        # create_all方法已经排除了同名表存在的情况
        metadata.create_all(cls.__engine)

    @classmethod
    def __get_stock(cls, code):
        """
        根据code通过创建或者查询，return一个新的model类
        code:数据库表名
        engine:create_engine返回的对象，指定要操作的数据库连接，from sqlalchemy import create_engine
        TODO 回头试试绑在flask_sqlalchemy的engine上
        :param code: 股票代码，数据库表名
        :return: 返回该股票代码的股票类
        """
        # 1、判断是stock_mapper中否有该股票 # TODO 判断股票是否在可选列表内，需要额外爬一个股票清单，并定期更新
        if code in cls.__stock_mapper:

            # 2、如果有直接中stock_mapper中返回对应股票类
            return cls.__stock_mapper[code]
        else:

            # 3、如果没有,则在数据库中创建同名表
            cls.__create_table(code)

            # 4、由表生成对应Model类形成映射
            cls.__Base.metadata.reflect(cls.__engine)
            table = cls.__Base.metadata.tables[code]
            t = type(code, (object,), dict())
            mapper(t, table)
            cls.__Base.metadata.clear()

            # 5、把Model存入stock_mapper
            cls.__stock_mapper[code] = t  # TODO 单独开辟一个文件存放历史数据，应用启动时加载文件自动生成所有Model映射

        # 6、返回对应Model类
        return cls.__stock_mapper[code]

    @classmethod
    def generate_record(cls,
                        code,
                        timestamp,
                        mkt_value='-',
                        value_change='-',
                        transaction_volume='-',
                        transaction_amount=0,
                        buy_or_sale='-'):
        """
        :param code: 股票代码
        :param timestamp: 时间戳
        :param mkt_value: 市场价格
        :param value_change: 市场价格变动率
        :param transaction_volume: 成交量
        :param transaction_amount: 成交额
        :param buy_or_sale: 买入还是卖出
        :param update: 最近更新时间
        :return: 返回code对象的一条交易记录

        传入交易记录各个参数，code为股票代码，返回code对象的一条交易记录
        """
        try:
            s = cls.__get_stock(code)
            t = s()
            t.timestamp = timestamp
            t.mkt_value = mkt_value
            t.value_change = value_change
            t.transaction_volume = transaction_volume
            t.transaction_amount = transaction_amount
            t.buy_or_sale = buy_or_sale
            t.update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return t
            # cls.__session.add(t)
            # cls.__session.commit()
        except Exception as e:
            raise e

    @classmethod
    def add_msgs(cls, msgs):
        """
        :param msgs: 一个由多条股票记录组成的list
        :return:
        """
        try:
            t = []
            for msg in msgs:
                t.append(msg)
            cls.__session.add_all(t)
            cls.__session.commit()
        except Exception as e:
            raise e
