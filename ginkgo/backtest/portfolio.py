"""
资产组合类

"""
from ginkgo.libs.enums import InfoType
import pandas as pd


class Portfolio(object):
    def __init__(self, *, stamp_tax=.001, fee=0.0000687, init_captial = 100000):
        self._stamp_tax = stamp_tax
        self._fee = fee
        self._init_captial = init_captial

    def get_new_info(self, info):
        try:
            if info.type == InfoType.Price:
                self.__get_new_price(info=info)
                pass
            elif info.type == InfoType.Message:
                self.__get_new_msg(info=info)
                pass
        except Exception as e:
            print(e)

    def __get_new_price(self, info: InfoType.Price):
        print(info.data.high)
        # TODO 处理新的价格信息
        # 计算各种指标，记录价格信息
        # 通过stratagy类校验
        return None

    def __get_new_msg(self, info: InfoType.Message):
        # TODO 处理新的市场信息
        pass