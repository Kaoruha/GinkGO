"""
数据的存储模块，负责与MongoDocker的通信以及本地缓存的处理
"""
import threading
import datetime
import time
import tqdm
import mongoengine
import pandas as pd
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.data.models.stock_info import StockInfo
from ginkgo_server.data.models.adjust_factor import AdjustFactor
from ginkgo_server.data.models.day_bar import DayBar
from ginkgo_server.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD


class GinkgoStorage(object):
    _instance_lock = threading.Lock()

    # 单例模式
    def __new__(cls, *args, **kwargs):
        """
        Create a new instance
        """
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
    def insert_a_stock_info(self,
                            code='sh.000001',
                            code_name='上证综合指数',
                            trade_status=1):
        """
        向MongoDB中插入StockInfo数据，包括代号、名称、交易状态、是否有分钟数据
        """
        self.__connect_mongo()
        info = StockInfo(code=code,
                         code_name=code_name,
                         trade_status=trade_status)
        info.save()
        # gl.info(f'成功创建 {code} 的指数基础信息')

    # 更新指数信息
    def update_stock_info(self,
                          code='待更新指数',
                          code_name='待更新指数',
                          trade_status=1):
        """
        更新指数基本信息
        """
        # 尝试查询数据库
        data_search = self.query_stock_info(code=code)
        if data_search:
            # 有值的处理
            has_changed = False

            if data_search.code_name != code_name:
                data_search.code_name = code_name
                has_changed = True
            if data_search.trade_status != trade_status:
                data_search.trade_status = trade_status
                has_changed = True
            if has_changed:
                data_search.save()
                # gl.info(f'{code} 指数信息数据已更新')
            else:
                # gl.info(f'{code} 指数信息数据无更新')
                pass
            return True
        elif data_search is None:
            # 库里没值的处理
            self.insert_a_stock_info(code=code,
                                     code_name=code_name,
                                     trade_status=trade_status)
            return True
        else:
            # 数据库错误的处理
            return False

    # 查询指数信息
    def query_stock_info(self, code='sh.000001'):
        """
        查询指数信息，理论上库里只有一条数据
        """
        self.__connect_mongo()
        # gl.info(f'尝试查询 {code} 的指数基础信息')
        stock_info_search = StockInfo.objects(code=code)

        if stock_info_search.count() == 0:
            return None
        elif stock_info_search.count() == 1:
            return stock_info_search[0]
        else:
            gl.critical(f'{code} 指数基本数据超过1条，请检查代码')
            return False

    # 批量插入指数信息
    def insert_stock_info_list(self, stock_info_list):
        """
        批量插入指数信息
        stock_info_list: StockInfo的数组
        """
        insert_list = []
        update_list = []
        # 校验stock_info_list
        for i in stock_info_list:
            if not isinstance(i, StockInfo):
                gl.error('批量插入指数信息失败，stock_info_list 类型不匹配')
                return False

        self.__connect_mongo()
        # 确认stock_info_list的成员结构了，进行遍历,查询库里是否有数据，如果有则把这条stock_info从list中剔除
        pbar = tqdm.tqdm(stock_info_list)
        for i in pbar:
            stock_info_search = self.query_stock_info(code=i.code)
            if stock_info_search:
                has_different = False
                if i.code_name != stock_info_search.code_name:
                    stock_info_search.code_name = i.code_name
                    has_different = True
                if i.trade_status != stock_info_search.trade_status:
                    stock_info_search.trade_status = i.trade_status
                    has_different = True

                if has_different:
                    update_list.append(stock_info_search)
            elif stock_info_search is None:
                insert_list.append(i)
            else:
                pass
            pbar.set_description(f"Querying {i.code} StockInfo")

        # 批量插入Mongo
        if len(insert_list) > 0:
            StockInfo.objects.insert(insert_list)
        gl.info(f'插入StockInfo {len(insert_list)} 条')
        # 更新
        if len(update_list) > 0:
            pbar = tqdm.tqdm(update_list)
            for i in pbar:
                i.update_time()
                i.save()
                pbar.set_description(f"Updateing {i.code} StockInfo")
        gl.info(f'更新StockInfo {len(update_list)} 条')

        return True

    # 获取所有指数代码信息
    def get_all_stock_code(self):
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
    def insert_adjust_factor(self,
                             code='sh.000000',
                             divid_operate_date='0000-00-00',
                             fore_adjust_factor=0,
                             back_adjust_factor=0,
                             adjust_factor=0):
        """
        向MongoDB中插入AdjustFactor数据，
        
        包括代号、名称、前复权、后复权、复权因子、是否为最新数据
        """
        self.__connect_mongo()
        af = AdjustFactor(code=code,
                          divid_operate_date=divid_operate_date,
                          fore_adjust_factor=fore_adjust_factor,
                          back_adjust_factor=back_adjust_factor,
                          adjust_factor=adjust_factor)
        af.save()
        # gl.info(f'成功创建 {code} 的复权信息')

    # 更新复权因子
    def update_adjust_factor(self,
                             code='default',
                             divid_operate_date='0000/00/00',
                             fore_adjust_factor=0,
                             back_adjust_factor=0,
                             adjust_factor=0):
        # 尝试查询数据库
        data_search = self.query_adjust_factor(
            code=code, divid_operate_date=divid_operate_date)

        if data_search:
            # 更新数据
            # 尝试更新
            # 否则更新数据
            has_changed = False

            if data_search.code != code:
                data_search.code = code
                has_changed = True
                # gl.info(f'{code} 指数信息Code代码变更')

            if data_search.divid_operate_date != divid_operate_date:
                data_search.divid_operate_date = divid_operate_date
                has_changed = True
                # gl.info(f'{code} divid_operate_date变更')

            if data_search.fore_adjust_factor != fore_adjust_factor:
                data_search.fore_adjust_factor = fore_adjust_factor
                has_changed = True
                # gl.info(f'{code} fore_adjust_factor变更')

            if data_search.back_adjust_factor != back_adjust_factor:
                data_search.back_adjust_factor = back_adjust_factor
                has_changed = True
                # gl.info(f'{code} back_adjust_factor变更')

            if data_search.adjust_factor != adjust_factor:
                data_search.adjust_factor = adjust_factor
                has_changed = True
                # gl.info(f'{code} adjust_factor变更')

            if not has_changed:
                pass
                # gl.info(f'{code} 复权数据无更新')
            else:
                data_search.save()
                # gl.info(f'{code} 复权数据更新完毕')
                return True
        elif data_search is None:
            # 当查询结果为None即库内无数据，直接插入新的数据
            self.insert_adjust_factor(code=code,
                                      divid_operate_date=divid_operate_date,
                                      fore_adjust_factor=fore_adjust_factor,
                                      back_adjust_factor=back_adjust_factor,
                                      adjust_factor=adjust_factor)
            return True
        else:
            # 数据库异常的处理
            return False

    # 查询复权因子
    def query_adjust_factor(self,
                            code='sh.600000',
                            divid_operate_date='0000/00/00'):
        self.__connect_mongo()
        # gl.info(f'尝试查询 {code} {divid_operate_date} 的复权因子数据')
        adjust_factor_search = AdjustFactor.objects(
            code=code, divid_operate_date=divid_operate_date, is_delete=False)
        if adjust_factor_search.count() == 1:
            return adjust_factor_search[0]
        elif adjust_factor_search.count() == 0:
            # gl.info(f'{code} 复权因子数据不存在')
            return None
        else:
            gl.critical(f'{code} 复权因子数据超过1条，请检查代码')
            return False

    # 批量插入复权因子
    def insert_adjust_factor_list(self, adjust_factor_list):
        """
        批量插入复权因子
        adjust_factor_list: AdjustFactor的数组
        """

        insert_list = []
        update_list = []

        # 校验 adjust_factor_list
        for i in adjust_factor_list:
            if not isinstance(i, AdjustFactor):
                gl.error('批量插入指数信息失败，adjust_factor_list 类型不匹配')
                return False

        # 数据库连接
        self.__connect_mongo()

        # 确认了stock_info_list的成员结构
        # 进行遍历,查询库里是否有数据，如果有则把这条stock_info从list中剔除
        adjust_factor_search = AdjustFactor.objects()

        gl.info(f'库中已经有 AdjustFactor {len(adjust_factor_search)} 条')

        if len(adjust_factor_search) > 0:
            # 查重
            # 库里有数据，则遍历
            pbar = tqdm.tqdm(adjust_factor_list)
            for i in pbar:
                to_update_list = []
                for j in adjust_factor_search:
                    if j.code == i.code and j.divid_operate_date == i.divid_operate_date:
                        # 如果有Code与复权日相同的数据，则添加到待更新列表
                        to_update_list.append(j)

                if len(to_update_list) == 1:
                    # 待更新列表有且只有一个，则判断数值是否相同，如有不同，添加到更新列表
                    is_different = False
                    columns = [
                        'fore_adjust_factor', 'back_adjust_factor',
                        'adjust_factor'
                    ]
                    for c in columns:
                        if i[c] != to_update_list[0][c]:
                            is_different = True
                            to_update_list[0][c] = i[c]

                    if is_different:
                        update_list.append(to_update_list[0])
                elif len(to_update_list) == 0:
                    insert_list.append(i)

                elif len(to_update_list) > 1:
                    gl.critical('数据库异常，AdjustFactor的数量超过1')

                pbar.set_description(f"Querying {i.code} AdjustFactor")
        else:
            # 库里不存在
            for i in adjust_factor_list:
                insert_list.append(i)

        # 批量插入Mongo
        if len(insert_list) > 0:
            # for i in insert_list:
            # i.update()
            AdjustFactor.objects.insert(insert_list)
        gl.info(f'插入AdjustFactor {len(insert_list)} 条')
        # 更新
        if len(update_list) > 0:
            pbar = tqdm.tqdm(update_list)
            for i in pbar:
                i.update_time()
                i.save()
                pbar.set_description(f"Updateing {i.code} AdjustFactor")
        gl.info(f'更新StockInfo {len(update_list)} 条')

        return True

    # 获取某只股票的复权因子数据
    def get_adjust_factors(self, code='sh.600000'):
        self.__connect_mongo()
        # gl.info(f'尝试查询 {code} 的复权因子数据')
        adjust_factor_search = AdjustFactor.objects(code=code, is_latest=True)

        if adjust_factor_search.count() == 0:
            # gl.info(f'{code}复权因子数据不存在')
            return None
        else:
            return adjust_factor_search

    # 添加Stock日交易数据
    def insert_day_bar(self,
                       date='0000/00/00',
                       code='sh.600000',
                       open=0.0,
                       high=0.0,
                       low=0.0,
                       close=0.0,
                       preclose=0.0,
                       volume=0,
                       amount=0,
                       adjust_flag=0,
                       turn=0.0,
                       trade_status=0,
                       pct_change=0.0,
                       is_ST=0):

        self.__connect_mongo()
        with mongoengine.context_managers.switch_collection(DayBar, code):
            bar = DayBar(date=date,
                         code=code,
                         open=open,
                         high=high,
                         low=low,
                         close=close,
                         preclose=preclose,
                         volume=volume,
                         amount=amount,
                         adjust_flag=adjust_flag,
                         turn=turn,
                         trade_status=trade_status,
                         pct_change=pct_change,
                         is_ST=is_ST)
            bar.save()

        # gl.info(f'成功创建 {code} {date} 的DayBar信息')

    # 更新Stock日交易数据
    def update_day_bar(self,
                       date='0000/00/00',
                       code='sh.600000',
                       open=0.0,
                       high=0.0,
                       low=0.0,
                       close=0.0,
                       preclose=0.0,
                       volume=0,
                       amount=0,
                       adjust_flag=0,
                       turn=0.0,
                       trade_status=0,
                       pct_change=0.0,
                       is_ST=0):
        # 尝试查询数据库
        day_bar_search = self.query_day_bar(code=code, date=date)
        if day_bar_search:
            # 更新数据
            has_changed = False
            if day_bar_search.open != open:
                day_bar_search.open = open
                has_changed = True
            if day_bar_search.high != high:
                day_bar_search.high = high
                has_changed = True
            if day_bar_search.low != low:
                day_bar_search.low = low
                has_changed = True
            if day_bar_search.close != close:
                day_bar_search.close = close
                has_changed = True
            if day_bar_search.preclose != preclose:
                day_bar_search.preclose = preclose
                has_changed = True
            if day_bar_search.volume != volume:
                day_bar_search.volume = volume
                has_changed = True
            if day_bar_search.amount != amount:
                day_bar_search.amount = amount
                has_changed = True
            if day_bar_search.adjust_flag != adjust_flag:
                day_bar_search.adjust_flag = adjust_flag
                has_changed = True
            if day_bar_search.turn != turn:
                day_bar_search.turn = turn
                has_changed = True
            if day_bar_search.trade_status != trade_status:
                day_bar_search.trade_status = trade_status
                has_changed = True
            if day_bar_search.pct_change != pct_change:
                day_bar_search.pct_change = pct_change
                has_changed = True
            if day_bar_search.is_ST != is_ST:
                day_bar_search.is_ST = is_ST
                has_changed = True

            if has_changed:
                day_bar_search.update_time()
                day_bar_search.save()
                # gl.info(f'{code} 日交易数据已更新')
            else:
                # gl.info(f'{code} 日交易数据无更新')
                pass

        elif day_bar_search is None:
            # 插入数据
            self.insert_day_bar(date=date,
                                code=code,
                                open=open,
                                high=high,
                                low=low,
                                close=close,
                                preclose=preclose,
                                volume=volume,
                                amount=amount,
                                adjust_flag=adjust_flag,
                                turn=turn,
                                trade_status=trade_status,
                                pct_change=pct_change,
                                is_ST=is_ST)
        else:
            return False

    # 查询Stock日交易数据
    def query_day_bar(self, code='sh.600000', date='0000/00/00'):
        self.__connect_mongo()
        with mongoengine.context_managers.switch_collection(DayBar, code):
            # gl.info(f'尝试查询 {code} {date} 的日交易数据')
            day_bar_search = DayBar.objects(code=code, date=date)
            if day_bar_search.count() == 1:
                return day_bar_search[0]
            elif day_bar_search.count() == 0:
                # gl.info(f'{code} {date} 日交易数据不存在')
                return None
            else:
                gl.critical(f'{code} {date} 日交易数据超过1条，请检查代码')
                return False
            pass

    # 批量插入日交易数据
    def insert_day_bar_list(self, code, day_bar_list):
        """
        批量插入日交易数据
        code:代码编号，用来确定数据插入到哪个集合
        day_bar_list: Daybar的数组
        """

        insert_list = []
        update_list = []

        # 校验 adjust_factor_list
        for i in day_bar_list:
            if not isinstance(i, DayBar):
                gl.error('批量插入日交易信息失败，day_bar_list 类型不匹配')
                return False

        # 数据库连接
        self.__connect_mongo()
        # 确认了day_bar_list的成员结构
        with mongoengine.context_managers.switch_collection(DayBar, code):
            for i in day_bar_list:
                DayBar.objects(date=i.date).update_one(
                    upsert=True,
                    code=i.code,
                    open=i.open,
                    high=i.high,
                    low=i.low,
                    close=i.close,
                    preclose=i.preclose,
                    volume=i.volume,
                    amount=i.amount,
                    adjust_flag=i.adjust_flag,
                    turn=i.turn,
                    tradestatus=i.tradestatus,
                    pct_change=i.pct_change,
                    is_ST=i.is_ST)
        return True

    # 插入Stock 5min交易数据

    # 更新Stock 5min交易数据

    # 查询Stock 5min交易数据

    def test(self, *args, **kwargs):
        # self.update_stock_info(has_min_bar=False, trade_status=0)
        # self.get_all_stock_code()
        # r = self.query_stock_info(code='sh.000001')
        # self.insert_day_bar(code='sh.002001')
        # s = self.query_day_bar('sh.002001')
        # print(s)
        pass


ginkgo_storage = GinkgoStorage()