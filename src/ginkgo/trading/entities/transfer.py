# Upstream: Portfolio Manager (创建资金流转记录)、Backtest Engines (记录出入金)
# Downstream: Base (继承提供uuid/component_type)、TRANSFERDIRECTION_TYPES/TRANSFERSTATUS_TYPES/MARKET_TYPES (枚举)
# Role: Transfer资金流转实体继承Base定义投资组合/引擎/运行/方向/市场/金额/状态/时间/UUID等核心属性






import datetime
import pandas as pd
from functools import singledispatchmethod
from decimal import Decimal

from ginkgo.trading.core.base import Base
from ginkgo.libs import base_repr
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, DIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, TRANSFERDIRECTION_TYPES, COMPONENT_TYPES
from ginkgo.libs import datetime_normalize, Number


class Transfer(Base):
    """
    Holding Position Class.
    """

    def __init__(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str,
        direction: TRANSFERDIRECTION_TYPES,
        market: MARKET_TYPES,
        money: Number,
        status: TRANSFERSTATUS_TYPES,
        timestamp: any,
        uuid: str = "",
        *args,
        **kwargs,
    ):
        # 使用新的Base类初始化，传入组件类型和UUID
        super(Transfer, self).__init__(uuid=uuid, component_type=COMPONENT_TYPES.TRANSFER, *args, **kwargs)

        # 严格参数验证 - 要求所有核心参数必须传入且类型正确
        if not isinstance(portfolio_id, str):
            raise TypeError(f"portfolio_id must be str, got {type(portfolio_id)}")
        if not portfolio_id:
            raise ValueError("portfolio_id cannot be empty.")
        if not isinstance(engine_id, str):
            raise TypeError(f"engine_id must be str, got {type(engine_id)}")
        if not engine_id:
            raise ValueError("engine_id cannot be empty.")
        if not isinstance(run_id, str):
            raise TypeError(f"run_id must be str, got {type(run_id)}")
        if not run_id:
            raise ValueError("run_id cannot be empty.")
        if not isinstance(direction, TRANSFERDIRECTION_TYPES):
            raise TypeError(f"direction must be TRANSFERDIRECTION_TYPES enum, got {type(direction)}")
        if not isinstance(market, MARKET_TYPES):
            raise TypeError(f"market must be MARKET_TYPES enum, got {type(market)}")
        if not isinstance(status, TRANSFERSTATUS_TYPES):
            raise TypeError(f"status must be TRANSFERSTATUS_TYPES enum, got {type(status)}")

        # 金额验证 - 支持Number类型并确保非负
        if not isinstance(money, (int, float, Decimal)):
            raise TypeError(f"money must be Number type (int/float/Decimal), got {type(money)}")
        if money < 0:
            raise ValueError(f"money must be non-negative, got {money}")

        # 时间戳验证和标准化
        normalized_timestamp = datetime_normalize(timestamp)
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {timestamp}")

        # 设置属性
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._direction = direction
        self._market = market
        self._money = money
        self._status = status
        self._timestamp = normalized_timestamp

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str,
        direction: TRANSFERDIRECTION_TYPES,
        market: MARKET_TYPES,
        money: Number,
        status: TRANSFERSTATUS_TYPES,
        timestamp: any,
        *args,
        **kwargs,
    ) -> None:
        # 参数校验
        if not isinstance(portfolio_id, str):
            raise ValueError("portfolio_id must be a string.")
        if not isinstance(engine_id, str):
            raise ValueError("engine_id must be a string.")
        if not isinstance(run_id, str):
            raise ValueError("run_id must be a string.")
        if not isinstance(direction, TRANSFERDIRECTION_TYPES):
            raise ValueError("direction must be a valid TRANSFERDIRECTION_TYPES enum.")
        if not isinstance(market, MARKET_TYPES):
            raise ValueError("market must be a valid MARKET_TYPES enum.")
        if not isinstance(money, Number) or money < 0:
            raise ValueError("money must be a non-negative number.")
        if not isinstance(status, TRANSFERSTATUS_TYPES):
            raise ValueError("status must be a valid TRANSFERSTATUS_TYPES enum.")
        if timestamp is None:
            from ginkgo.trading.time.clock import now as clock_now
            timestamp = clock_now()
        elif not isinstance(timestamp, (str, datetime.datetime)):
            raise ValueError("timestamp must be a string, datetime object, or None.")

        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._direction = direction
        self._market = market
        self._money = money
        self._status = status
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {"portfolio_id", "engine_id", "run_id", "direction", "market", "money", "timestamp"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(df.index):
            missing_fields = required_fields - set(df.index)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        self._portfolio_id = df["portfolio_id"]
        self._engine_id = df["engine_id"]
        self._run_id = df["run_id"]
        self._direction = df["direction"]
        self._market = df["market"]
        self._money = df["money"]
        if "status" in df.index:
            self._status = TRANSFERSTATUS_TYPES(df["status"])
        self._timestamp = datetime_normalize(df["timestamp"])

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        required_fields = {"portfolio_id", "engine_id", "run_id", "direction", "market", "money", "timestamp"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 假设DataFrame只有一行数据，取第一行
        row = df.iloc[0] if len(df) > 0 else df.iloc[0]

        self._portfolio_id = row["portfolio_id"]
        self._engine_id = row["engine_id"]
        self._run_id = row["run_id"]
        self._direction = row["direction"]
        self._market = row["market"]
        self._money = row["money"]
        if "status" in df.columns:
            self._status = TRANSFERSTATUS_TYPES(row["status"])
        self._timestamp = datetime_normalize(row["timestamp"])

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value) -> None:
        self._portfolio_id = value

    @property
    def engine_id(self, *args, **kwargs) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def run_id(self) -> str:
        return self._run_id

    @run_id.setter
    def run_id(self, value) -> None:
        self._run_id = value

    @property
    def direction(self) -> TRANSFERDIRECTION_TYPES:
        return self._direction

    @property
    def market(self) -> MARKET_TYPES:
        return self._market

    @property
    def money(self) -> Decimal:
        return Decimal(str(self._money))

    @property
    def status(self) -> TRANSFERSTATUS_TYPES:
        return self._status

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def __repr__(self) -> str:
        return base_repr(self, Transfer.__name__, 20, 60)

    @classmethod
    def from_model(cls, model):
        """
        从MTransfer模型创建Transfer业务对象

        Args:
            model: MTransfer数据库模型实例

        Returns:
            Transfer: Transfer业务对象实例
        """
        return cls(
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            run_id=model.run_id,
            direction=model.direction,  # 此时已经是枚举对象
            market=model.market,       # 此时已经是枚举对象
            money=model.money,
            status=model.status,      # 此时已经是枚举对象
            timestamp=model.timestamp,
            uuid=model.uuid
        )
