"""
引擎类

用于模拟回测，验证策略

# TODO 实盘操作
"""

import queue
import time, datetime
from ginkgo.libs.enums import EventType, InfoType



class Ginkgo_Engine(object):
    def __init__(self, strategy, portfolio, heartbeat: float):
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
                info = self.info_list.get(False)
                to_do_events = self.portfolio.get_new_info(info)
                if to_do_events is not None:
                    for event in to_do_events:
                        self._add_event(event)
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
                            to_do_events = self.portfolio.get_signal(event)
                        elif event.type == EventType.Signal:
                            self.signals += 1
                            to_do_events = self.portfolio.get_signal(event)
                        elif event.type == EventType.Order:
                            ordered_done = self.portfolio.excute_order(event)
                            if ordered_done:
                                self.orders += 1
                        elif event.type == EventType.Fill: # 暂时没搞明白这个fill是个啥
                            self.fills += 1
                            self.portfolio.update_fill(event)

                        if to_do_events is not None:
                            for event in to_do_events:
                                self._add_event(event)
            time.sleep(self.heartbeat)

    def _add_event(self, event):
        if event.type is not (EventType.Market or EventType.Signal
                              or EventType.Order or EventType.Fill):
            print('Event type is unknown!')
        else:
            self.event_list.put(event)

    def _add_info(self, info):
        if (info.type is InfoType.Message) or (
                info.type is InfoType.MinutePrice) or (info.type is
                                                       InfoType.DailyPrice):
            self.info_list.put(info)
        else:
            print('Info type is unknown!')

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
