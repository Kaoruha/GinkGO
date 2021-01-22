 # pylint: disable=no-member
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
from ginkgo_server.data.models.min5_bar import Min5Bar
from ginkgo_server.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD


class GinkgoStorage(object):
    _instance_lock = threading.Lock()

    # 单例模式
    def __new__(cls, *args, **kwargs):
        """
        Create a new instance
        """
        if not hasattr(cls, "_instance"):
            with GinkgoStorage._instance_lock:
                if not hasattr(cls, "_instance"):
                    GinkgoStorage._instance = super().__new__(cls)

            return GinkgoStorage._instance

    # 连接MongoDocker
    def __connect_mongo(self):
        """
        从Ginkgo_Server的Config内读取MongoDB的配置信息，尝试进行连接
        """
        # mongoengine.connect(
        #     db=DATABASE, host=HOST, port=PORT, username=USERNAME, password=PASSWORD
        # )
        mongoengine.connect(db=DATABASE, host=HOST, port=PORT)
        # TODO 连接结果输出，方便定位Bug

    # 判断数据库DB是否存在
    def __is_database_exists(self):
        pass

    # 判断集合Collection是否存在
    def __is_collection_exists(self):
        pass

    # 插入指数信息
    def insert_a_stock_info(self, code="sh.000001", code_name="上证综合指数", trade_status=1):
        """
        向MongoDB中插入StockInfo数据，包括代号、名称、交易状态、是否有分钟数据
        """
        self.__connect_mongo()
        info = StockInfo(code=code, code_name=code_name, trade_status=trade_status)
        info.save()
        # gl.info(f'成功创建 {code} 的指数基础信息')

    # 更新指数信息
    def update_stock_info(self, code="待更新指数", code_name="待更新指数", trade_status=1):
        """
        更新指数基本信息
        """
        # 尝试查询数据库
        data_search = self.query_stock_info(code=code)

        StockInfo.objects(code=code).update_one(
            upsert=True, code_name=code_name, trade_status=trade_status
        )

    # 查询指数信息
    def query_stock_info(self, code="sh.000001"):
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
            gl.critical(f"{code} 指数基本数据超过1条，请检查代码")
            return False

    # 批量插入指数信息
    def insert_stock_info_list(self, stock_info_list):
        """
        批量插入指数信息

        stock_info_list: StockInfo的数组
        """
        # 校验stock_info_list
        for i in stock_info_list:
            if not isinstance(i, StockInfo):
                gl.error("批量插入指数信息失败，stock_info_list 类型不匹配")
                return False

        self.__connect_mongo()
        # 确认stock_info_list的成员结构了，进行遍历,查询库里是否有数据，如果有则把这条stock_info从list中剔除
        pbar = tqdm.tqdm(stock_info_list)
        for i in pbar:
            StockInfo.objects(code=i.code).update_one(
                upsert=True, code_name=i.code_name, trade_status=i.trade_status
            )
            pbar.set_description(f"Updating {i.code} StockInfo")

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
            gl.info(f"查询到 {len(rs)} 条指数代码")
        else:
            gl.error(f"指数代码查询为空，请检查代码")

        return rs

    def get_all_min5_code(self):
        """
        获取所有有分钟数据的指数代码

        # TODO 等本地缓存模块完成，应该从本地缓存找起，找不到找远程Mongo,最后找不到尝试重新获取
        """
        self.__connect_mongo()
        stock_info_search = StockInfo.objects(has_min_bar=True)

        rs = []
        for i in stock_info_search:
            rs.append(i.code)

        if len(rs) > 0:
            gl.info(f"查询到 {len(rs)} 条指数代码")
        else:
            gl.error(f"指数代码查询为空，请检查代码")

        return rs

    # 插入复权因子数据
    def insert_adjust_factor(
        self,
        code="sh.000000",
        divid_operate_date="0000-00-00",
        fore_adjust_factor=0,
        back_adjust_factor=0,
        adjust_factor=0,
    ):
        """
        向MongoDB中插入AdjustFactor数据，
        
        包括代号、名称、前复权、后复权、复权因子
        """
        self.__connect_mongo()
        new_data = AdjustFactor(
            code=code,
            divid_operate_date=divid_operate_date,
            fore_adjust_factor=fore_adjust_factor,
            back_adjust_factor=back_adjust_factor,
            adjust_factor=adjust_factor,
        )
        new_data.save()
        # gl.info(f'成功创建 {code} 的复权信息')

    # 更新复权因子
    def update_adjust_factor(
        self,
        code="default",
        divid_operate_date="0000/00/00",
        fore_adjust_factor=0,
        back_adjust_factor=0,
        adjust_factor=0,
    ):
        AdjustFactor.objects(
            code=code, divid_operate_date=divid_operate_date
        ).update_one(
            upsert=True,
            fore_adjust_factor=fore_adjust_factor,
            back_adjust_factor=back_adjust_factor,
            adjust_factor=adjust_factor,
        )

    # 查询复权因子
    def query_adjust_factor(self, code="sh.600000", divid_operate_date="0000/00/00"):
        self.__connect_mongo()
        # gl.info(f'尝试查询 {code} {divid_operate_date} 的复权因子数据')
        adjust_factor_search = AdjustFactor.objects(
            code=code, divid_operate_date=divid_operate_date, is_delete=False
        )
        if adjust_factor_search.count() == 1:
            return adjust_factor_search[0]
        elif adjust_factor_search.count() == 0:
            # gl.info(f'{code} 复权因子数据不存在')
            return None
        else:
            gl.critical(f"{code} 复权因子数据超过1条，请检查代码")
            return False

    # 批量插入复权因子
    def insert_adjust_factor_list(self, adjust_factor_list):
        """
        批量插入复权因子
        adjust_factor_list: AdjustFactor的数组
        """

        # 校验 adjust_factor_list
        for i in adjust_factor_list:
            if not isinstance(i, AdjustFactor):
                gl.error("批量插入指数信息失败，adjust_factor_list 类型不匹配")
                return False

        # 数据库连接
        self.__connect_mongo()
        for i in adjust_factor_list:
            AdjustFactor.objects(
                code=i.code, divid_operate_date=i.divid_operate_date
            ).update_one(
                upsert=True,
                fore_adjust_factor=i.fore_adjust_factor,
                back_adjust_factor=i.back_adjust_factor,
                adjust_factor=i.adjust_factor,
            )

    # 获取某只股票的复权因子数据
    def get_adjust_factors(self, code="sh.600000"):
        self.__connect_mongo()
        # gl.info(f'尝试查询 {code} 的复权因子数据')
        adjust_factor_search = AdjustFactor.objects(code=code, is_latest=True)

        if adjust_factor_search.count() == 0:
            # gl.info(f'{code}复权因子数据不存在')
            return None
        else:
            return adjust_factor_search

    # 添加Stock日交易数据
    def insert_day_bar(
        self,
        code="sh.600000",
        date="0000/00/00",
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
        is_ST=0,
    ):
        """
        插入单挑日交易数据
        """
        self.__connect_mongo()
        with mongoengine.context_managers.switch_collection(DayBar, code):
            new_day_bar = DayBar(
                date=date,
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
                is_ST=is_ST,
            )
            new_day_bar.save()

        # gl.info(f'成功创建 {code} {date} 的DayBar信息')

    # 更新Stock日交易数据
    def update_day_bar(
        self,
        date="0000/00/00",
        code="sh.600000",
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
        is_ST=0,
    ):
        """
        更新某条日交易数据
        """
        DayBar.objects(date=date, code=code).update_one(
            upsert=True,
            open=open,
            high=high,
            low=low,
            close=close,
            preclose=preclose,
            volume=volume,
            adjust_flag=adjust_flag,
            trade_status=trade_status,
            pct_change=pct_change,
            is_ST=is_ST,
        )

    # 查询Stock日交易数据
    def query_day_bar(self, code="sh.600000", date="0000/00/00"):
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
                gl.critical(f"{code} {date} 日交易数据超过1条，请检查代码")
                return False
            pass

    # 批量插入日交易数据
    def insert_day_bar_list(self, code, day_bar_list):
        """
        批量插入日交易数据
        code:代码编号，用来确定数据插入到哪个集合
        day_bar_list: Daybar的数组
        """

        # 校验 adjust_factor_list
        for i in day_bar_list:
            if not isinstance(i, DayBar):
                gl.error("批量插入日交易信息失败，day_bar_list 类型不匹配")
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
                    is_ST=i.is_ST,
                )

    # 插入Stock 5min交易数据
    def insert_min5_bar(
        self,
        date="0000/00/00",
        code="待插入指数代码",
        time="19991111093500000",
        open=0.0,
        high=0.0,
        low=0.0,
        close=0.0,
        volume=0,
        amount=0,
        adjust_flag=0,
    ):
        self.__connect_mongo()
        with mongoengine.context_managers.switch_collection(Min5Bar, code + "_min5"):
            new_data = Min5Bar(
                date=date,
                code=code,
                time=time,
                open=open,
                high=high,
                low=low,
                close=close,
                volume=volume,
                amount=amount,
                adjust_flag=adjust_flag,
            )
            new_data.save()

    # 更新Stock 5min交易数据

    # 查询Stock 5min交易数据

    # 批量插入Stock_5min交易数据
    def insert_min5_bar_list(self, code, min5_bar_list):
        # 校验 min5_bar_list
        for i in min5_bar_list:
            if not isinstance(i, Min5Bar):
                gl.error("批量插入5min交易信息失败，min5_bar_list 类型不匹配")
                return False

        # 数据库连接
        self.__connect_mongo()
        # 确认了min5_bar_list的成员结构
        with mongoengine.context_managers.switch_collection(Min5Bar, code + "_min5"):
            Min5Bar.objects.insert(min5_bar_list)

    def get_day_bar_last_date(self, code="sh.000001"):
        self.__connect_mongo()
        with mongoengine.context_managers.switch_collection(DayBar, code) as NewDayBar:
            print(NewDayBar.objects.count())
            last = NewDayBar.objects.order_by("-date")[:1][0].date
        return last

    def get_min5_bar_last_date(self, code="sh.000001"):
        self.__connect_mongo()
        with mongoengine.context_managers.switch_collection(DayBar, code + "_min5"):
            last = DayBar.objects.order_by("-date")[:1][0].date
        return last

    def set_stock_has_min_bar(self, code="sh.000001", has_min_bar=False):
        result = StockInfo.objects(code=code)
        if len(result) == 1:
            result[0].set_min_bar(has_min_bar)
            result[0].save()

    def test(self):
        print(1)
        self.insert_min5_bar(code="sh.600000")
        print("Done")


ginkgo_storage = GinkgoStorage()
