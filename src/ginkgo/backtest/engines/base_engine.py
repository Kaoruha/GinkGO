import uuid

from ginkgo.backtest.backtest_base import BacktestBase


class BaseEngine(BacktestBase):
    """
    Basic Backtest Engine.
    """

    def __init__(self, name: str = "BaseEngine", *args, **kwargs):
        super(BaseEngine, self).__init__(name, *args, **kwargs)
        self._active: bool = False
        self._backtest_id: str = uuid.uuid4().hex

    @property
    def backtest_id(self) -> str:
        return self._backtest_id

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def name(self) -> str:
        return self._name

    def start(self) -> None:
        self._active = True

    def pause(self) -> None:
        self._active = False

    def stop(self) -> None:
        self._active = False

    def __repr__(self) -> str:
        return self.name
