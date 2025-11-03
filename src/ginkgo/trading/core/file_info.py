import datetime
import pandas as pd
from types import FunctionType, MethodType
from functools import singledispatchmethod
from typing import Optional

from ginkgo.trading.core.base import Base
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES


class FileInfo(Base):
    """
    File Information Container. Store file metadata including name, type, data and other info.
    Business entity for file operations, separate from database model (MFile).
    """

    def __init__(
        self,
        name: str = "default_file",
        type: FILE_TYPES = FILE_TYPES.OTHER,
        data: bytes = b"",
        desc: str = "This man is lazy, there is no description.",
        meta: str = "{}",
        create_at: any = None,
        update_at: any = None,
        *args,
        **kwargs
    ) -> None:
        super(FileInfo, self).__init__(*args, **kwargs)
        self.set(name, type, data, desc, meta, create_at, update_at)

    @singledispatchmethod
    def set(self) -> None:
        """
        Set file properties. Supports multiple input types:
        1. name, type, data, desc, meta, create_at, update_at (parameters)
        2. pandas Series (from database query result)
        """
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        name: str,
        type: FILE_TYPES,
        data: bytes,
        desc: str = "This man is lazy, there is no description.",
        meta: str = "{}",
        create_at: any = None,
        update_at: any = None,
        *args,
        **kwargs
    ) -> None:
        """
        Set file data from parameters.

        Args:
            name(str): File name
            type(FILE_TYPES): File type (STRATEGY, SELECTOR, etc.)
            data(bytes): File content as bytes
            desc(str): File description
            meta(str): Metadata as JSON string
            create_at(any): Creation timestamp
            update_at(any): Last update timestamp
        Returns:
            None
        """
        self._name = name
        self._type = type
        self._data = data
        self._desc = desc
        self._meta = meta
        if create_at:
            self._create_at = datetime_normalize(create_at)
        else:
            from ginkgo.trading.time.clock import now as clock_now
            self._create_at = clock_now()
        if update_at:
            self._update_at = datetime_normalize(update_at)
        else:
            from ginkgo.trading.time.clock import now as clock_now
            self._update_at = clock_now()

    @set.register
    def _(self, df: pd.Series) -> None:
        """
        Set file data from pandas Series (typically from database query result).

        Args:
            df(pd.Series): pandas Series containing file data with columns:
                          uuid, name, type, data, desc, meta, create_at, update_at, is_del, source
        Returns:
            None
        """
        self._name = df["name"]
        self._type = df["type"]
        self._data = df["data"]
        self._desc = df.get("desc", "This man is lazy, there is no description.")
        self._meta = df.get("meta", "{}")
        from ginkgo.trading.time.clock import now as clock_now
        self._create_at = datetime_normalize(df.get("create_at", clock_now()))
        self._update_at = datetime_normalize(df.get("update_at", clock_now()))
        
        # Set inherited properties from Base
        if "uuid" in df:
            self._uuid = df["uuid"]
        if "source" in df:
            self._source = df["source"]

    @property
    def name(self) -> str:
        """
        The name of the file.
        """
        return self._name

    @property
    def type(self) -> FILE_TYPES:
        """
        The type of the file (STRATEGY, SELECTOR, SIZER, etc.).
        """
        return self._type

    @property
    def data(self) -> bytes:
        """
        The file content as bytes.
        """
        return self._data

    @property
    def desc(self) -> str:
        """
        File description.
        """
        return self._desc

    @property
    def meta(self) -> str:
        """
        Metadata as JSON string.
        """
        return self._meta

    @property
    def create_at(self) -> datetime.datetime:
        """
        Creation timestamp.
        """
        return self._create_at

    @property
    def update_at(self) -> datetime.datetime:
        """
        Last update timestamp.
        """
        return self._update_at

    @property
    def content(self) -> str:
        """
        Get file content as decoded string.
        
        Returns:
            str: File content decoded as UTF-8 string
        """
        try:
            return self._data.decode('utf-8')
        except UnicodeDecodeError:
            return self._data.decode('utf-8', errors='replace')

    @property
    def size(self) -> int:
        """
        Get file size in bytes.
        
        Returns:
            int: File size in bytes
        """
        return len(self._data)

    def is_text_file(self) -> bool:
        """
        Check if the file contains text content.
        
        Returns:
            bool: True if file appears to be text-based
        """
        try:
            self._data.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False

    def __repr__(self) -> str:
        return base_repr(self, FileInfo.__name__, 12, 60)
