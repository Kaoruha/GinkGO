import pandas as pd


class BaseIndex(object):
    def __init__(self, name: str = "", *args, **kwargs) -> None:
        self._name = name
        pass

    @property
    def name(self) -> str:
        return self._name

    def cal(self, *args, **kwargs) -> None:
        raise NotImplementedError("Cal Func should be overwrite.")
