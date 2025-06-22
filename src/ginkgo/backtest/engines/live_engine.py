from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
    from ginkgo.backtest.matchmakings import MatchMakingBase
    from ginkgo.backtest.events.base_event import EventBase
    from ginkgo.backtest.feeders.base_feed import BaseFeed
    from ginkgo.enums import EVENT_TYPES

import datetime
import sys
import os
from time import sleep
from queue import Queue, Empty
from threading import Thread, Event


from ginkgo.backtest.engines.event_engine import EventEngine
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize, GinkgoLogger
from ginkgo.notifier.notifier_beep import beep
from ginkgo.data.drivers import GinkgoConsumer, GinkgoProducer
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.backtest.position import Position
from ginkgo.data.operations import delete_engine, add_engine, update_engine_status


live_logger = GinkgoLogger("live")


class LiveEngine(EventEngine):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False
    # TODO
    # REbuild with kafka

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
        self._control_thread: Thread = Thread(target=self.run_control_listener, args=(self._control_flag,))
        live_logger.reset_logfile(f"live_{backtest_id}.log")
        self.register_timer(self.update_time)
        self.register_timer(self.get_price)

    def update_time(self) -> None:
        self._now = datetime.datetime.now()

    def get_price(self) -> None:
        # TODO Get Codes all portfolio care.
        codes = []
        node = self.portfolios.head
        while node is not None:
            portfolio = node.value
            code_node = portfolio.interested.head
            while code_node is not None:
                codes.append(code_node.value.code)
                code_node = code_node.next
            node = node.next
        # Try get Price info from DataEngine
        for i in codes:
            # TODO Get data from DataEngine
            # TODO Create PriceUpdate Event
            # TODO Push into queue
            pass
        pass

    @property
    def now(self) -> datetime.datetime:
        return datetime.datetime.now()

    @property
    def engine_id(self) -> str:
        return self.backtest_id

    def reset_positions(self):
        """
        Iterate over the portfolios, query orders from db, generate holding positions.
        """
        if len(self.portfolios) == 0:
            live_logger.DEBUG("There is no portfolio bind to live. Can not update positions")
            return
        node = self.portfolios.head
        while node is not None:
            p = node.value
            # Get Positions via portfolio id and backtest_id
            p.reset_positions()
            node = node.next

    def get_portfolio(self, portfolio_id: str):
        """
        Try get portfolio via id.
        """
        node = self.portfolios.head
        while node is not None:
            p = node.value
            if p.uuid == portfolio_id:
                return p
            node = node.next
        return None

    def buy(self, portfolio_id, code, price, volume) -> None:
        """
        Add Long record for portfolio.
        """
        p = self.get_portfolio(portfolio_id)
        if p is None:
            live_logger.warning(f"{portfolio_id} not exist.")
            return
        pos = Position(code, price, volume)
        p.add_position(pos)
        # Update position
        # TODO add record

    def sell(self, portfolio_id, code, price, volume) -> None:
        """
        Add Short record for portfolio.
        """
        p = self.get_portfolio(portfolio_id)
        if p is None:
            return
        if code not in p.positions.keys():
            return
        p.positions[code].deal(DIRECTION_TYPES.SHORT, price, volume)
        # Update position
        # TODO add record
        pass

    def cal_signals(self) -> None:
        """
        Calculate signals.
        """
        live_logger.INFO("Try gen signals.")
        node = self.portfolios.head
        while node is not None:
            portfolio = node.value
            portfolio.cal_signals()
        # TODO

    def cal_suggestions(self) -> None:
        self.cal_signals()

    def run_control_listener(self, flag) -> None:
        pid = os.getpid()
        error_time = 0
        max_try = 5
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
                live_logger.INFO(f"{self.engine_id} Start Listen Kafka Topic: {topic_name}  PID:{pid}")
                for msg in con.consumer:
                    error_time = 0
                    value = msg.value
                    self.process_control_command(value)
            except Exception as e2:
                live_logger.ERROR(f"Something wrong happend when dealing with Kafka Topic: {topic_name}, {e2}")
                error_time += 1
                if error_time > max_try:
                    sys.exit(0)
                else:
                    sleep(min(5 * (2**error_time), 300))
        delete_engine(self.backtest_id)

    def process_control_command(self, command: dict) -> None:
        if command["engine_id"] != self.engine_id:
            live_logger.INFO(f"{command['engine_id']} is not my type {self.engine_id}")
            return
        if command["command"].upper() == "PAUSE":
            self.pause()
        elif command["command"].upper() == "RESUME":
            self.resume()
        elif command["command"].upper() == "START":
            self._active = True
            live_logger.INFO("Engine START.")
            update_engine_status(self.engine_id, "running")
        elif command["command"].upper() == "RESTART":
            self.restart()
        elif command["command"].upper() == "CAL_SIGNAL":
            live_logger.INFO("Calculating signals.")
        else:
            live_logger.ERROR(f"Command not support, {command}")

    def start(self) -> Thread:
        super(LiveEngine, self).start()
        pid = os.getpid()
        add_engine(self.engine_id, True)
        self._control_thread.start()
        update_engine_status(self.engine_id, "running")
        return self._control_thread

    def pause(self) -> None:
        live_logger.INFO("Engine PAUSE.")
        self._active = False
        update_engine_status(self.engine_id, "pause")

    def resume(self) -> None:
        self._active = True
        live_logger.INFO("Engine RESUME.")
        update_engine_status(self.engine_id, "running")

    def stop(self) -> None:
        super(LiveEngine, self).stop()
        self._control_flag.set()
        update_engine_status(self.engine_id, "stop")

    def restart(self) -> None:
        live_logger.INFO("Engine RESTART.")
        self._active = True
        self._main_flag.set()
        self._timer_flag.set()
        update_engine_status(self.engine_id, "restart")
        for i in range(self._interval + 5):
            live_logger.INFO(f"Restart in {self._interval+5-i}s")
            sleep(1)
        self._main_flag = Event()
        self._main_thread: Thread = Thread(target=self.main_loop, args=(self._main_flag,))
        self._timer_flag = Event()
        self._timer_thread: Thread = Thread(target=self.timer_loop, args=(self._timer_flag,))
        self._main_thread.start()
        self._timer_thread.start()
        update_engine_status(self.engine_id, "running")
