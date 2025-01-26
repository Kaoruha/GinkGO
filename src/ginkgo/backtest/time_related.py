import datetime
from ginkgo.libs import GLOG, datetime_normalize


class TimeRelated:
    def __init__(self, *args, **kwargs) -> None:
        self._now: datetime.datetime = None

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
        has_log = hasattr(self, "log") and callable(self.log)
        # Should support Day or Min or other frame gap
        time = datetime_normalize(time)

        if time is None:
            self.log("ERROR", "Time format not support, can not update time")
            return

        if self._now is None:
            self._now = time
            if has_log:
                self.log("DEBUG", f"{self.name} Time Init: None --> {self._now}")
            return

        if time < self.now:
            if has_log:
                self.log("ERROR", "We can not go back such as a TIME TRAVALER.")
            return

        elif time == self.now:
            if has_log:
                self.log("WARNING", "Time not goes on.")
            return

        else:
            # time > self.now
            # Go next frame
            old = self._now
            self._now = time
            if has_log:
                self.log("DEBUG", f"{type(self)} {self.name} Time Elapses: {old} --> {self.now}")
            console.print(f":swimmer: {self.name} Time Elapses: {old} --> {self.now}")
