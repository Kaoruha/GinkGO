import pandas as pd
from types import FunctionType, MethodType
from ginkgo.enums import SOURCE_TYPES
from enum import Enum


class Base(object):
    def __init__(self, *args, **kwargs):
        self._source = SOURCE_TYPES.VOID

    def set_source(self, source: SOURCE_TYPES):
        self._source = source

    @property
    def source(self):
        return self._source

    @property
    def to_dataframe(self) -> pd.DataFrame:
        item = {}
        methods = ["delete", "query", "registry", "metadata", "to_dataframe"]
        for param in self.__dir__():
            if param in methods:
                continue
            if param.startswith("_"):
                continue
            if isinstance(self.__getattribute__(param), MethodType):
                continue
            if isinstance(self.__getattribute__(param), FunctionType):
                continue

            if isinstance(self.__getattribute__(param), Enum):
                item[param] = self.__getattribute__(param).value
            elif isinstance(self.__getattribute__(param), str):
                item[param] = self.__getattribute__(param).strip(b"\x00".decode())
            else:
                item[param] = self.__getattribute__(param)

        df = pd.DataFrame.from_dict(item, orient="index")
        return df[0]
