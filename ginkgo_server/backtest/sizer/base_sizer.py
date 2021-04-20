"""
仓位管理类
"""
import datetime
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.events import SignalEvent
import abc


class BaseSizer(metaclass=abc.ABCMeta):
    """
    仓位管理基类

    """

    def __init__(self):
        self._engine = None
        self._init_capital: float = 0.0

    def __call__(self):
        engine_status = "未挂在引擎" if self._engine is None else f"已挂载引擎 {self._engine}"
        print(f"仓位管理基类，{engine_status}, 金额: {self._init_capital}")

    def engine_register(self, engine: EventEngine):
        """
        引擎注册，通过Broker的注册获得引擎实例

        :param engine: [description]
        :type engine: EventEngine
        """
        self._engine = engine

    def set_init_capital(self, init_capital: float):
        """
        获取初始总金额

        :param init_capital: [description]
        :type init_capital: int
        """
        self._init_capital = init_capital

    def get_signal(self, event: SignalEvent, capital: float, position):
        """
        获取信号事件
        根据初始金额、手持现金、当前持仓进行仓位调整，产生订单事件OrderEvent
        :param event: 某只股票的多空信号
        :param capital: 当前手持现金
        :param position: 当前持仓
        :return: void
        """
        raise NotImplementedError("Must implement get_buy_signal()")

    def _get_trade_date(self, event: SignalEvent):
        """
        根据信号事件的日期，返回下单日期

        此处利用到了未来的数据，需要当心
        :param event: 信号事件
        :return: 下单日期
        """
        code = event.code
        signal_date = event.date
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            df = gm.query_stock(
                code=code,
                start_date=signal_date,
                end_date=today,
                frequency="d",
                adjust_flag=3,
            )["date"].head(2)
            return df.iloc[1]
        except Exception as e:
            return None
