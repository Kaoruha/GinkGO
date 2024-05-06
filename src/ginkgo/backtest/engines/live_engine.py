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
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize
from ginkgo.libs import GinkgoSingleLinkedList


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
        **kwargs
    ) -> None:
        super(LiveEngine, self).__init__(name, interval, *args, **kwargs)
        self.set_backtest_id(backtest_id)

    @property
    def now(self) -> datetime.datetime:
        return datetime.datetime.now()

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
            node = noed.next
        return None

    def buy(self, portfolio_id, code, price, volume) -> None:
        p = self.get_portfolio(portfolio_id)
        if p is None:
            return
        pos = Position(code, price, volume)
        self.add_position(pos)
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
            self.datafeeder.broadcast()

        # TODO
        pass
