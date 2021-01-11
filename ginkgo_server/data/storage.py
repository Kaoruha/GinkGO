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

    # 单例模式
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with GinkgoStorage._instance_lock:
                if not hasattr(cls, '_instance'):
                    GinkgoStorage._instance = super().__new__(cls)

            return GinkgoStorage._instance

    # 连接MongoDocker
    def __connect_mongo(self):
        """
        从Ginkgo_Server的Config内读取MongoDB的配置信息，尝试进行连接
        """
        mongoengine.connect(db=DATABASE,
                            host=HOST,
                            port=PORT,
                            username=USERNAME,
                            password=PASSWORD)
        # TODO 连接结果输出，方便定位Bug

    # 判断数据库DB是否存在
    def __is_database_exists(self):
        pass

    # 判断集合Collection是否存在
    def __is_collection_exists(self):
        pass

    # 插入指数信息
    def insert_stock_info(self,
                          code='sh.000001',
                          code_name='上证综合指数',
                          trade_status=1,
                          has_min_bar=True):
        self.__connect_mongo()
        info = StockInfo()
        info.code = code
        info.code_name = code_name
        info.trade_status = trade_status
        info.has_min_bar = has_min_bar
        info.date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info.save()
        gl.info(f'成功创建 {code} 的指数基础信息')

    # 更新指数信息
    def update_stock_info(self,
                          code='待更新指数',
                          code_name='待更新指数',
                          trade_status=1):
        """
        更新指数基本信息
        """
        date_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 尝试查询数据库
        data_search = self.query_stock_info(code=code)
        if data_search is None:
            # 当查询结果为None即库内无数据，直接插入新的数据
            self.create_stock_info(code=code, code_name=code_name, trade_status=trade_status, has_min_bar=has_min_bar)
            return True
        elif not data_search:
            # 数据库错误处理
            return False
        else:
            # 尝试更新
            # 否则更新数据
            has_changed = False

            if data_search.code != code:
                data_search.code = code
                has_changed = True
                gl.info(f'{code} 指数信息Code代码变更')

            if data_search.code_name != code_name:
                data_search.code_name = code_name
                has_changed = True
                gl.info(f'{code} 指数信息code_name变更')

            if data_search.trade_status != trade_status:
                data_search.trade_status = trade_status
                has_changed = True
                gl.info(f'{code} 交易状态变更')
                # TODO 区分停牌 or 交易

            if not has_changed:
                gl.info(f'{code} 指数信息数据无更新')
            else:
                data_search.date = date_now
                data_search.save()
                gl.info(f'{code} 指数信息数据已更新')
            
            return True

    # 查询指数信息
    def query_stock_info(self, code='sh.000001'):
        """
        查询指数信息，理论上库里只有一条数据
        """
        self.__connect_mongo()
        gl.info(f'尝试查询 {code} 的指数基础信息')
        stock_info_search = StockInfo.objects(code=code)
        if stock_info_search.count() == 1:
            return stock_info_search[0]
        elif stock_info_search.count() == 0:
            gl.info(f'{code} 指数信息不存在')
            return None
        else:
            gl.critical(f'{code} 指数信息超过1条，请检查代码')
            return False

    # 获取所有指数代码信息
    def get_all_stock_info(self):
        """
        获取所有指数代码

        # TODO 等本地缓存模块完成，应该从本地缓存找起，找不到找远程Mongo,最后找不到尝试重新获取
        """
        self.__connect_mongo()
        stock_info_search = StockInfo.objects()
        rs = []
        for i in stock_info_search:
            rs.append(i.code)

        if len(rs) > 0:
            gl.info(f'查询到 {len(rs)} 条指数代码')
        else:
            gl.error(f'指数代码查询为空，请检查代码')

        return rs


    # 插入复权因子数据
    def insert_adjust_factor(self):
        pass

    # 更新复权因子
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
        self.__connect_mongo()
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

    # 查询复权因子
    def query_adjust_factor(self):
        pass

    # 获取某只股票的复权因子数据
    def get_adjust_factors(self,code):
        pass

    # 添加Stock日交易数据
    def insert_day_bar(self):
        pass

    # 更新Stock日交易数据
    def update_day_bar(self):
        pass

    # 查询Stock日交易数据
    def query_day_bar(self):
        pass

    def test(self, *args, **kwargs):
        # self.update_stock_info(has_min_bar=False, trade_status=0)
        # self.get_all_stock_code()
        r = self.filter_stock_info(code='sh.000001')


ginkgo_storage = GinkgoStorage()