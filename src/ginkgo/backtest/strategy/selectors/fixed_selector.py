import json
from ginkgo.backtest.strategy.selectors.base_selector import BaseSelector


class FixedSelector(BaseSelector):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, codes: str, *args, **kwargs) -> None:
        super(FixedSelector, self).__init__(name, *args, **kwargs)

        self._interested = []
        try:
            self._interested = json.loads(codes)
        except Exception as e:
            print(e)
        finally:
            pass

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        r = self._interested
        self.log("DEBUG", f"Selector:{self.name} pick {r}.")
        return r
