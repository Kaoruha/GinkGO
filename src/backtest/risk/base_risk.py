"""
风控类
"""
import abc
from src.backtest.event_engine import EventEngine
from src.backtest.events import SignalEvent


class BaseRisk(abc.ABC):
    """
    风控基类
    回头改成抽象类
    """

    def __init__(self, name="基础风控") -> None:
        self.name = name
        self.engine = None

    def engine_register(self, engine: EventEngine) -> EventEngine:
        # 引擎注册，通过Broker的注册获得引擎实例
        self.engine = engine
        return self.engine

    @abc.abstractmethod
    def risk_analyze(self, *args, **kwargs) -> SignalEvent:
        raise NotImplementedError("Must implement risk_analyze()")

    def risk_process(self, *args, **kwargs):
        r = self.risk_analyze(args=args, kwargs=kwargs)
        if r is not None:
            self.engine.put(r)
