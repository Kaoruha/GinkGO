"""
回测类
用于模拟回测，验证策略
"""

import queue
from app.libs.enums import EventType
import time
import pandas as pd

class BeuBacktest(object):
    def __init__(self, data:pd.DataFrame, strategy, portfolio, heartbeat:float):
        self.data = data
        self.strategy =strategy
        self.portfolio = portfolio
        self.heartbeat = heartbeat
        self.event_list = queue.Queue()
        self.signals = 0
        self.orders = 0
        self.fills = 0

    def _run(self):
        series = self.data.copy(deep=True)
        while True:
            # 获取一条数据
            self.portfolio.get_new_price(series.head(1))
            # 处理事件列表
            while True:
                try:
                    event = self.event_list.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        if event.type == EventType.Market:
                            self.portfolio.get_signal(event)
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
            series.drop(index=0)

    def _output_performance(self):
        """
        调用评价类，输出此次回测的结果
        """
        self.portfolio.create_equity_curve_dataframe()
        
        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()
        
        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))

        print("Signals: %s" % self.signals)
        print("Orders: %s" % self.orders)
        print("Fills: %s" % self.fills)

    def simulate_trading(self):
        """
        Simulates the backtest and outputs portfolio performance.
        """
        self._run()
        self._output_performance()    