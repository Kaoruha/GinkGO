"""
The EventDrivenBacktest class will provide a way to run an event-driven backtest, which involves listening for events (e.g. price updates, order fills) and executing trades based on the signals generated by the Strategy.

- Support both historic and live.

- Registering event handles to listen for specific types of events (e.g. price updates, order fills).

- Executing trades based on the signals generated by the Strategy in response to these events.

- Generating reports and metrics related to the performance of the backtesting system (By portfolio).
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
    from ginkgo.backtest.matchmakings import MatchMakingBase
    from ginkgo.backtest.events.base_event import EventBase
    from ginkgo.backtest.feeds.base_feed import BaseFeed
    from ginkgo.enums import EVENT_TYPES

import datetime
import sys
from time import sleep
from queue import Queue, Empty
from threading import Thread, Event
from ginkgo.backtest.engines.base_engine import BaseEngine
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize
from ginkgo.libs import GinkgoSingleLinkedList


class EventEngine(BaseEngine):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self, name: str = "EventEngine", interval: int = 1, *args, **kwargs
    ) -> None:
        super(EventEngine, self).__init__(name, *args, **kwargs)
        self._active = False
        self._interval: int = interval
        self._time_interval = datetime.timedelta(days=1)
        self._date_start = None
        self._date_end = None
        self._now = None
        self.set_date_start(20000101)
        self._duration = 10
        self._main_flag = Event()
        self._main_thread: Thread = Thread(
            target=self.main_loop, args=(self._main_flag,)
        )
        self._timer_flag = Event()
        self._timer_thread: Thread = Thread(
            target=self.timer_loop, args=(self._timer_flag,)
        )
        self._handles: dict = {}
        self._general_handles: list = []
        self._timer_handles: list = []
        self._queue: Queue = Queue()
        self._portfolios = GinkgoSingleLinkedList()
        self._matchmaking = None
        self._datafeeder = None

    @property
    def datafeeder(self):
        return self._datafeeder

    def bind_datafeeder(self, datafeeder: "BaseFeed"):
        self._datafeeder = datafeeder
        if self._datafeeder.engine is None:
            self._datafeeder.bind_engine(self)

    @property
    def now(self) -> datetime.datetime:
        return self._now

    @property
    def matchmaking(self) -> "MatchMakingBase":
        return self._matchmaking

    def bind_matchmaking(self, matchmaking: "MatchMakingBase") -> "MatchMakingBase":
        self._matchmaking = matchmaking
        if self.matchmaking.engine is None:
            self.matchmaking.bind_engine(self)
            GLOG.DEBUG(f"{type(self)}:{self.name} bind MATCHMAKING {matchmaking.name}.")
        GLOG.DEBUG(
            f"Bind Failed. {type(self)}:{self.name} already have MATCHMAKING {matchmaking.name}."
        )
        return self.matchmaking

    @property
    def portfolios(self) -> GinkgoSingleLinkedList:
        return self._portfolios

    def bind_portfolio(self, portfolio: "BasePortfolio") -> int:
        portfolio.set_backtest_id(self.backtest_id)
        self._portfolios.append(portfolio)
        GLOG.DEBUG(f"{type(self)}:{self.name} bind PORTFOLIO {portfolio.name}.")
        for i in self.portfolios:
            if i.value.engine is None:
                i.value.bind_engine(self)
        l = len(self.portfolios)
        GLOG.DEBUG(f"{type(self)}:{self.name} has {l} PORTFOLIOs.")
        # TODO set backtest_id
        return l

    @property
    def duration(self) -> int:
        return self._duration

    def set_duration(self, duration: int) -> int:
        self._duration = duration
        GLOG.DEBUG(f"{type(self)}:{self.name} set duration {duration}.")
        return self._duration

    @property
    def date_start(self) -> datetime.datetime:
        return self._date_start

    def set_date_start(self, date: any) -> datetime.datetime:
        self._date_start = datetime_normalize(date)
        self._now = self._date_start
        GLOG.DEBUG(f"{type(self)}:{self.name} set DATESTART {self.date_start}.")
        return self.date_start

    @property
    def date_end(self) -> datetime.datetime:
        return self._date_end

    def set_date_end(self, date: any) -> datetime.datetime:
        self._date_end = datetime_normalize(date)
        GLOG.DEBUG(f"{type(self)}:{self.name} set DATEEND {self.date_end}.")
        return self.date_end

    def set_backtest_interval(self, interval: str) -> datetime.timedelta:
        interval = interval.upper()
        if interval == "DAY":
            self._time_interval = datetime.timedelta(days=1)
        elif interval == "MIN":
            self._time_interval = datetime.timedelta(minutes=1)
        GLOG.DEBUG(f"{type(self)}:{self.name} set INTERVAL {self._time_interval}.")
        return self._time_interval

    def main_loop(self, flag) -> None:
        """
        The EventBacktest Main Loop.
        """
        count = 0
        while self._active:
            if flag.is_set():
                break
            try:
                # Get a event from events_queue
                event: EventBase = self._queue.get(block=True, timeout=0.5)
                # Pass the event to handle
                self._process(event)
                count = 0
            except Empty:
                GLOG.WARN(f"No Event in Queue. {datetime.datetime.now()} {count}")
                count += 1
                # Exit
                if count >= self.duration:
                    GLOG.WARN("Should Stop.")
                    self.stop()
                    sys.exit()

            # Break for a while
            # sleep(GCONF.HEARTBEAT)

    def timer_loop(self, flag) -> None:
        """
        Timer Task. Something like crontab or systemd timer
        """
        while self._active:
            if flag.is_set():
                break
            [handle() for handle in self._timer_handles]
            sleep(self._interval)

    def start(self) -> Thread:
        """
        Start the engine
        """
        super(EventEngine, self).start()
        self._main_thread.start()
        self._timer_thread.start()
        GLOG.DEBUG("Engine Start.")
        return self._main_thread

    def stop(self) -> None:
        """
        Pause the Engine
        """
        super(EventEngine, self).stop()
        self._main_flag.set()
        self._timer_flag.set()
        # self._main_thread.join()
        # self._timer_thread.join()
        GLOG.WARN("Engine Stop.")

    def put(self, event: "EventBase") -> None:
        self._queue.put(event)
        GLOG.DEBUG(f"{type(self)}:{self.name} put {event.event_type} in queue.")

    def _process(self, event: "EventBase") -> None:
        print(f"Process {event.event_type}")
        print(event)
        if event.event_type in self._handles:
            [handle(event) for handle in self._handles[event.event_type]]
            GLOG.DEBUG(f"{self.name} Deal with {event.event_type}.")
        else:
            GLOG.WARN(f"There is no handler for {event.event_type}")

        if len(self._general_handles) == 0:
            return

        [handle(event) for handle in self._general_handles]

    def register(self, type: "EVENT_TYPES", handle: callable) -> None:
        if type in self._handles:
            if handle not in self._handles[type]:
                self._handles[type].append(handle)
            else:
                GLOG.WARN(f"handle Exists.")
        else:
            self._handles[type]: list = []
            self._handles[type].append(handle)
            GLOG.INFO(
                f"Register handle {type} : {handle.__name__}"
            )  # handler.__func__ for method object, not support function object.

    def unregister(self, type: "EVENT_TYPES", handle: callable) -> None:
        if type not in self._handles:
            GLOG.WARN(f"Event {type} not exsits. No need to unregister the handle.")
            return

        if handle not in self._handles[type]:
            GLOG.WARN(f"Event {type} do not own the handle.")
            return

        self._handles[type].remove(handle)
        GLOG.INFO(f"Unregister handle {type} : {handle}")

    def register_general(self, handle: callable) -> None:
        if handle not in self._general_handles:
            self._general_handles.append(handle)
            msg = f"RegisterGeneral : {handle}"
            GLOG.INFO(msg)
        else:
            msg = f"{handle} already exist."
            GLOG.WARN(msg)

    def unregister_general(self, handle: callable) -> None:
        if handle in self._general_handles:
            self._general_handles.remove(handle)
            msg = f"UnregisterGeneral : {handle}"
            GLOG.INFO(msg)
        else:
            msg = f"{handle} not exsit in Generalhandle"
            GLOG.WARN(msg)

    def register_timer(self, handle: callable) -> None:
        if handle not in self._timer_handles:
            self._timer_handles.append(handle)
            GLOG.INFO(f"Register Timer handle: {handle}")
        else:
            GLOG.DEBUG(f"Timer handle Exsits.")

    def unregister_timer(self, handle: callable) -> None:
        if handle in self._timer_handles:
            self._timer_handles.remove(handle)
            GLOG.INFO(f"Unregister Timer handle: {handle}")
        else:
            msg = f"Timerhandle {handle} not exists."
            GLOG.WARN(msg)

    @property
    def handle_count(self) -> int:
        count = 0
        for i in self._handles:
            count += len(self._handles[i])
        return count

    @property
    def general_count(self) -> int:
        return len(self._general_handles)

    @property
    def timer_count(self) -> int:
        return len(self._timer_handles)

    @property
    def todo_count(self) -> int:
        return self._queue.qsize()

    def nextphase(self, *args, **kwargs) -> None:
        if self.now >= self.date_end:
            self.stop()
            return
        self._now = self.now + self._time_interval

        if self.matchmaking is None:
            GLOG.ERROR(f"There is no matchmaking binded.")
        else:
            self.matchmaking.on_time_goes_by(self.now)

        if self.datafeeder is None:
            GLOG.ERROR(f"There is no datafeeder.")
        else:
            self.datafeeder.on_time_goes_by(self.now)

        if len(self.portfolios) == 0:
            GLOG.ERROR(f"There is no portfolio binded.")
        else:
            GLOG.INFO(f"Engine:{self.name} Go NextDay {self.now}.")
            for i in self.portfolios:
                i.value.on_time_goes_by(self.now)
