from sqlalchemy import Column, String, Integer, Table, MetaData
from sqlalchemy.orm import mapper
from app.models.base import Base, db


class IPProxy(Base):
    __tablename__ = 'IPProxy'
    id = Column(Integer, name='id', primary_key=True)
    schema = Column(String(10), name='schema')  # 代理的类型 http/https
    ip = Column(String(20), name='ip')  # 代理的IP地址
    port = Column(String(10), name='port')  # 代理的端口号
    original = Column(String(20), name='original')  # 代理来源
    used_total = Column(Integer, name='used_total')  # 代理的使用次数
    success_times = Column(Integer, name='success_times')  # 代理请求成功的次数
    continuous_failed = Column(Integer, name='continuous_failed')  # 使用代理发送请求，连续失败的次数
    created_time = Column(String(20), name='created_time')  # 代理的爬取时间
    status = Column(String(10), name='status')  # 代理d最新状态
    update_time = Column(String(20), name='update_time')  # 代理状态低更新时间

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    # 查询和动态变更查询的目标数据库Ok
    @classmethod
    def test(cls):
        # cls.__table__.name = 'BOOK'
        user = db.session.query(IPProxy).filter().all()
        return user
