from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.backtest.engines.base_engine import BaseEngine
import datetime
import uuid
from rich.console import Console

from ginkgo.libs import GLOG, base_repr
from ginkgo.libs import datetime_normalize, GinkgoSingleLinkedList


console = Console()


class BacktestBase(object):
    """
    Basic Class of Backtest.
    """

    def __init__(self, name: str = "backtest_base", *args, **kwargs) -> None:
        self._now: datetime.datetime = None
        self._engine_id: str = uuid.uuid4().hex
        self.set_name(str(name))

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value: str) -> None:
        self._engine_id = value

    def bind_engine(self, engine: "BaseEngine") -> None:
        self._engine_id = engine.engine_id
        # Do not hold engine any more. just got the put function
        self._engine_put = engine.put

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    def set_name(self, name: str) -> str:
        """
        Name update.

        Args:
            name(str): new name
        Returns:
            current name
        """
        self._name = name
        return self.name

    @property
    def now(self) -> datetime.datetime:
        return self._now

    def on_time_goes_by(self, time: any, *args, **kwargs) -> None:
        """
        Go next frame.
        Timestamp update. Just support from past to future.

        Args:
            time(any): new time
        Returns:
            None
        """
        # Should support Day or Min or other frame gap
        time = datetime_normalize(time)

        if time is None:
            GLOG.ERROR("Format not support, can not update time")
            return

        if self._now is None:
            self._now = time
            GLOG.DEBUG(f"{self.name} Time Init: None --> {self._now}")
            return

        if time < self.now:
            GLOG.ERROR("We can not go back such as a TIME TRAVALER.")
            return

        elif time == self.now:
            GLOG.WARN("Time not goes on.")
            return

        else:
            # time > self.now
            # Go next frame
            old = self._now
            self._now = time
            GLOG.DEBUG(f"{type(self)} {self.name} Time Elapses: {old} --> {self.now}")
            console.print(f":swimmer: {self.name} Time Elapses: {old} --> {self.now}")

    def __repr__(self) -> str:
        return base_repr(self, self._name, 12, 60)
