from ginkgo.backtest.selectors.base_selector import BaseSelector


class FixedSelector(BaseSelector):
    def __init__(self, code: str, *args, **kwargs):
        super(FixedSelector, self).__init__(*args, **kwargs)
        self._interested = code

    def pick(self):
        r = [
            self._interested,
        ]
        return r
