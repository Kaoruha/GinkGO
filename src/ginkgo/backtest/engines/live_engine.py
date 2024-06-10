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
        interval: int = 1,
        *args,
        **kwargs,
    ) -> None:
        super(LiveEngine, self).__init__(name, interval, *args, **kwargs)
        self.set_backtest_id(backtest_id)
        self._control_thread: Thread = Thread(target=self.run_control_listener)

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

    def run_control_listener(self) -> None:
        pid = os.getpid()
        error_time = 0
        max_try = 5
        GLOG.reset_logfile("live_control.log")
        while True:
            try:
                topic_name = f"live_control"
                con = GinkgoConsumer(topic_name, "ginkgo_live_engine_group")
                print(f"Start Listen Kafka Topic: {topic_name}  PID:{pid}")
                for msg in con.consumer:
                    beep(freq=2190.7, repeat=2, delay=200, length=500)
                    error_time = 0
                    # Handle msg
                    value = msg.value
                    self.process_control_command(con, value)
            except Exception as e2:
                print(e2)
                error_time += 1
                if error_time > max_try:
                    sys.exit(0)
                else:
                    sleep(min(5 * (2**error_time), 300))
        GinkgoThreadManager().remove_liveengine(self.backtest_id)

    def process_control_command(self, con, command: dict) -> None:
        if command["command"] == "pause":
            print("pause")
        elif command["command"] == "start":
            print("start")
        elif command["command"] == "stop":
            try:
                print("stop")
                GinkgoThreadManager().remove_liveengine(self.backtest_id)
                con.commit()
                sleep(5)
            except Exception as e:
                pass
            finally:
                con.close()
                sys.exit(0)
        else:
            print("cant handle")
            print(command)

    def start(self) -> Thread:
        # super(LiveEngine, self).start()
        pid = os.getpid()
        GinkgoThreadManager().add_liveengine(self.engine_id, int(pid))
        self._control_thread.start()
        return self._control_thread
