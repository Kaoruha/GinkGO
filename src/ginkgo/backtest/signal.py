import pandas as pd
import uuid
import datetime
from functools import singledispatchmethod
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, GLOG
from ginkgo.backtest.base import Base


class Signal(Base):
    """
    Signal Class.
    """

    def __init__(
        self,
        portfolio_id: str = "",
        engine_id: str = "",
        timestamp: any = None,
        code: str = "Default Signal Code",
        direction: DIRECTION_TYPES = None,
        reason: str = "no reason",
        source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
        *args,
        **kwargs,
    ) -> None:
        super(Signal, self).__init__(*args, **kwargs)
        try:
            self.set(portfolio_id, engine_id, timestamp, code, direction, reason, source)
        except Exception as e:
            GLOG.ERROR(f"Error initializing Signal: {e}")
            raise Exception("Error initializing Signal: {e}")

    @singledispatchmethod
    def set(self, *args, **kwargs) -> None:
        """
        Dispatch method for setting attributes.
        """
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        timestamp: any,
        code: str,
        direction: DIRECTION_TYPES,
        reason: str,
        source: SOURCE_TYPES,
        *args,
        **kwargs,
    ):
        if not portfolio_id:
            raise ValueError("portfolio_id cannot be empty.")
        if not engine_id:
            raise ValueError("engine_id cannot be empty.")
        if not timestamp:
            raise ValueError("timestamp cannot be empty.")
        if not code:
            raise ValueError("code cannot be empty.")
        if not direction:
            raise ValueError("direction cannot be empty.")
        if not reason:
            raise ValueError("reason cannot be empty.")
        if not source:
            raise ValueError("source cannot be empty.")
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)
        self._code: str = code
        self._direction: DIRECTION_TYPES = direction
        self._reason = reason
        self.set_source(source)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs):
        """
        Set from dataframe
        """
        required_fields = {"portfolio_id", "timestamp", "code", "direction", "reason"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        self._portfolio_id = df.portfolio_id
        self._engine_id = df["engine_id"]
        self._timestamp: datetime.datetime = datetime_normalize(df.timestamp)
        self._code: str = df.code
        self._direction: DIRECTION_TYPES = DIRECTION_TYPES(df.direction)
        self._reason = df.reason
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    @property
    def code(self) -> str:
        return self._code

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def engine_id(self, *args, **kwargs) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def source(self) -> SOURCE_TYPES:
        return self._source

    def __repr__(self) -> str:
        return base_repr(self, Signal.__name__, 12, 60)
