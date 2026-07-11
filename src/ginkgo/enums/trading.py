"""交易订单域枚举：方向/转账方向/订单/订单状态/转账状态/追踪状态/资金调整/币种。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase


class CURRENCY_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    CNY = 1
    USD = 2


class DIRECTION_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    LONG = 1
    SHORT = 2


class TRANSFERDIRECTION_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    IN = 1
    OUT = 2


class ORDER_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    MARKETORDER = 1
    LIMITORDER = 2


class ORDERSTATUS_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    NEW = 1
    SUBMITTED = 2
    PARTIAL_FILLED = 3
    PARTIALLY_FILLED = 3  # 别名，兼容不同命名风格
    FILLED = 4
    CANCELED = 5
    CANCELLED = 5  # 双L别名，兼容 brokers 层拼写 (#6061)
    REJECTED = 6


class TRANSFERSTATUS_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4
    CANCELLED = 4  # 双L别名 (#6061)
    PENDING = 5


class CAPITALADJUSTMENT_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    EXR_EXD = 1  # 除权除息
    BONUS_RIGHTS_LIST = 2  # 送配股上市
    NON_TRADABLE_LIST = 3  # 非流通股上市
    UNKNOWN_CHANGE = 4  # 为知股本变动
    CAPITALCHANGE = 5  # 股本变化
    ADDITIONAL_ISSUANCE = 6  # 新股发行
    SHARE_BUYBACK = 7  # 股份回购
    NEW_SHARE_LIST = 8  # 增发新股上市
    TRANSFER_RIGHTS_LIST = 9  # 转配股上市
    CB_LIST = 10  # 可转债上市
    SPLIT_REVERSE_SPLIT = 11  # 扩缩股
    NON_TRADABLE_REVERSE_SPLIT = 12  # 非流通股缩股
    CALL_WARRANT = 13  # 送认购权证
    PUT_WARRANT = 14  # 送认沽权证


class TRACKINGSTATUS_TYPES(EnumBase):
    """信号追踪状态枚举"""

    VOID = -1
    PENDING = 0                 # 待处理
    NOTIFIED = 1                # 已通知
    EXECUTED = 2                # 已执行
    TIMEOUT = 3                 # 超时
    CANCELED = 4                # 已取消
    CANCELLED = 4                # 双L别名 (#6061)


__all__ = ['CURRENCY_TYPES', 'DIRECTION_TYPES', 'TRANSFERDIRECTION_TYPES', 'ORDER_TYPES', 'ORDERSTATUS_TYPES', 'TRANSFERSTATUS_TYPES', 'CAPITALADJUSTMENT_TYPES', 'TRACKINGSTATUS_TYPES']
