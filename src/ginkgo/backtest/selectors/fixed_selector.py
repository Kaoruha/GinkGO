from ginkgo.backtest.selectors.base_selector import BaseSelector


class FixedSelector(BaseSelector):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, codes: list, *args, **kwargs) -> None:
        super(FixedSelector, self).__init__(name, *args, **kwargs)
        if not isinstance(codes, list):
            print(codes)
            raise Exception("Codes must be list. Example: [code1,code2]")
        self._interested = codes

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        r = self._interested
        print("++++++++++++++++++++")
        print(r)
        return r
