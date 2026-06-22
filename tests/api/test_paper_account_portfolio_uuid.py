# Issue: #5648 — Paper Trading CreatePaperAccountRequest 缺 portfolio_uuid
# Upstream: api.api.trading.CreatePaperAccountRequest, create_paper_account
# Downstream: PortfolioService.add（新建）/ _require_portfolio（关联校验）
# Role: 验证创建 paper account 时可关联已有 Portfolio（含策略组件）

"""
Paper Trading portfolio_uuid 关联测试 (#5648)。

根因：CreatePaperAccountRequest 无 portfolio_uuid 字段，create_paper_account
恒新建空 Portfolio，用户无法复用已绑定策略/选股/仓位/风控组件的 Portfolio。

修复：schema 加 portfolio_uuid: Optional[str]；create 分支——
- 提供 portfolio_uuid → _require_portfolio 校验存在 + 返回该 uuid（不新建）
- 未提供 → 现行新建行为不变
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.exceptions import NotFoundError


def run_async(coro):
    return asyncio.run(coro)


class TestCreatePaperAccountRequestSchema:
    """#5648: schema 接受 portfolio_uuid 字段，默认 None（向后兼容）。"""

    def test_request_accepts_portfolio_uuid(self):
        """验收: schema 必须接受 portfolio_uuid 字段。"""
        from api.trading import CreatePaperAccountRequest

        req = CreatePaperAccountRequest(name="t", portfolio_uuid="port-abc-123")
        assert req.portfolio_uuid == "port-abc-123"

    def test_portfolio_uuid_defaults_none(self):
        """不传 portfolio_uuid 时默认 None（现行新建行为保持不变）。"""
        from api.trading import CreatePaperAccountRequest

        req = CreatePaperAccountRequest(name="t")
        assert req.portfolio_uuid is None


class TestCreatePaperAccountLinksExistingPortfolio:
    """#5648: 提供 portfolio_uuid → 关联已有 Portfolio，不新建。"""

    def test_provided_uuid_returns_it_without_creating_new(self):
        """验收: 提供已存在 portfolio_uuid → account_id 为该 uuid，portfolio_service.add 不被调用。"""
        from api.trading import create_paper_account, CreatePaperAccountRequest

        req = CreatePaperAccountRequest(name="t", portfolio_uuid="exist-uuid")

        with patch("api.trading._require_portfolio", return_value=SimpleNamespace(uuid="exist-uuid")) as mock_req, \
             patch("api.trading._get_portfolio_service") as mock_svc_factory:
            result = run_async(create_paper_account(req))

        # _require_portfolio 被调用校验存在
        mock_req.assert_called_once_with("exist-uuid")
        # 不新建：portfolio_service.add 不应被调用
        mock_svc_factory.return_value.add.assert_not_called()
        # 返回的 account_id 就是传入的 portfolio_uuid
        assert result["data"]["account_id"] == "exist-uuid"

    def test_linked_portfolio_mode_updated_to_paper(self):
        """#5648 review: 关联已有 portfolio 时设 mode=PAPER。

        根因：list_paper_accounts 按 mode=PAPER 过滤；关联路径不改 mode，
        关联的 BACKTEST portfolio 查不到。修复=关联时 update mode=PAPER，
        与新建路径（add mode=PAPER）对称。
        """
        from api.trading import create_paper_account, CreatePaperAccountRequest
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        req = CreatePaperAccountRequest(name="t", portfolio_uuid="exist-uuid")
        upd_ok = SimpleNamespace(is_success=lambda: True)

        with patch("api.trading._require_portfolio",
                   return_value=SimpleNamespace(uuid="exist-uuid")), \
             patch("api.trading._get_portfolio_service") as mock_svc_factory:
            mock_svc_factory.return_value.update.return_value = upd_ok
            result = run_async(create_paper_account(req))

        # 关联时 update 被调用，portfolio_id 位置传，mode=PAPER
        mock_svc_factory.return_value.update.assert_called_once()
        args, kwargs = mock_svc_factory.return_value.update.call_args
        assert args[0] == "exist-uuid"
        assert kwargs.get("mode") == PORTFOLIO_MODE_TYPES.PAPER
        assert result["data"]["account_id"] == "exist-uuid"

    def test_nonexistent_uuid_raises_not_found(self):
        """提供不存在的 portfolio_uuid → NotFoundError（复用 _require_portfolio 校验）。"""
        from api.trading import create_paper_account, CreatePaperAccountRequest

        req = CreatePaperAccountRequest(name="t", portfolio_uuid="nope-uuid")

        with patch("api.trading._require_portfolio",
                   side_effect=NotFoundError("Paper account", "nope-uuid")), \
             patch("api.trading._get_portfolio_service") as mock_svc_factory:
            with pytest.raises(NotFoundError):
                run_async(create_paper_account(req))

        # 校验失败时不应新建
        mock_svc_factory.return_value.add.assert_not_called()

    def test_omitted_uuid_creates_new_portfolio(self):
        """不提供 portfolio_uuid → 现行新建行为（portfolio_service.add 被调用）。"""
        from api.trading import create_paper_account, CreatePaperAccountRequest

        req = CreatePaperAccountRequest(name="t")  # portfolio_uuid 默认 None

        mock_result = SimpleNamespace(
            is_success=lambda: True,
            data=SimpleNamespace(uuid="new-uuid"),
        )

        with patch("api.trading._get_portfolio_service") as mock_svc_factory:
            mock_svc_factory.return_value.add.return_value = mock_result
            result = run_async(create_paper_account(req))

        # 新建路径：add 被调用
        mock_svc_factory.return_value.add.assert_called_once()
        assert result["data"]["account_id"] == "new-uuid"
