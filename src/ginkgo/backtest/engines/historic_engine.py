from ginkgo.backtest.engine.event_engine import EventEngine


class HistoricEngine(EventEngine):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False
    pass
