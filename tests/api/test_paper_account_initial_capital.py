# #6046 — create_paper_account 必须把 initial_capital 透传给 portfolio_service.add
"""
表象：POST /accounts 创建模拟盘时传 initial_capital=500000，
      但账户实际初始资金是 1,000,000（service.add 的 None 回退默认）。
根因：api/api/trading.py create_paper_account 调 portfolio_service.add()
      只传 name/mode/description，initial_capital 仅拼进 description 字符串，
      从未作为参数透传 → service 收到 None → 回退 1,000,000。
契约：create_paper_account(initial_capital=X) → service.add 被以 initial_capital=X 调用。

注：api/ 非 Python 包，经 tests/api/conftest 的 api_modules fixture 临时加入
    sys.path，import 须延迟到测试函数内。
"""
import asyncio
from unittest.mock import Mock


def test_create_paper_account_passes_initial_capital(api_modules, monkeypatch):
    """create_paper_account 必须把 initial_capital 透传给 portfolio_service.add"""
    from api import trading as trading_api
    from api.trading import CreatePaperAccountRequest

    mock_service = Mock()
    result = Mock()
    result.is_success.return_value = True
    result.data = {"uuid": "paper-uuid-1"}
    mock_service.add.return_value = result
    monkeypatch.setattr(trading_api, "_get_portfolio_service", lambda: mock_service)

    req = CreatePaperAccountRequest(name="paper-test", initial_capital=500000.0)
    asyncio.run(trading_api.create_paper_account(req))

    call_kwargs = mock_service.add.call_args.kwargs
    assert call_kwargs.get("initial_capital") == 500000.0, (
        f"initial_capital 未透传给 service.add, 实际 kwargs: {call_kwargs}"
    )
