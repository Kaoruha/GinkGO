"""
#5806 — GET /node-graphs/{portfolio_uuid}/files 端点

表象：前端列出 portfolio 已绑定文件时，只有 POST/DELETE files，无 GET files，
      只能退而调 GET /mappings（含参数，重）。缺一个语义直白的文件列表端点。
契约：
  - GET /{portfolio_uuid}/files 委托 service.get_portfolio_mappings
  - 返回 {portfolio_uuid, files:[...], total}
  - service 失败时 404（与 mappings 端点一致）
风格对齐 tests/api/test_node_graph_lifecycle.py（函数内 import + mock + await）。
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from ginkgo.data.services.base_service import ServiceResult


class TestGetPortfolioFiles:
    """GET /{portfolio_uuid}/files → 返已绑定文件列表 (#5806)"""

    @pytest.mark.asyncio
    async def test_returns_bound_files_list(self):
        """成功时委托 service 并返文件列表 + total"""
        from api.node_graph import get_portfolio_files

        mock_svc = MagicMock()
        mock_svc.get_portfolio_mappings.return_value = ServiceResult.success(data=[
            {"file_id": "f1", "type": "STRATEGY"},
            {"file_id": "f2", "type": "SELECTOR"},
        ])
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            result = await get_portfolio_files("p1")

        mock_svc.get_portfolio_mappings.assert_called_once()
        assert result["data"]["portfolio_uuid"] == "p1"
        assert result["data"]["total"] == 2
        assert len(result["data"]["files"]) == 2

    @pytest.mark.asyncio
    async def test_service_failure_raises_404(self):
        """service 失败抛 404（与 mappings 端点一致）"""
        from api.node_graph import get_portfolio_files

        mock_svc = MagicMock()
        mock_svc.get_portfolio_mappings.return_value = ServiceResult.error("not found")
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                await get_portfolio_files("p1")

        assert exc.value.status_code == 404
