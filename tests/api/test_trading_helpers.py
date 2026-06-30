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


# P0 #5479: 端点层 except Exception 不得吞 helper 的 HTTPException(500) 成 BusinessError(400)。
# 背景：helper _query_positions/_query_orders 已 raise HTTPException(500)（见上），
# 但端点 get_paper_account/get_paper_positions/get_paper_orders 的 except Exception
# 会先捕获它（HTTPException 继承 Exception）改写成 BusinessError(code=400)，
# 致 AC1 生产路径返 400 非 500——500 永远到不了 global_error_handler。
# 修法：每处 except Exception 前加 except HTTPException: raise 透传。
def test_get_paper_positions_endpoint_propagates_http_500(api_modules):
    """AC1 生产路径：helper raise HTTPException(500) 须透传到 global_error_handler，不被吞成 400。"""
    import asyncio
    import api.trading as trading_mod

    with patch.object(trading_mod, "_require_portfolio", return_value=[MagicMock()]), \
         patch.object(trading_mod, "_query_positions",
                      side_effect=HTTPException(status_code=500, detail="DB down")):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(trading_mod.get_paper_positions("acct-1"))
    assert exc.value.status_code == 500


def test_get_paper_orders_endpoint_propagates_http_500(api_modules):
    """AC1: get_paper_orders 端点同型透传 HTTPException(500)。"""
    import asyncio
    import api.trading as trading_mod

    with patch.object(trading_mod, "_require_portfolio", return_value=[MagicMock()]), \
         patch.object(trading_mod, "_query_orders",
                      side_effect=HTTPException(status_code=500, detail="DB down")):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(trading_mod.get_paper_orders("acct-1", status=None))
    assert exc.value.status_code == 500


def test_get_paper_account_endpoint_propagates_http_500(api_modules):
    """AC1: get_paper_account 端点同型透传（_query_positions 内部 raise HTTPException）。"""
    import asyncio
    import api.trading as trading_mod

    mock_p = MagicMock()
    mock_p.uuid = "p1"
    with patch.object(trading_mod, "_require_portfolio", return_value=[mock_p]), \
         patch.object(trading_mod, "_query_positions",
                      side_effect=HTTPException(status_code=500, detail="DB down")):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(trading_mod.get_paper_account("acct-1"))
    assert exc.value.status_code == 500


# #6495: #6380 给 get_paper_account/get_paper_positions/get_paper_orders 三端点加了
# except HTTPException: raise，但 list_paper_accounts（循环内调 _query_positions）漏改，
# DB 故障被 except Exception 吞成 BusinessError(400) 非 AC1 的 500。
# 修法：异常链补 except HTTPException: raise，与三 sibling 对齐。
def test_list_paper_accounts_endpoint_propagates_http_500(api_modules):
    """AC1: list_paper_accounts 端点同型透传 HTTPException(500)（循环内 _query_positions raise）。"""
    import asyncio
    import api.trading as trading_mod
    from ginkgo.data.services.base_service import ServiceResult

    # list_paper_accounts 经 portfolio_service.get(mode=PAPER) 拿账户列表，循环内调 _query_positions
    mock_p = MagicMock()
    mock_p.uuid = "p1"
    mock_p.initial_capital = 100000
    mock_p.cash = 100000
    mock_p.name = "paper-1"

    svc = MagicMock()
    svc.get.return_value = ServiceResult.success([mock_p])

    with patch.object(trading_mod, "_get_portfolio_service", return_value=svc), \
         patch.object(trading_mod, "_query_positions",
                      side_effect=HTTPException(status_code=500, detail="DB down")):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(trading_mod.list_paper_accounts())
    assert exc.value.status_code == 500
