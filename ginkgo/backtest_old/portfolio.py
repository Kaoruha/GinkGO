"""
资产组合类

"""
import pandas as pd
from ginkgo.libs.enums import InfoType, MarketType
from ginkgo.backtest_old.strategies.base_strategy import BaseStrategy
from ginkgo.backtest_old.hold_info import HoldInfo
from ginkgo.backtest_old.trade_info import TradeInfo
from ginkgo.backtest_old.events import SignalEvent, OrderEvent


class Portfolio(object):
    """
    资产管理类，负责接收信息、处理事件、执行下单等操作
    """

    # 初始化
    def __init__(self, name, *, stamp_tax=.0015, fee=.00025, init_capital=100000):
        self.name = name
        self._stamp_tax = stamp_tax  # 设置印花税，默认千1.5
        self._fee = fee  # 设置交易税,默认万2.5
        self._init_capital = init_capital  # 设置初始资金，默认100K
        self.capital = self._init_capital
        self.daily = {}
        self.minute = {}
        self.strategies = []
        self.capital_controls = []
        self.risk_controls = []
        self.hold = []  # 'code': ['price', 'amount']
        self.trades = []  # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 以后会支持港股美股日股等乱七八糟的市场

    # 策略注册
    def register_strategy(self, new_strategy):
        """
        策略注册

        :param new_strategy: 新策略
        :type new_strategy: BaseStrategy的衍生类
        """
        if isinstance(new_strategy, BaseStrategy):
            # TODO 查重
            self.strategies.append(new_strategy)
            print(f'{type(new_strategy)} 策略注册成功')
        else:
            print('注册失败，待注册待策略应该是BaseStrategy的衍生类')

    # 重新设置初始资金
    def reset_capital(self, capital: int):
        """
        重新设置初始资金

        :param capital: 初始资金
        :type capital: int
        """
        self._init_capital = capital

    # Portfolio获取新信息后的处理
    def get_info(self, info):
        """
        Portfolio获取新信息

        :param info: 市场信息或者价格信息
        :type info: Info的继承类
        """
        try:
            if info.type == InfoType.DailyPrice:
                self.__handle_new_price(info=info)
            elif info.type == InfoType.MinutePrice:
                self.__handle_new_price(info=info)
            elif info.type == InfoType.Message:
                self.__handle_new_msg(info=info)

            data = {
                'daily': self.daily,
                'minute': self.minute
            }
            signals = []
            for strategy in self.strategies:
                strategy.data_transfer(data)
                signal = (strategy.check())  # TODO 准备接收信号对象
                if signal is not None:
                    signals.append(signal)
            print(signals)
            return signals  # 返回所有信号
        except Exception as e:
            print(e)
            return []  # 如果发生异常，返回空信号

    # 获取新的价格信息
    def __handle_new_price(self, info):
        """
        处理新获取价格信息
        记录——排序（计算指标）

        :param info: 价格信息，包含数据为DataFrame
        :type info: DailyPrice 或 MinutePrice
        """
        # 1、交易数据记录
        if info.type == InfoType.DailyPrice:
            # 记录日交易数据
            self.__daily_bar_writer(info.data)
        elif info.type == InfoType.MinutePrice:
            # 记录分钟交易数据
            self.__minute_bar_writer(info.data)

        # 2、按照时间顺序将交易数据重新排序
        for code in self.daily:
            self.daily[code] = self.daily[code].sort_values(by='date',
                                                            ascending=True,
                                                            axis=0)
        for code in self.minute:
            self.minute[code] = self.minute[code].sort_values(by='time',
                                                              ascending=True,
                                                              axis=0)
        # 2、计算各种指标，记录价格信息
        # 2.1、将daily里的交易信息按照时间顺序排序

        # 2.2、计算逐个股票的MACD TODO转移至策略类计算
        self.__average_line_calculate(span=5)

    # 处理新的市场信息
    def __handle_new_msg(self, info: InfoType.Message):
        # TODO 处理新的市场信息
        pass

    # 获取新的信号
    def get_signal(self, signal: SignalEvent):

        data = {
            'daily': self.daily,
            'minute': self.minute
        }

        should_take_order = True
        for capital in self.capital_controls:
            capital.data_transfer(data)
            capital.signal_transfer(signal=signal)
            if capital.check():
                volume = 100  # TODO 确定量
                price = 2.1  # TODO 确定价格
            else:
                should_take_order = False
        if should_take_order:
            order = OrderEvent(buy_or_sell=signal.buy_or_sell, code=signal.code, price=price, volume=volume)
            return order
        else:
            return None

            # 获取价格信息的股票代码

    @staticmethod
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
            'volume', 'adjustflag', 'turn', 'tradestatus', 'pctChg', 'isST'
        ]
        if code in self.daily:
            self.daily[code] = self.daily[code].append(daily_bar.T,
                                                       ignore_index=True)
            self.daily[code] = self.daily[code].drop_duplicates()
        else:
            self.daily[code] = pd.DataFrame(columns=daily_columns)
        # print(self.daily[code])

    def __average_line_calculate(self, span: int):
        ma_title = 'MA_' + str(span)
        for code in self.daily:
            self.daily[code][ma_title] = self.daily[code]['close'].rolling(span, min_periods=1).mean()

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
        # print(self.minute[code])

    # 执行下单操作
    def excute_order(self, order):
        # 模拟
        trade = TradeInfo(code=order.code, date=order.date, price=order.price, amount=order.amount, order_id=order.id)
        self.trades.append(trade)

        # 实盘
        # 发送下单信息
        # 确认下单成功
        # 修改现金
        # 查询是否下单成功
        # 修改持有
        return True
