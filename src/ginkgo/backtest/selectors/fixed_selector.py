from ginkgo.backtest.selectors.base_selector import BaseSelector


class FixedSelector(BaseSelector):
    abstract = False

    def __init__(
        self, codes: list, name: str = "FixedSelector", *args, **kwargs
    ) -> None:
        super(FixedSelector, self).__init__(name, *args, **kwargs)
        if not isinstance(codes, list):
            print(codes)
            raise Exception("Codes must be list. Example: [code1,code2]")
        self._interested = codes

    def pick(self) -> list:
        r = self._interested
        return r
