import datetime
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import datetime_normalize, GinkgoSingleLinkedList


class BacktestBase(object):
    def __init__(self, name: str = "backtest_base", *args, **kwargs) -> None:
        self._name: str = ""
        self.set_name(name)
        self._now: datetime.datetime = None

    @property
    def name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        self._name = name

    @property
    def now(self) -> datetime.datetime:
        return self._now

    def on_time_goes_by(self, time: any, *args, **kwargs):
        # Should support Day or Min or other frame gap
        time = datetime_normalize(time)
        if time is None:
            GLOG.WARN("Format not support, can not update time")
            return
        if self._now is None:
            self._now = time
            GLOG.DEBUG(f"{self.name} Time Init: None --> {self._now}")
        else:
            if time < self.now:
                GLOG.ERROR("We can not go back such as a TIME TRAVALER.")
                return
            elif time == self.now:
                GLOG.WARN("The time not goes on.")
                return
            else:
                # Go next frame
                old = self._now
                self._now = time
                # GLOG.INFO(f"{self.name} Time Elapses: {old} --> {self._now}")

    def __repr__(self) -> str:
        return self.name
