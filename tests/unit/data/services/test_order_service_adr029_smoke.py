"""OrderService ADR-029 Task 7/8 写路径 smoke（upsert + create_record + get_df）。

``upsert_order``（存在判断 ``get_by_uuid`` → modify/insert 双语义，``status_override``
事件后状态覆盖）+ ``create_order_record``（懒 import OrderRecordCRUD 写 MOrderRecord）+
``get_orders_df``（出口① DataFrame）被 containers import 链触达但 smoke 不调方法体
→ diff coverage gate 红。本 smoke mock crud 调起方法体补覆盖信号，并锁定 ADR-029 新契约。
"""
from unittest.mock import patch, MagicMock

import pandas as pd

from ginkgo.entities import Order
from ginkgo.enums import ORDERSTATUS_TYPES
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.services.order_service import OrderService


class _FakeCrud:
    """最小 crud mock：记录 add/modify 调用，get_by_uuid 可注入存在性。"""

    def __init__(self, existing=None):
        self._existing = existing
        self.added = []
        self.modified = []

    def get_by_uuid(self, uuid):
        return self._existing

    def add(self, model):
        self.added.append(model)

    def modify(self, filters, updates):
        self.modified.append((filters, updates))

    def find(self, filters=None, page=None, page_size=None, order_by=None, desc_order=None):
        return [MOrder(portfolio_id="p", engine_id="e")]


# ---------------- upsert_order ----------------
def test_upsert_insert_path():
    """get_by_uuid→None：Order Entity→mapper→crud.add，action=insert（L274-285）。"""
    crud = _FakeCrud(existing=None)
    svc = OrderService(crud_repo=crud)
    order = Order(uuid="u1", portfolio_id="p", engine_id="e", code="000001", volume=100)
    res = svc.upsert_order(order)
    assert res.success
    assert res.data["action"] == "insert"
    assert len(crud.added) == 1


def test_upsert_update_path():
    """get_by_uuid→<obj>：modify 语义，action=update（L256-272）。"""
    crud = _FakeCrud(existing=MagicMock(uuid="u1"))
    svc = OrderService(crud_repo=crud)
    order = Order(uuid="u1", portfolio_id="p", engine_id="e", code="000001", volume=100,
                  status=ORDERSTATUS_TYPES.NEW, fee=5)
    res = svc.upsert_order(order)
    assert res.success
    assert res.data["action"] == "update"
    assert len(crud.modified) == 1


def test_upsert_status_override():
    """status_override 覆盖 order.status（事件后状态，L249-261）。"""
    crud = _FakeCrud(existing=MagicMock(uuid="u1"))
    svc = OrderService(crud_repo=crud)
    order = Order(uuid="u1", portfolio_id="p", engine_id="e", code="000001", volume=100,
                  status=ORDERSTATUS_TYPES.NEW)
    res = svc.upsert_order(order, status_override=ORDERSTATUS_TYPES.FILLED)
    assert res.success
    _filters, updates = crud.modified[0]
    assert updates["status"] == ORDERSTATUS_TYPES.FILLED


def test_upsert_no_uuid_returns_error():
    """order 无 uuid → ServiceResult.error（L246-247）。Order Entity 自动生成 uuid，
    用无 uuid 的裸对象触发缺失守卫。"""
    svc = OrderService(crud_repo=_FakeCrud())

    class NoUuid:
        pass

    res = svc.upsert_order(NoUuid())  # getattr(order, "uuid", None) → None
    assert not res.success


# ---------------- create_order_record ----------------
def test_create_order_record_delegates_to_crud():
    """懒 import OrderRecordCRUD → create(**kwargs)（L308-319）。"""
    fake_crud = MagicMock()
    with patch(
        "ginkgo.data.crud.order_record_crud.OrderRecordCRUD",
        return_value=fake_crud,
    ):
        svc = OrderService(crud_repo=_FakeCrud())
        res = svc.create_order_record(code="000001", portfolio_id="p")
    assert res.success
    fake_crud.create.assert_called_once_with(code="000001", portfolio_id="p")


# ---------------- get_orders_df ----------------
def test_get_orders_df_returns_dataframe():
    """find→list → models_to_dataframe（L122）。"""
    svc = OrderService(crud_repo=_FakeCrud())
    res = svc.get_orders_df(portfolio_id="p")
    assert res.success
    assert isinstance(res.data, pd.DataFrame)


# ---------------- except 分支（覆盖 L283-285 / L317-319）----------------
class _BoomCrud:
    """crud 抛异常，触发 service except 分支。"""

    def get_by_uuid(self, uuid):
        raise RuntimeError("db down")


def test_upsert_exception_returns_error():
    """get_by_uuid 抛异常 → except → ServiceResult.error（L283-285）。"""
    svc = OrderService(crud_repo=_BoomCrud())
    order = Order(uuid="u1", portfolio_id="p", engine_id="e", code="000001", volume=100)
    res = svc.upsert_order(order)
    assert not res.success


def test_create_order_record_exception_returns_error():
    """OrderRecordCRUD.create 抛异常 → except → ServiceResult.error（L317-319）。"""
    fake_crud = MagicMock()
    fake_crud.create.side_effect = RuntimeError("db down")
    with patch(
        "ginkgo.data.crud.order_record_crud.OrderRecordCRUD",
        return_value=fake_crud,
    ):
        svc = OrderService(crud_repo=_FakeCrud())
        res = svc.create_order_record(code="000001")
    assert not res.success
