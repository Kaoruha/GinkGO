from ginkgo.libs import GLOG
from ginkgo.backtest.backtest_base import BacktestBase


class HandlerBase(BacktestBase):
    def __init__(self, *args, **kwargs):
        super(HandlerBase, self).__init__(*args, **kwargs)
        self.set_name("Handler")

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            GLOG.ERROR(f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)
