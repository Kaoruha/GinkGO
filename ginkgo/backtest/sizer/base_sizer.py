"""
仓位管理类
"""
import datetime
from ginkgo.data.data_portal import data_portal
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.event import SignalEvent
import abc


class BaseSizer(metaclass=abc.ABCMeta):
    """
    仓位管理基类
    回头改成抽象类
    """

    def engine_register(self, engine: EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine

    def get_init_capital(self, init_capital: int):
        self._init_capital = init_capital

    def get_signal(self, event: SignalEvent, capital: float, position):
        """
        仓位管理根据信号事件，手持现金，持仓进行仓位调整，通知Mather下单
        :param event: 某只股票的多空信号
        :param capital: 当前手持现金
        :param position: 当前持仓
        :return: void
        """
        raise NotImplementedError("Must implement get_buy_signal()")

    def _get_trade_date(self, event: SignalEvent):
        """
        根据下单信号的日期，返回下单日期
        :param event:下单信号事件
        :return: 返回下单日期
        """
        code = event.code
        signal_date = event.date
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        try:
            df = data_portal.query_stock(code=code, start_date=signal_date, end_date=today, frequency='d', adjust_flag=3)['date']
            return df.iloc[1]
        except Exception as e:
            return None
