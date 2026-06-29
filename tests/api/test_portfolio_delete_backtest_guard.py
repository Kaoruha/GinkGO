# #5688 — DELETE /api/v1/portfolios/{uuid} 含回测时无确认直接删，历史数据丢失
"""
验证 delete_portfolio 端点的回测守卫：
- 含回测 + 未传 force → ConflictError(409)，不执行删除
- 含回测 + force=true → 正常删除
- 无回测 → 直接删除（默认行为回归）
- portfolio 不存在 → NotFoundError(404)（既有行为回归）
"""
import pytest
from unittest.mock import MagicMock, patch

from core.exceptions import ConflictError, NotFoundError


def _ok_result():
    r = MagicMock()
    r.is_success.return_value = True
    return r


def _fail_result():
    r = MagicMock()
    r.is_success.return_value = False
    return r


class TestDeletePortfolioBacktestGuard:
    """#5688：delete_portfolio 删除前检查关联回测。"""

    @pytest.mark.asyncio
    @patch("api.portfolio._count_backtests", return_value=3)
    @patch("api.portfolio.get_portfolio_service")
    async def test_backtests_without_force_raises_conflict(self, mock_svc, mock_count):
        """含 3 条回测 + force=False → ConflictError(409)，不调 delete。"""
        from api.portfolio import delete_portfolio

        mock_svc.return_value.delete.return_value = _ok_result()
        # 直接 await 绕过 FastAPI，force 须显式传 bool（签名默认 Query(False) 对象 truthy 会跳过守卫）
        with pytest.raises(ConflictError) as exc:
            await delete_portfolio("pid-1", force=False)
        mock_svc.return_value.delete.assert_not_called()
        assert "3" in exc.value.message  # 回测数出现在 message
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    @patch("api.portfolio._count_backtests", return_value=3)
    @patch("api.portfolio.get_portfolio_service")
    async def test_backtests_with_force_deletes(self, mock_svc, mock_count):
        """含回测 + force=True → 强制删除，调 delete。"""
        from api.portfolio import delete_portfolio

        mock_svc.return_value.delete.return_value = _ok_result()
        await delete_portfolio("pid-1", force=True)
        mock_svc.return_value.delete.assert_called_once_with(portfolio_id="pid-1")

    @pytest.mark.asyncio
    @patch("api.portfolio._count_backtests", return_value=0)
    @patch("api.portfolio.get_portfolio_service")
    async def test_no_backtests_deletes_without_force(self, mock_svc, mock_count):
        """无回测 + force=False(默认) → 直接删除（回归默认行为）。"""
        from api.portfolio import delete_portfolio

        mock_svc.return_value.delete.return_value = _ok_result()
        await delete_portfolio("pid-1")
        mock_svc.return_value.delete.assert_called_once_with(portfolio_id="pid-1")

    @pytest.mark.asyncio
    @patch("api.portfolio._count_backtests", return_value=0)
    @patch("api.portfolio.get_portfolio_service")
    async def test_not_found_raises_404(self, mock_svc, mock_count):
        """portfolio 不存在 → NotFoundError(404)（既有行为回归）。"""
        from api.portfolio import delete_portfolio

        mock_svc.return_value.delete.return_value = _fail_result()
        with pytest.raises(NotFoundError):
            await delete_portfolio("missing-pid")

    @pytest.mark.asyncio
    @patch("api.portfolio._count_backtests", return_value=5)
    @patch("api.portfolio.get_portfolio_service")
    async def test_conflict_error_not_swallowed_by_general_except(self, mock_svc, mock_count):
        """ConflictError 不被端点 except Exception 吞成 BusinessError(400)。"""
        from api.portfolio import delete_portfolio

        mock_svc.return_value.delete.return_value = _ok_result()
        # 必须是 ConflictError(409) 而非被 except Exception 转成 BusinessError(400)
        # 直接 await 同样须显式 force=False（见切片 1 注释）
        with pytest.raises(ConflictError):
            await delete_portfolio("pid-1", force=False)
