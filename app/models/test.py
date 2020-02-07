#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time    : 2018/11/23 09:45
@File    : myautomap.py
@Author  : frank.chang@shoufuyou.com
"""

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.schema import Table
from datetime import datetime


def to_dict(self):
    return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


Base = automap_base()

# engine, suppose it has two tables 'Bank' and 'BidOrder' set up
url = 'mysql+pymysql://calvin:qweasd123@47.102.46.64:3306/myquant'
engine = create_engine(url, pool_size=10, pool_recycle=7200,
                       pool_pre_ping=True, encoding='utf-8')

# reflect the tables
Base.prepare(engine, reflect=True)

# mapped classes are now created with names by default
# matching that of the table name.
# notice 注意这里 Bank 对应数据库中的表
print(Base.classes.keys())
Bank = Base.classes.BOOK

session_factory = sessionmaker(bind=engine)
session = session_factory()

# # 查询数据
# query = session.query(Bank).filter_by(name='frank')
# print(query)
#
# m = query.first()
#
# mydict = to_dict(m)
#
# for k, v in mydict.items():
#     print(k, v)

if __name__ == '__main__':
    data = {'name': 'fuckme'
            }

    bank = Bank(**data)
    # 添加一条数据
    session.add(bank)

    session.commit()
