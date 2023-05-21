import datetime
from ginkgo.libs import datetime_normalize
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.event import EventPriceUpdate
from ginkgo.libs import GINKGOLOGGER as gl


class MatchMaking_Sim(object):
    def __init__(self):
        self._current = None
        pass

    @property
    def current_time(self) -> datetime.datetime:
        return self._current

    def price_update(self, event: EventPriceUpdate):
        # TODO Check the source
        if self._current is None:
            self._current = event.timestamp
            gl.logger.debug(f"Sim MatchMaking start. {self.current_time}")

        # Update Current Time
        if event.timestamp < self._current:
            gl.logger.warn(
                f"Current Time is {self.current_time} the price come from past {event.timestamp}"
            )
            return
