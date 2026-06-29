# Issue: #5611
# Upstream: api.trading.create_paper_account
# Downstream: pytest
# Role: Paper Trading 创建端点 ID 字段统一为 uuid（与列表/详情端点一致）

"""
Paper Trading 创建端点 uuid 字段测试

根因：create_paper_account (trading.py:241) 返回 data={"account_id": portfolio_id}，
而 list (line 180) / detail (line 270) 端点统一返回 "uuid"。创建端点是全文件唯一
异类——内部变量名就是 portfolio_id（取自 portfolio.uuid），返回时却改名 account_id。
前端按创建响应取 account_id、按详情取 uuid，需双字段适配；遗漏一端即静默 undefined。

修复：创建端点返回 data={"uuid": portfolio_id}，与列表/详情统一。
"""

import pytest
from types import SimpleNamespace


class TestCreatePaperAccountUuidField:
    """#5611: 创建端点必须返回 uuid 字段（与列表/详情端点统一），而非 account_id"""

    def test_create_returns_uuid_not_account_id(self, monkeypatch):
        """创建成功响应的 data 含 'uuid'，不含 'account_id'（验收核心）"""
        import asyncio
        from api import trading

        class FakeResult:
            data = {"uuid": "port-abc123"}
            def is_success(self): return True

        class FakeSvc:
            def add(self, **kwargs): return FakeResult()

        monkeypatch.setattr(trading, "_get_portfolio_service", lambda: FakeSvc())

        req = trading.CreatePaperAccountRequest(name="test-account")
        resp = asyncio.run(trading.create_paper_account(req))

        assert resp["code"] == 0
        assert resp["data"]["uuid"] == "port-abc123"
        # account_id 必须消失，否则前端仍会按旧字段名取值
        assert "account_id" not in resp["data"]

    def test_create_uuid_value_matches_service_result_list_form(self, monkeypatch):
        """service 返回 list 形式 result 时，uuid 仍正确提取并以 uuid 字段返回（回归）"""
        import asyncio
        from api import trading

        portfolio = SimpleNamespace(uuid="port-from-list-xyz")
        class FakeResult:
            data = [portfolio]  # 生产 PortfolioService.get 经 crud find 返回 list 形状
            def is_success(self): return True
        class FakeSvc:
            def add(self, **kwargs): return FakeResult()

        monkeypatch.setattr(trading, "_get_portfolio_service", lambda: FakeSvc())

        req = trading.CreatePaperAccountRequest(name="list-form-account")
        resp = asyncio.run(trading.create_paper_account(req))

        assert resp["code"] == 0
        assert resp["data"]["uuid"] == "port-from-list-xyz"
        assert "account_id" not in resp["data"]
