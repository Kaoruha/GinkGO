"""
资产组合类

"""
from ginkgo.libs.enums import InfoType
import pandas as pd


class Portfolio(object):
    def __init__(self, *, stamp_tax=.001, fee=0.0000687, init_captial = 100000):
        self._stamp_tax = stamp_tax # 设置印花税
        self._fee = fee # 设置交易税
        self._init_captial = init_captial # 设置初始资金
        self.daily = {}
        self.minute = {}


    def get_new_info(self, info):
        """
        处理新获取的信息

        :param info: 市场信息或者价格信息
        :type info: Info的继承类
        """
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
        # print(info.data)
        # self.__daily_bar_writer(info.data)
        self.__minute_bar_writer(info.data)
        # TODO 处理新的价格信息
        # 分别处理分钟交易数据以及日交易数据
        # 计算各种指标，记录价格信息
        # 通过stratagy类校验
        return None

    def __get_new_msg(self, info: InfoType.Message):
        # TODO 处理新的市场信息
        pass

    def __get_code(self, df:pd.DataFrame):
        # 获取价格信息的股票代码
        code = df['code']
        return code

    def __daily_bar_writer(self, daily_bar):
        # 日交易数据写入
        code = self.__get_code(daily_bar)
        if code in self.daily:
            self.daily[code] = self.daily[code].append(daily_bar.T, ignore_index=True).drop_duplicates()
        else:
            self.daily[code] = pd.DataFrame(columns=('date','code','open','high','low','close','preclose','volume','adjustflag','turn','tradestatus','pctChg','isST'))
        print(self.daily[code])

    def __minute_bar_writer(self, minute_bar):
        # 分钟交易数据写入
        code = self.__get_code(minute_bar)
        # TODO 分钟数据处理
        if code in self.minute:
            # TODO 去重
            self.minute[code] = self.minute[code].append(minute_bar.T, ignore_index=True).drop_duplicates()
        else:
            self.minute[code] = pd.DataFrame(columns=('date','time','code','open','high','low','close','volume','amount','adjustflag'))
        print(self.minute[code])