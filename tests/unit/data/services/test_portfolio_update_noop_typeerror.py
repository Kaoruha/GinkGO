"""#5409: portfolio update 在无可更新字段时不应抛 TypeError。

复现 issue：PUT /api/v1/portfolios/{id} 触发 saga.update_basic_info，
当 saga 字段被 `**kwargs` 丢弃致 `updates` 空时，命中
`ServiceResult.success({}, msg, warnings)` 第 3 个位置参数 → TypeError
（success 签名只收 data/message 两参），端点误报 "rolled back"。

隔离单测：mock crud，不连库。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_src = str(project_root / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from ginkgo.data.services.portfolio_service import PortfolioService


@pytest.fixture
def noop_portfolio_service():
    """PortfolioService with mocked collaborators (no DB)."""
    svc = PortfolioService(crud_repo=MagicMock(), portfolio_file_mapping_crud=MagicMock())
    return svc


class TestPortfolioUpdateNoopNoTypeerror:
    """#5409 regression: update 无可更新字段路径。"""

    def test_update_with_no_fields_returns_success_not_typeerror(self, noop_portfolio_service):
        """仅传 portfolio_id（无可更新字段）应返回 success，不抛 TypeError。"""
        with patch.object(noop_portfolio_service, "is_portfolio_frozen", return_value=False):
            # 修复前：line 260 ServiceResult.success({}, msg, warnings) → TypeError
            result = noop_portfolio_service.update(portfolio_id="some-uuid")

        assert result.is_success(), f"expected success, got error={result.error!r}"

    def test_update_with_no_fields_message_indicates_noop(self, noop_portfolio_service):
        """无字段更新应通过 message（而非抛异常）告知调用方是 no-op。"""
        with patch.object(noop_portfolio_service, "is_portfolio_frozen", return_value=False):
            result = noop_portfolio_service.update(portfolio_id="some-uuid")

        assert result.is_success()
        text = (result.message or "").lower()
        assert "no update" in text, f"message should mention no-update, got {result.message!r}"

    def test_update_with_only_unknown_kwarg_no_typeerror(self, noop_portfolio_service):
        """saga 路径：initial_capital 不在 update 签名，被 **kwargs 丢弃致 updates 空。

        调用方（saga.update_basic_info）传 update(portfolio_uuid, initial_capital=X)，
        update 内部 kwargs 接收但不处理 → updates 空 → 应返回 success(no-op)，
        不应抛 TypeError。
        """
        with patch.object(noop_portfolio_service, "is_portfolio_frozen", return_value=False):
            result = noop_portfolio_service.update(
                portfolio_id="some-uuid", initial_capital=100000.0
            )

        assert result.is_success(), f"expected success, got error={result.error!r}"


class TestPortfolioUpdateInitialCapitalPersisted:
    """#5409 第二半：saga 转发 initial_cash -> update(initial_capital=X) 应真正写入 DB。

    Portfolio model 有 initial_capital 字段，但 update() 历史签名未暴露，
    saga 传入被 **kwargs 静默丢弃 → updates 空 → 即便修了 TypeError 也只是 no-op，
    用户改 initial_cash 会"静默不生效"。update 应显式处理 initial_capital。
    """

    def test_update_initial_capital_is_persisted(self, noop_portfolio_service):
        """update(portfolio_id, initial_capital=X) 应把 initial_capital 写入 updates。"""
        noop_portfolio_service._crud_repo.modify = MagicMock()
        with patch.object(noop_portfolio_service, "is_portfolio_frozen", return_value=False):
            result = noop_portfolio_service.update(
                portfolio_id="some-uuid", initial_capital=500000.0
            )

        assert result.is_success(), f"expected success, got error={result.error!r}"
        noop_portfolio_service._crud_repo.modify.assert_called_once()
        updates = noop_portfolio_service._crud_repo.modify.call_args.kwargs.get("updates")
        assert updates is not None, "modify should be called with updates dict"
        assert updates.get("initial_capital") == 500000.0, \
            f"initial_capital should be in updates, got {updates!r}"

