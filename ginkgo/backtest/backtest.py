"""
引擎类
用于模拟回测，验证策略
# TODO 实盘操作
"""

import queue
from ginkgo.libs.enums import EventType, InfoType
from ginkgo.backtest.info import InfoPrice
import time, datetime


class BeuBacktest(object):
    def __init__(self, strategy, portfolio,
                 heartbeat: float):
        self.strategy = strategy
        self.portfolio = portfolio
        self.heartbeat = heartbeat
        self.info_list = queue.Queue()
        self.event_list = queue.Queue()
        self.signals = 0
        self.orders = 0
        self.fills = 0

    def _run(self):
        while True:
            # 处理数据列表
            try:
                print(f'Now the info_list has {self.info_list.qsize()} elements!')
                info = self.info_list.get(False)
                to_do_events = self.portfolio.get_new_info(info)
                if to_do_events is not None:
                    for e in to_do_events:
                        self._add_evnet(e)
            except queue.Empty:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f'Data_list is Empty!! {now}')
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
                            self.signals += 1
                            self.portfolio.update_signal(event)
                        elif event.type == EventType.Order:
                            self.orders += 1
                            self.portfolio.excute_order(event)
                        elif event.type == EventType.Fill:
                            self.fills += 1
                            self.portfolio.update_fill(event)
            time.sleep(self.heartbeat)

    def _add_evnet(self, event):
        if event.type is not (EventType.Market or EventType.Signal or EventType.Order or EventType.Fill):
            print('Event type is unknown!')
            return
        self.event_list.put(event)

    def _add_info(self, info):
        # print(info.type is not (InfoType.Price or InfoType.Message))
        if (info.type is not (InfoType.Price or InfoType.Message)):
            print('Info type is unknown!')
            return
        self.info_list.put(info)

    def _output_performance(self):
        """
        调用评价类，输出此次回测的结果
        """
        # self.portfolio.create_equity_curve_dataframe()

        # print("Creating summary stats...")
        # stats = self.portfolio.output_summary_stats()

        # print("Creating equity curve...")
        # print(self.portfolio.equity_curve.tail(10))

        # print("Signals: %s" % self.signals)
        # print("Orders: %s" % self.orders)
        # print("Fills: %s" % self.fills)
        pass

    def simulate_trading(self):
        """
        Simulates the backtest and outputs portfolio performance.
        """
        self._run()
        self._output_performance()
