"""
资产组合类

"""
import pandas as pd
from ginkgo.libs.enums import InfoType


class Portfolio(object):
    """
    资产管理类，负责接收信息、处理事件、执行下单等操作
    """
    def __init__(self, *, stamp_tax=.001, fee=0.0000687, init_capital=100000):
        self._stamp_tax = stamp_tax  # 设置印花税
        self._fee = fee  # 设置交易税
        self._init_capital = init_capital  # 设置初始资金
        self.daily = {}
        self.minute = {}

    def get_new_info(self, info):
        """
        处理新获取的信息

        :param info: 市场信息或者价格信息
        :type info: Info的继承类
        """
        try:
            if info.type == InfoType.DailyPrice:
                self.__get_new_price(info=info)
                # TODO 将需要的信息交给策略类
            elif info.type == InfoType.MinutePrice:
                self.__get_new_price(info=info)
            elif info.type == InfoType.Message:
                self.__get_new_msg(info=info)
        except Exception as e:
            print(e)

    # 获取新的价格信息
    def __get_new_price(self, info):
        """
        获取价格信息

        :param info: 价格信息，包含数据为DataFrame
        :type info: DailyPrice 或 MinutePrice
        :return: [description]
        :rtype: [type]
        """
        # 1、交易数据记录
        if info.type == InfoType.DailyPrice:
            # 记录日交易数据
            self.__daily_bar_writer(info.data)
        elif info.type == InfoType.MinutePrice:
            # 记录分钟交易数据
            self.__minute_bar_writer(info.data)
        # 2、计算各种指标，记录价格信息
        self.__macd_calculate()

    def __get_new_msg(self, info: InfoType.Message):
        # TODO 处理新的市场信息
        pass

    # 获取价格信息的股票代码
    def __get_code(self, df: pd.DataFrame):
        """
        获取传入价格信息等股票代码

        :param df: [股票价格信息]
        :type df: pd.DataFrame
        :return: [返回该价格信息等股票代码]
        :rtype: [string]]
        """
        code = df['code']
        return code

    # 日交易数据写入
    def __daily_bar_writer(self, daily_bar: pd.DataFrame):
        """
        日交易数据写入

        :param daily_bar: [日交易数据]
        :type daily_bar: [pd.DataFrame]
        """

        code = self.__get_code(daily_bar)
        daily_columns = [
            'date', 'code', 'open', 'high', 'low', 'close', 'preclose',
            'volume', 'adjustflag', 'turn', 'tradestatus', 'pctChg', 'isST',
            'MA5', 'MA10', 'MA20', 'MA30', 'MA60', 'MA120'
        ]
        if code in self.daily:
            self.daily[code] = self.daily[code].append(daily_bar.T,
                                                       ignore_index=True)
            self.daily[code] = self.daily[code].drop_duplicates()
        else:
            self.daily[code] = pd.DataFrame(columns=daily_columns)
        print(self.daily[code])

    # 5分钟交易数据写入
    def __minute_bar_writer(self, minute_bar):
        minute_columns = [
            'date', 'time', 'code', 'open', 'high', 'low', 'close', 'volume',
            'amount', 'adjustflag'
        ]
        # 分钟交易数据写入
        code = self.__get_code(minute_bar)
        # 分钟数据处理
        if code in self.minute:
            # 去重
            self.minute[code] = self.minute[code].append(
                minute_bar.T, ignore_index=True).drop_duplicates()
        else:
            self.minute[code] = pd.DataFrame(columns=minute_columns)
        print(self.minute[code])

    # MACD计算
    def __macd_calculate(self):
        """
        负责计算MACD值
        """
        # 1、将daily，minute里的交易信息按照时间顺序排序
        # 1.1、将daily里的交易信息按时间排序
        # 1.2、将minute里的交易信息按时间排序
        # 2、计算逐个股票的MACD
        pass

    def excute_order(self, event):
        pass