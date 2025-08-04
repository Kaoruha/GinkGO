from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.backtest.execution.engines.base_engine import BaseEngine
import datetime
import uuid
from rich.console import Console

from ...libs import GLOG, base_repr, datetime_normalize
from .base import Base


console = Console()


class BacktestBase(Base):
    """
    Basic Class of Backtest.
    """

    def __init__(self, name: str = "backtest_base", uuid_str: str = "", *args, **kwargs) -> None:
        # Initialize the parent Base class first
        # If no UUID is provided, generate one automatically
        if not uuid_str:
            uuid_str = uuid.uuid4().hex
        super().__init__(uuid=uuid_str, *args, **kwargs)
        
        self._now: datetime.datetime = None
        self._engine_id: str = uuid.uuid4().hex
        self._engine_put = None
        self.set_name(str(name))
        self.loggers = []
        self.add_logger(GLOG)


    @property
    def engine_id(self) -> str:
        """
        As same as backtest id. But more property at live time.
        """
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def backtest_id(self) -> str:
        """
        ID for Backtest.
        """
        return self._engine_id

    @backtest_id.setter
    def backtest_id(self, value: str) -> None:
        self._engine_id = value

    def bind_engine(self, engine: "BaseEngine") -> None:
        """
        Bind the backtest instance to an engine.

        Args:
            engine (BaseEngine): The engine to bind to.

        Raises:
            ValueError: If the engine is invalid or missing required attributes.
        """
        if not hasattr(engine, "engine_id") or not hasattr(engine, "put"):
            raise ValueError("Invalid engine: missing required attributes engine_id and put.")
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
        Update the instance name.

        Args:
            name (str): New name for the instance.

        Returns:
            str: The updated name.
        """
        self._name = name
        return self.name

    @property
    def now(self) -> datetime.datetime:
        return self._now

    def add_logger(self, logger) -> None:
        if logger in self.loggers:
            return
        self.loggers.append(logger)

    def reset_logger(self) -> None:
        self.loggers = []

    def log(self, level: str, msg: str, *args, **kwargs) -> None:
        level_up = level.upper()
        if level_up == "DEBUG":
            for i in self.loggers:
                i.DEBUG(msg)
        elif level_up == "INFO":
            for i in self.loggers:
                i.INFO(msg)
        elif level_up == "WARNING":
            for i in self.loggers:
                i.WARN(msg)
        elif level_up == "ERROR":
            for i in self.loggers:
                i.ERROR(msg)
        elif level_up == "CRITICAL":
            for i in self.loggers:
                i.CRITICAL(msg)
        else:
            pass

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
            self.log("ERROR", "Time format not support, can not update time")
            return

        if self._now is None:
            self._now = time
            self.log("DEBUG", f"{self.name} Time Init: None --> {self._now}")
            return

        if time < self.now:
            self.log("ERROR", "We can not go back such as a TIME TRAVALER.")
            return

        elif time == self.now:
            self.log("WARNING", "Time not goes on.")
            return

        else:
            # time > self.now
            # Go next frame
            old = self._now
            self._now = time
            self.log("DEBUG", f"{type(self)} {self.name} Time Elapses: {old} --> {self.now}")
            console.print(f":swimmer: {self.name} Time Elapses: {old} --> {self.now}")

    def __repr__(self) -> str:
        return base_repr(self, self._name, 12, 60)
