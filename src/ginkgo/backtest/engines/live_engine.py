from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
    from ginkgo.backtest.matchmakings import MatchMakingBase
    from ginkgo.backtest.events.base_event import EventBase
    from ginkgo.backtest.feeds.base_feed import BaseFeed
    from ginkgo.enums import EVENT_TYPES

import datetime
import sys
import os
from time import sleep
from queue import Queue, Empty
from threading import Thread, Event


from ginkgo.backtest.engines.event_engine import EventEngine
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize
from ginkgo.libs import GinkgoSingleLinkedList
from ginkgo.notifier.notifier_beep import beep
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.drivers import GinkgoConsumer, GinkgoProducer
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.backtest.position import Position


class LiveEngine(EventEngine):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        backtest_id: str,
        name: str = "LiveEngine",
        interval: int = 5,
        *args,
        **kwargs,
    ) -> None:
        super(LiveEngine, self).__init__(name, interval, *args, **kwargs)
        self.set_backtest_id(backtest_id)
        self._control_flag = Event()
        self._control_thread: Thread = Thread(
            target=self.run_control_listener, args=(self._control_flag,)
        )

    @property
    def now(self) -> datetime.datetime:
        return datetime.datetime.now()

    @property
    def engine_id(self) -> str:
        return self.backtest_id

    def recover_positions(self):
        if len(self.portfolios) == 0:
            GLOG.DEBUG("There is no portfolio bind to live. Can not update positions")
            return
        node = self.portfolios.head
        while node is not None:
            p = node.value
            # Get Positions via portfolio id and backtest_id
            p.recover_positions()
            node = node.next

    def get_portfolio(self, portfolio_id: str):
        node = self.portfolios.head
        while node is not None:
            p = node.value
            if p.uuid == portfolio_id:
                return p
            node = node.next
        return None

    def buy(self, portfolio_id, code, price, volume) -> None:
        p = self.get_portfolio(portfolio_id)
        if p is None:
            return
        pos = Position(code, price, volume)
        p.add_position(pos)
        # Update position
        # TODO add record
        pass

    def sell(self, portfolio_id, code, price, volume) -> None:
        p = self.get_portfolio(portfolio_id)
        if p is None:
            return
        if code not in p.positions.keys():
            return
        p.positions[code].deal(DIRECTION_TYPES.SHORT, price, volume)
        # Update position
        # TODO add record
        pass

    def cal_signal_manually(self) -> None:
        node = self.portfolios.head
        while node is not None:
            portfolio = node.value
            portfolio.cal_signal_manually()

        # TODO
        pass

    def run_control_listener(self, flag) -> None:
        pid = os.getpid()
        error_time = 0
        max_try = 5
        GLOG.reset_logfile("live_control.log")
        while True:
            if flag.is_set():
                break
            try:
                topic_name = f"live_control"
                con = GinkgoConsumer(
                    topic=topic_name,
                    # group_id=f"ginkgo_live_engine_{self.engine_id}",
                    offset="latest",
                )
                print(
                    f"{self.engine_id} Start Listen Kafka Topic: {topic_name}  PID:{pid}"
                )
                for msg in con.consumer:
                    error_time = 0
                    value = msg.value
                    self.process_control_command(value)
            except Exception as e2:
                print(e2)
                error_time += 1
                if error_time > max_try:
                    sys.exit(0)
                else:
                    sleep(min(5 * (2**error_time), 300))
        GDATA.remove_liveengine(self.backtest_id)

    def process_control_command(self, command: dict) -> None:
        if command["engine_id"] != self.engine_id:
            print(f"{command['engine_id']} is not my type {self.engine_id}")
            return
        if command["command"].uppder() == "PAUSE":
            self._active = False
            GDATA.set_live_status(self.engine_id, "pause")
        elif command["command"].uppder() == "STOp":
            self._active = False
            GDATA.set_live_status(self.engine_id, "pause")
        elif command["command"].uppder() == "RESUME":
            self._active = True
            print("resume")
            GDATA.set_live_status(self.engine_id, "running")
        elif command["command"].uppder() == "START":
            self._active = True
            print("start")
            GDATA.set_live_status(self.engine_id, "running")
        elif command["command"].uppder() == "RESTART":
            self._active = True
            self.restart()
        elif command["command"].uppder() == "CAL_SIGNAL":
            print("calculating signals.")
        else:
            print("cant handle")
            print(command)

    def start(self) -> Thread:
        super(LiveEngine, self).start()
        pid = os.getpid()
        GDATA.add_liveengine(self.engine_id, int(pid))
        self._control_thread.start()
        GDATA.set_live_status(self.engine_id, "running")
        return self._control_thread

    def stop(self) -> None:
        super(LiveEngine, self).stop()
        self._control_flag.set()
        GDATA.set_live_status(self.engine_id, "stop")

    def restart(self) -> None:
        self._main_flag.set()
        self._timer_flag.set()
        GDATA.set_live_status(self.engine_id, "restart")
        for i in range(self._interval + 5):
            print(f"Restart in {self._interval+5-i}s")
            sleep(1)
        self._main_flag = Event()
        self._main_thread: Thread = Thread(
            target=self.main_loop, args=(self._main_flag,)
        )
        self._timer_flag = Event()
        self._timer_thread: Thread = Thread(
            target=self.timer_loop, args=(self._timer_flag,)
        )
        self._main_thread.start()
        self._timer_thread.start()
        GDATA.set_live_status(self.engine_id, "running")
