"""
HistoricEngine 模块

该模块实现了一个历史回测引擎，用于模拟金融市场的历史事件处理。
核心功能包括事件循环、时间推进、以及事件处理。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
    from ginkgo.backtest.events.base_event import EventBase
    from ginkgo.backtest.feeders.base_feed import BaseFeed
    from ginkgo.enums import EVENT_TYPES

import datetime
import sys
from time import sleep
from queue import Queue, Empty
from threading import Thread, Event


from ginkgo.backtest.engines.event_engine import EventEngine
from ginkgo.backtest.events import EventNextPhase
from ginkgo.libs import datetime_normalize, GCONF, time_logger


class HistoricEngine(EventEngine):
    """
    历史回测引擎类

    继承自 EventEngine，用于处理历史数据回测中的事件循环和时间推进。
    支持设置回测时间范围、时间间隔，并处理事件队列中的事件。
    """

    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "HistoricEngine", interval: int = 1, *args, **kwargs) -> None:
        super(HistoricEngine, self).__init__(name, interval, *args, **kwargs)
        self._backtest_interval = datetime.timedelta(days=1)  # TODO Next step could be set up in future.
        self._start_date = None
        self._end_date = None
        self._max_waits = 4
        self._empty_count = 0

    @property
    def max_waits(self) -> int:
        return self._max_waits

    @max_waits.setter
    def max_waits(self, value: int) -> None:
        if not isinstance(value, int):
            self.log("ERROR", f"{type(self)}:{self.name} set max_waits {value} error.")
            return
        self._max_waits = value

    @property
    def start_date(self) -> datetime.datetime:
        return self._start_date

    @start_date.setter
    def start_date(self, value: any) -> None:
        try:
            self._start_date = datetime_normalize(value)
            self.log("INFO", f"{type(self)}:{self.name} set DATESTART {self.start_date}.")
        except Exception as e:
            self.log("ERROR", f"{type(self)}:{self.name} set start_date failed: {e}")

    @property
    def end_date(self) -> datetime.datetime:
        return self._end_date

    @end_date.setter
    def end_date(self, value: any) -> None:
        try:
            self._end_date = datetime_normalize(value)
            self.log("INFO", f"{type(self)}:{self.name} set DATEEND {self.end_date}.")
        except Exception as e:
            self.log("ERROR", f"{type(self)}:{self.name} set end_date failed: {e}")

    def set_backtest_interval(self, interval: str) -> None:
        interval = interval.upper()
        if interval == "DAY":
            self._backtest_interval = datetime.timedelta(days=1)
        elif interval == "MIN":
            self._backtest_interval = datetime.timedelta(minutes=1)
        else:
            self.log("ERROR", f"{type(self)}:{self.name} set INTERVAL failed: Unsupported interval type '{interval}'.")
        self.log("INFO", f"{type(self)}:{self.name} set INTERVAL {self._backtest_interval}.")

    @time_logger
    def main_loop(self, flag) -> None:
        """
        The EventBacktest Main Loop.
        """
        if not isinstance(flag, Event):
            self.log("ERROR", f"{self.name} main_loop: flag must be an instance of threading.Event.")
            return

        while self._active:
            if flag.is_set():
                break
            try:
                # Get a event from events_queue
                event: EventBase = self._queue.get(block=True, timeout=0.05)
                # Pass the event to handle
                self._process(event)
                self._empty_count = 0
            except Empty:
                self.next_phase()
            finally:
                pass

            # Break for a while
            sleep(0.002)
        self.log("INFO", f"Engine: {self.name} Main Loop End.")

    def next_phase(self, *args, **kwargs) -> None:
        if self.now is None and self.start_date is None:
            self.log("ERROR", f"{self.name} Check the code. There is no start_date or now.")
            self.stop()
            sys.exit(0)

        if self.now is None:
            self._now = datetime_normalize(self.start_date)

        # Exit Condition
        try:
            if self.now >= self.end_date:
                self._empty_count += 1
                if self._empty_count >= self.max_waits:
                    self.stop()
                    # Exit the programe
                    sys.exit(0)
                return
            self._now = self.now + self._backtest_interval
        except Exception as e:
            import pdb

            pdb.set_trace
            print(e)

        if self.matchmaking is None:
            self.log("ERROR", f"{self.name} Check the code. There is no matchmaking.")
            self.stop()
            sys.exit(0)
        self.matchmaking.on_time_goes_by(self.now)

        if self.datafeeder is None:
            self.log("ERROR", f"{self.name} Check the code. There is no datafeeder.")
            self.stop()
            sys.exit(0)
        self.datafeeder.on_time_goes_by(self.now)

        if len(self.portfolios) == 0:
            self.log("ERROR", f"{self.name} Check the code. There is no portfolio.")
            self.stop()
            sys.exit(0)
        else:
            self.log("INFO", f"{self.name} Go NextDay {self.now}.")
            for i in self.portfolios:
                i.on_time_goes_by(self.now)

        # 执行所有的钩子函数
        for hook in self._time_hooks:
            try:
                hook(self.now)  # 传递当前时间
                self.log("DEBUG", f"Executed time hook {hook.__name__} at {self.now}.")
            except Exception as e:
                self.log("ERROR", f"Error executing time hook {hook.__name__}: {e}")
            finally:
                pass
