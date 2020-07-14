import queue
from app.libs.enums import EventType
import time

class BeuBacktest(object):
    def __init__(self, data, strategy, portfolio, heartbeat):
        self.data = data
        self.strategy = strategy
        self.portfolio = portfolio
        self.heartbeat = heartbeat
        self.event_list = queue.Queue()
        self.signals = 0
        self.orders = 0
        self.fills = 0
        pass

    def _run(self):
        while True:
            # 获取一条数据


            # 处理事件列表
            while True:
                try:
                    event = self.event_list.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        if event.type = EventType.Market:
                            self.strategy.calculate_signals(event)
                            self.portfolio.update_timeindex(event)
                        elif event.type == EventType.Signal:
                            self.signals +=1
                            self.portfolio.update_signal(event)
                        elif event.type == EventType.Order:
                            self.orders +=1
                            self.portfolio.excute_order(event)
                        elif event.type == EventType.Fill:
                            self.fills +=1
                            self.portfolio.update_fill(event)
            time.sleep(self.heartbeat)

    def _output_performance(self):
        """
        Outputs the strategy performance from the backtest.
        """
        self.portfolio.create_equity_curve_dataframe()
        
        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()
        
        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))
        pprint.pprint(stats)

        print("Signals: %s" % self.signals)
        print("Orders: %s" % self.orders)
        print("Fills: %s" % self.fills)

    def simulate_trading(self):
        """
        Simulates the backtest and outputs portfolio performance.
        """
        self._run()
        self._output_performance()    