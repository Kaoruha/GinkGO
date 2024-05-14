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


from ginkgo.backtest.engines.event_engine import EventEngine
from ginkgo.backtest.events import EventNextPhase
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize
from ginkgo.libs import GinkgoSingleLinkedList


class HistoricEngine(EventEngine):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self, name: str = "HistoricEngine", interval: int = 1, *args, **kwargs
    ) -> None:
        super(HistoricEngine, self).__init__(name, interval, *args, **kwargs)
        self._backtest_interval = datetime.timedelta(days=1)
        self._date_start = None
        self._date_end = None
        self.set_date_start(20000101)
        self._max_waits = 4
        self._matchmaking = None

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
        else:
            GLOG.DEBUG(
                f"{type(self)}:{self.name} already have MATCHMAKING {matchmaking.name}."
            )
        return self.matchmaking

    @property
    def max_waits(self) -> int:
        return self._max_waits

    def set_max_waits(self, max_waits: int) -> int:
        self._max_waits = max_waits
        GLOG.DEBUG(f"{type(self)}:{self.name} set max_waits {max_waits}.")
        return self._max_waits

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
            self._backtest_interval = datetime.timedelta(days=1)
        elif interval == "MIN":
            self._backtest_interval = datetime.timedelta(minutes=1)
        GLOG.DEBUG(f"{type(self)}:{self.name} set INTERVAL {self._backtest_interval}.")
        return self._backtest_interval

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
                event: EventBase = self._queue.get(block=True, timeout=0.05)
                # Pass the event to handle
                self._process(event)
                count = 0
            except Empty:
                count += 1
                GLOG.WARN(f"No Event in Queue. {datetime.datetime.now()} {count}")
                # Exit
                if count >= self._max_waits:
                    now = datetime.datetime.now()
                    if self.now > now:
                        GLOG.WARN("Should Stop.")
                        self.stop()
                        sys.exit()
                    else:
                        self.put(EventNextPhase())

            # Break for a while
            # sleep(0.005)

    def nextphase(self, *args, **kwargs) -> None:
        if self.now >= self.date_end:
            self.stop()
            return
        self._now = self.now + self._backtest_interval

        if self.matchmaking is None:
            GLOG.DEBUG(f"There is no matchmaking binded.")
        else:
            self.matchmaking.on_time_goes_by(self.now)

        if self.datafeeder is None:
            GLOG.DEBUG(f"There is no datafeeder.")
        else:
            self.datafeeder.on_time_goes_by(self.now)

        if len(self.portfolios) == 0:
            GLOG.DEBUG(f"There is no portfolio binded.")
        else:
            GLOG.INFO(f"Engine:{self.name} Go NextDay {self.now}.")
            for i in self.portfolios:
                i.value.on_time_goes_by(self.now)
