"""#6061: CANCELED/CANCELLED 双L别名向后兼容测试。

6 个枚举历史用单 L ``CANCELED``，而 brokers 层用双 L ``CANCELLED``。
为枚举加双 L 别名桥接两套拼写；别名与原成员同一对象、同值，单 L 引用不受影响。

先例：``ORDERSTATUS_TYPES`` 已有 ``PARTIALLY_FILLED`` 别名（enums.py L189）。
"""
from ginkgo.enums import (
    ORDERSTATUS_TYPES,
    TRANSFERSTATUS_TYPES,
    RECORDSTAGE_TYPES,
    ENGINE_TYPES,
    EXECUTION_STATUS,
    TRACKINGSTATUS_TYPES,
)


def test_orderstatus_cancelled_alias():
    assert ORDERSTATUS_TYPES.CANCELLED is ORDERSTATUS_TYPES.CANCELED
    assert ORDERSTATUS_TYPES.CANCELLED.value == 5


def test_transferstatus_cancelled_alias():
    assert TRANSFERSTATUS_TYPES.CANCELLED is TRANSFERSTATUS_TYPES.CANCELED
    assert TRANSFERSTATUS_TYPES.CANCELLED.value == 4


def test_recordstage_ordercancelled_alias():
    # RECORDSTAGE 取消成员是带 ORDER 前缀的 ORDERCANCELED
    assert RECORDSTAGE_TYPES.ORDERCANCELLED is RECORDSTAGE_TYPES.ORDERCANCELED
    assert RECORDSTAGE_TYPES.ORDERCANCELLED.value == 5


def test_engine_cancelled_alias():
    assert ENGINE_TYPES.CANCELLED is ENGINE_TYPES.CANCELED
    assert ENGINE_TYPES.CANCELLED.value == 7


def test_execution_status_cancelled_alias():
    assert EXECUTION_STATUS.CANCELLED is EXECUTION_STATUS.CANCELED
    assert EXECUTION_STATUS.CANCELLED.value == 4


def test_trackingstatus_cancelled_alias():
    assert TRACKINGSTATUS_TYPES.CANCELLED is TRACKINGSTATUS_TYPES.CANCELED
    assert TRACKINGSTATUS_TYPES.CANCELLED.value == 4
