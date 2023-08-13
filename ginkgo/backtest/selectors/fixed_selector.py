from ginkgo.backtest.selectors.base_selector import BaseSelector


class FixedSelector(BaseSelector):
    def __init__(self, codes: list, *args, **kwargs):
        super(FixedSelector, self).__init__(*args, **kwargs)
        if not isinstance(codes, list):
            raise Exception("Codes must be list. Example: [code1,code2]")
        self._interested = codes

    def pick(self):
        r = self._interested
        return r
