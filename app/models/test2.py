import traceback

from sqlalchemy import (BigInteger, Column, DateTime, Integer, MetaData,
                        String, Table, create_engine, text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.schema import CreateTable

# 本地数据库
engineLocal = create_engine('mysql+pymysql://calvin:qweasd123@47.102.46.64:3306/myquant')

Base = declarative_base()
metadata = MetaData()


def dictToObj(results, to_class):
    """
    将字典list或者字典转化为指定类的对象list或指定类的对象
    python 支持动态给对象添加属性，所以字典中存在而该类不存在的会直接添加到对应对象
    """
    if isinstance(results, list):
        objL = []
        for result in results:
            obj = to_class()
            for r in result.keys():
                obj.__setattr__(r, result[r])
            objL.append(obj)
        return objL
    else:
        try:
            obj = to_class()
            for r in results.keys():
                obj.__setattr__(r, results[r])
            return obj
        except Exception as e:
            print(e)
            traceback.print_exc()
            return None
    # else:
    #     print("传入对象非字典或者list")
    #     return None


def getModel(name, engine):
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


def createTableFromTable(name, tableNam, engine):
    """copy一个已有表的结构，并创建新的表
    """
    metadata = MetaData(engine)
    Base.metadata.reflect(engine)
    # 获取原表对象
    table = Base.metadata.tables[tableNam]
    # 获取原表建表语句
    c = str(CreateTable(table))
    # 替换表名
    c = c.replace("CREATE TABLE " + tableNam, "CREATE TABLE if not exists " + name)
    db_conn = engine.connect()
    db_conn.execute(c)
    db_conn.close()
    Base.metadata.clear()


def getNewModel(name, tableNam, engine):
    """copy一个表的表结构并创建新的名为name的表并返回model类
    name:数据库表名
    tableNam:copy的表表名
    engine:create_engine返回的对象，指定要操作的数据库连接，from sqlalchemy import create_engine
    """
    createTableFromTable(name, tableNam, engine)
    return getModel(name, engine)


s = getModel('BOOK', engineLocal)
t = s()
t.name = 'naozi'
session_factory = sessionmaker(bind=engineLocal)
session = session_factory()
session.add(t)
session.commit()
