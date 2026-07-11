"""实盘账户域枚举：交易所/账户状态/订阅数据类型/Broker 状态机（#3880 从模型文件迁移）。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""


class ExchangeType(str):
    """交易所类型枚举"""

    OKX = "okx"
    BINANCE = "binance"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "okx":
            return cls.OKX
        elif value == "binance":
            return cls.BINANCE
        else:
            raise ValueError(f"Unknown exchange type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证交易所类型是否有效"""
        return value in [cls.OKX, cls.BINANCE]


class AccountStatusType(str):
    """账号状态类型枚举"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "enabled":
            return cls.ENABLED
        elif value == "disabled":
            return cls.DISABLED
        elif value == "connecting":
            return cls.CONNECTING
        elif value == "disconnected":
            return cls.DISCONNECTED
        elif value == "error":
            return cls.ERROR
        else:
            raise ValueError(f"Unknown account status type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证账号状态是否有效"""
        return value in [cls.ENABLED, cls.DISABLED, cls.CONNECTING, cls.DISCONNECTED, cls.ERROR]


class SubscriptionDataType(str):
    """市场订阅数据类型枚举"""

    TICKER = "ticker"
    CANDLESTICKS = "candlesticks"
    TRADES = "trades"
    ORDERBOOK = "orderbook"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "ticker":
            return cls.TICKER
        elif value == "candlesticks":
            return cls.CANDLESTICKS
        elif value == "trades":
            return cls.TRADES
        elif value == "orderbook":
            return cls.ORDERBOOK
        else:
            raise ValueError(f"Unknown subscription data type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证订阅数据类型是否有效"""
        return value in [cls.TICKER, cls.CANDLESTICKS, cls.TRADES, cls.ORDERBOOK]

    @classmethod
    def all_types(cls) -> list[str]:
        """返回所有数据类型"""
        return [cls.TICKER, cls.CANDLESTICKS, cls.TRADES, cls.ORDERBOOK]


class BrokerStateType(str):
    """Broker 状态类型枚举"""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "uninitialized":
            return cls.UNINITIALIZED
        elif value == "initializing":
            return cls.INITIALIZING
        elif value == "running":
            return cls.RUNNING
        elif value == "paused":
            return cls.PAUSED
        elif value == "stopped":
            return cls.STOPPED
        elif value == "error":
            return cls.ERROR
        elif value == "recovering":
            return cls.RECOVERING
        else:
            raise ValueError(f"Unknown broker state type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证 Broker 状态是否有效"""
        return value in [
            cls.UNINITIALIZED, cls.INITIALIZING, cls.RUNNING,
            cls.PAUSED, cls.STOPPED, cls.ERROR, cls.RECOVERING,
        ]

    @classmethod
    def is_terminal(cls, state: str) -> bool:
        """检查状态是否为终止状态"""
        return state in [cls.STOPPED, cls.ERROR]

    @classmethod
    def is_active(cls, state: str) -> bool:
        """检查状态是否为活跃状态（可接收订单）"""
        return state in [cls.RUNNING]

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        """检查状态转换是否合法"""
        valid_transitions = {
            cls.UNINITIALIZED: [cls.INITIALIZING, cls.STOPPED],
            cls.INITIALIZING: [cls.RUNNING, cls.ERROR, cls.STOPPED],
            cls.RUNNING: [cls.PAUSED, cls.STOPPED, cls.ERROR, cls.RECOVERING],
            cls.PAUSED: [cls.RUNNING, cls.STOPPED, cls.ERROR],
            cls.STOPPED: [cls.INITIALIZING, cls.RECOVERING],
            cls.ERROR: [cls.RECOVERING, cls.STOPPED],
            cls.RECOVERING: [cls.RUNNING, cls.ERROR, cls.STOPPED],
        }
        return to_state in valid_transitions.get(from_state, [])


__all__ = ['ExchangeType', 'AccountStatusType', 'SubscriptionDataType', 'BrokerStateType']
