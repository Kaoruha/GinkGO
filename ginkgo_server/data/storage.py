"""
数据的存储模块，负责与MongoDocker的通信以及本地缓存的处理
"""
import threading
import datetime
import time
import mongoengine
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.data.models.stock_info import StockInfo
from ginkgo_server.data.models.adjust_factor import AdjustFactor
from ginkgo_server.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD


class GinkgoStorage(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with GinkgoStorage._instance_lock:
                if not hasattr(cls, '_instance'):
                    GinkgoStorage._instance = super().__new__(cls)

            return GinkgoStorage._instance

    def connect_mongo(self):
        mongoengine.connect(db=DATABASE,
                            host=HOST,
                            port=PORT,
                            username=USERNAME,
                            password=PASSWORD)

    def is_database_exists(self):
        pass

    def is_collection_exists(self):
        pass

    def update_stock_info(self,
                          code='sh.000001',
                          code_name='上证综合指数',
                          trade_status=1,
                          has_min_bar=True):
        """
        更新指数基本信息
        """
        # 连接MongoDB
        self.connect_mongo()
        # 查重
        stock_info_search = StockInfo.objects(code=code)
        if stock_info_search.count() > 0:
            # 库中有数据
            # 检查状态是否有改变，有则更新，
            if stock_info_search.count() == 1:
                info = stock_info_search[0]
                if info.trade_status == trade_status and info.code_name == code_name:
                    gl.info(f"{code} {code_name} 数据无更新，不进行操作")
                    return 0
                else:
                    info.trade_status = trade_status
                    info.has_min_bar = has_min_bar
                    info.code_name = code_name
                    info.date = datetime.datetime.now().strftime(
                        '%Y-%m-%d %H:%M:%S')
                    info.save()
                    gl.info(f"{code} {code_name} 数据更新")
                    return 1
            else:
                gl.critical('数据库异常，指数代码有重复，请检查代码')
                return 0

        else:
            # 库中没有数据,则添加数据
            info = StockInfo(
                code=code,
                code_name=code_name,
                trade_status=trade_status,
                date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            info.save()

    def get_all_stock_code(self):
        """
        获取所有指数代码

        # TODO 等本地缓存模块完成，应该从本地缓存找起，找不到找远程Mongo,最后找不到尝试重新获取
        """
        self.connect_mongo()
        stock_info_search = StockInfo.objects()
        rs = []
        for i in stock_info_search:
            rs.append(i.code)

        if len(rs) > 0:
            gl.info(f'查询到 {len(rs)} 条指数代码')
        else:
            gl.error(f'指数代码查询为空，请检查代码')

        return rs

    def update_adjust_factor(
            self,
            date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            code='default',
            divid_operate_date='00-00-00',
            fore_adjust_factor=0,
            back_adjust_factor=0,
            adjust_factor=0,
            is_latest=True):
        # 连接MongoDB
        self.connect_mongo()
        # 查重
        adjust_factor_search = AdjustFactor.objects(
            code=code, divid_operate_date=divid_operate_date)
        if adjust_factor_search.count() > 0:
            # 库中有数据
            # 检查状态是否有改变，有则更新，
            if adjust_factor_search.count() == 1:
                adjust_factor = adjust_factor_search[0]
                if adjust_factor.fore_adjust_factor == fore_adjust_factor and adjust_factor.back_adjust_factor == back_adjust_factor and adjust_factor.adjust_factor == adjust_factor and adjust_factor.is_latest == is_latest:
                    gl.info(f"{code} {divid_operate_date} 复权数据无更新，不进行操作")
                    return 0
                else:
                    adjust_factor.date = datetime.datetime.now().strftime(
                        '%Y-%m-%d %H:%M:%S')
                    adjust_factor.code = code
                    adjust_factor.divid_operate_date = divid_operate_date
                    adjust_factor.back_adjust_factor = back_adjust_factor
                    adjust_factor.adjust_factor = adjust_factor
                    adjust_factor.is_latest = is_latest
                    adjust_factor.save()
                    gl.info(f"{code} {divid_operate_date} 复权数据更新")
                    return 1
            else:
                gl.critical('数据库异常，复权数据有重复，请检查代码')
                return 0

        else:
            # 库中没有数据,则添加数据
            adjust_factor = AdjustFactor(
                code=code,
                date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                divid_operate_date=divid_operate_date,
                back_adjust_factor=back_adjust_factor,
                adjust_factor=adjust_factor,
                is_latest=is_latest)

            adjust_factor.save()

    def add_day_bar(self):
        pass

    def test(self, *args, **kwargs):
        # self.update_stock_info(has_min_bar=False, trade_status=0)
        self.get_all_stock_code()


ginkgo_storage = GinkgoStorage()

# ginkgo_storage.connect_mongo()
