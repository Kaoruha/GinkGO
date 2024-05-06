import datetime
import uuid
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import datetime_normalize, GinkgoSingleLinkedList
from rich.console import Console


console = Console()


class BacktestBase(object):
    """
    Basic Class of Backtest.
    """

    def __init__(self, name: str = "backtest_base", *args, **kwargs) -> None:
        self._name: str = ""
        self._now: datetime.datetime = None
        self._abstract = True
        self._backtest_id = uuid.uuid4().hex

        self.set_name(name)

    @property
    def backtest_id(self) -> str:
        return self._backtest_id

    def set_backtest_id(self, value: str) -> str:
        """
        Backtest ID update.

        Args:
            value(str): new backtest id
        Returns:
            current backtest id
        """
        self._backtest_id = value
        return self.backtest_id

    @property
    def name(self) -> str:
        return self._name

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
            GLOG.WARN("The time not goes on.")
            return

        else:
            # time > self.now
            # Go next frame
            old = self._now
            self._now = time
            GLOG.DEBUG(f"{type(self)} {self.name} Time Elapses: {old} --> {self.now}")
            console.print(f":swimmer: {self.name} Time Elapses: {old} --> {self.now}")

    def __repr__(self) -> str:
        return self.name
