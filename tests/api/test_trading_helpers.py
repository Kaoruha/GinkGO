"""#5479: trading helper 不再将 DB 故障吞为空列表。

验收：
- DB 故障（service success=False）→ HTTPException(500)，不返空列表
- status_filter 用所有提供的值（IN 语义），不取首元素
"""
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException

from ginkgo.data.services.base_service import ServiceResult


def test_query_positions_raises_on_db_error(api_modules):
    """DB 故障（service success=False）必须 raise HTTPException(500)，不得返空列表。"""
    import api.trading as trading_mod

    with patch.object(trading_mod, "_get_result_service") as m_svc:
        svc = MagicMock()
        svc.get_current_positions.return_value = ServiceResult.error("db connection lost")
        m_svc.return_value = svc

        with pytest.raises(HTTPException) as exc:
            trading_mod._query_positions("acct-1")

    assert exc.value.status_code == 500


def test_query_orders_raises_on_db_error(api_modules):
    """DB 故障 → HTTPException(500)，不返空列表。"""
    import api.trading as trading_mod

    with patch.object(trading_mod, "_get_result_service") as m_svc:
        svc = MagicMock()
        svc.get_orders_by_portfolio.return_value = ServiceResult.error("db conn lost")
        m_svc.return_value = svc

        with pytest.raises(HTTPException) as exc:
            trading_mod._query_orders("acct-1")

    assert exc.value.status_code == 500


def test_query_orders_status_filter_uses_all_enums(api_modules):
    """status_filter=['pending'] → pending 映射 [NEW, SUBMITTED] 两个 enum 都查（IN 语义），不只 NEW。"""
    from types import SimpleNamespace
    import api.trading as trading_mod
    from ginkgo.enums import ORDERSTATUS_TYPES

    rec_new = SimpleNamespace(uuid="ord-new", code="000001", direction=1, limit_price=10,
        volume=100, transaction_volume=0, transaction_price=0,
        status=ORDERSTATUS_TYPES.NEW, business_timestamp=None, timestamp=None)
    rec_sub = SimpleNamespace(uuid="ord-sub", code="000002", direction=1, limit_price=20,
        volume=200, transaction_volume=0, transaction_price=0,
        status=ORDERSTATUS_TYPES.SUBMITTED, business_timestamp=None, timestamp=None)

    def fake_get(account_id, status=None, page_size=100):
        if status == ORDERSTATUS_TYPES.NEW.value:
            return ServiceResult.success({"data": [rec_new]})
        if status == ORDERSTATUS_TYPES.SUBMITTED.value:
            return ServiceResult.success({"data": [rec_sub]})
        return ServiceResult.success({"data": []})

    with patch.object(trading_mod, "_get_result_service") as m_svc:
        svc = MagicMock()
        svc.get_orders_by_portfolio.side_effect = fake_get
        m_svc.return_value = svc
        orders = trading_mod._query_orders("acct-1", status_filter=["pending"])

    called_statuses = [c.kwargs.get("status") for c in svc.get_orders_by_portfolio.call_args_list]
    assert ORDERSTATUS_TYPES.NEW.value in called_statuses
    assert ORDERSTATUS_TYPES.SUBMITTED.value in called_statuses
    ids = {o["order_id"] for o in orders}
    assert "ord-new" in ids
    assert "ord-sub" in ids
