from sqlalchemy import Column, String, Integer
from ginkgo.models.base import Base, db
import datetime


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
    status = Column(String(10), name='status')  # 代理最新状态
    update_time = Column(String(20), name='update_time')  # 代理状态更新时间

    def __init__(self, ip, port, schema, original):
        self.ip = ip
        self.port = port
        self.schema = schema
        self.original = original
        self.used_total = '0'
        self.success_times = '0'
        self.status = '未验证'
        self.update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 查询和动态变更查询的目标数据库Ok
    @classmethod
    def test(cls):
        # cls.__table__.name = 'BOOK'
        user = db.session.query(IPProxy).filter().all()
        return user


