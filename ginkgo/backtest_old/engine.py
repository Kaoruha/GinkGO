"""
引擎类

用于模拟回测，验证策略

# TODO 实盘操作
"""

import queue
import time
import datetime
from threading import Thread

from ginkgo.libs.enums import EventType, InfoType


class Ginkgo_Engine(object):
    def __init__(self, portfolio, heartbeat: float):
        self.runs_loop: int = 0
        self._active: bool = True
        self.portfolio = portfolio
        self.heartbeat = heartbeat  # 心跳时间，若为0则不进行休息
        self.info_list = queue.Queue()
        self.event_list = queue.Queue()
        self._thread: Thread = Thread(target=self._run, name='EngineThread')
        self.signals: int = 0
        self.orders: int = 0
        self.fills: int = 0

    def _run(self):
        while self._active:
            # 判断引擎状态
            # 处理数据列表
            try:
                info = self.info_list.get(False)
                to_do_events = self.portfolio.get_info(info)
                if len(to_do_events) > 0:
                    for event in to_do_events:
                        self.add_event(event)
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
                            to_do_events = self.portfolio.get_info(info=event)
                        elif event.type == EventType.Signal:
                            self.signals += 1
                            to_do_events = self.portfolio.get_signal(signal=event)
                        elif event.type == EventType.Order:
                            ordered_done = self.portfolio.excute_order(order=event)
                            if ordered_done:
                                self.orders += 1
                        elif event.type == EventType.Fill:  # 暂时没搞明白这个fill是个啥
                            self.fills += 1
                            self.portfolio.update_fill(event)

                        if to_do_events is not None:
                            for event in to_do_events:
                                self.add_event(event)
            if self.heartbeat is not 0:
                time.sleep(self.heartbeat)
            # print(f'Heart Beating {self.heartbeat}')

    def put_event(self, event):
        if (event.type is EventType.Market) or (event.type is EventType.Order) or (
                event.type is EventType.Signal) or (event.type is EventType.Fill):
            self.event_list.put(event)
        else:
            print('Event type is unknown!')

    def put_info(self, info):
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

    def engine_resume(self):
        """
        引擎休眠
        """
        self._active = True

    def start(self) -> None:
        """
        Start event engine to process events and generate timer events.
        """
        self._active = True
        self._thread.start()

    def stop(self) -> None:
        """
        Stop event engine.
        """
        self._active = False
        self._thread.join()
