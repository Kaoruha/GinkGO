from ginkgo.backtest.backtest_base import BacktestBase
from ginkgo.libs import base_repr


class BaseEngine(BacktestBase):
    """
    Basic Backtest Engine.
    """

    def __init__(self, name: str = "BaseEngine", *args, **kwargs):
        super(BaseEngine, self).__init__(name, *args, **kwargs)
        self._active: bool = False

    @property
    def status(self) -> str:
        if self._active:
            return "Active"
        else:
            return "Paused"

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        self._active = True
        self.log("INFO", f"Engine {self.name} {self.engine_id} started.")

    def pause(self) -> None:
        self._active = False
        self.log("INFO", f"Engine {self.name} {self.engine_id} paused.")

    def stop(self) -> None:
        self._active = False
        self.log("INFO", f"Engine {self.name} {self.engine_id} stop.")

    def __repr__(self) -> str:
        return base_repr(self, self._name, 16, 60)
