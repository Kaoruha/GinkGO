import pandas as pd

from types import FunctionType, MethodType
from enum import Enum

from ...enums import SOURCE_TYPES


class Base(object):
    """
    Origin Base Class
    """

    def __init__(self, uuid: str = "", *args, **kwargs):
        self._source = SOURCE_TYPES.VOID
        self._uuid = uuid

    @property
    def uuid(self, *args, **kwargs) -> str:
        return self._uuid

    @uuid.setter
    def uuid(self, uuid: str, *args, **kwargs) -> str:
        if not isinstance(uuid, str):
            raise ValueError("UUID must be a string.")
        self._uuid = uuid
        return self._uuid

    def set_uuid(self, uuid: str, *args, **kwargs) -> str:
        if not isinstance(uuid, str):
            raise ValueError("UUID must be a string.")
        self._uuid = uuid
        return self._uuid

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        if not isinstance(value, SOURCE_TYPES):
            raise ValueError("Source must be a valid SOURCE_TYPES enum.")
        self._source = value

    def set_source(self, source: SOURCE_TYPES):
        self._source = source

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert Object's parameters to DataFrame.
        Args:
            None
        Returns:
            A dataframe convert from this.
        """
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

        df = pd.DataFrame.from_dict(item, orient="index").transpose()
        return df
