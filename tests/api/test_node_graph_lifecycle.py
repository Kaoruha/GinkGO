"""
#5809 #5821 — node_graph 三端点（DELETE / duplicate / from-backtest）去 501 验证

验证端点正确委托到 PortfolioMappingService / BacktestTaskService，
不再返回 501。风格对齐 tests/api/test_portfolio_create_mode.py
（直接 await async 端点 + mock，函数内 import 规避 api/ sys.path 时机）。
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from ginkgo.data.services.base_service import ServiceResult


class TestDeleteNodeGraph:
    """DELETE /{graph_uuid} → service.delete_graph"""

    @pytest.mark.asyncio
    async def test_success_calls_service_and_returns_none(self):
        """成功时委托 delete_graph，204 路径无 body（函数无 return）"""
        from api.node_graph import delete_node_graph

        mock_svc = MagicMock()
        mock_svc.delete_graph.return_value = ServiceResult.success(
            data={"deleted_mappings": 2}
        )
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            result = await delete_node_graph("graph-1")

        mock_svc.delete_graph.assert_called_once_with("graph-1")
        assert result is None  # 204 No Content，无返回体

    @pytest.mark.asyncio
    async def test_failure_raises_400(self):
        """服务失败抛 400（不再 501）"""
        from api.node_graph import delete_node_graph

        mock_svc = MagicMock()
        mock_svc.delete_graph.return_value = ServiceResult.error("boom")
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                await delete_node_graph("graph-1")

        assert exc.value.status_code == 400
        assert "boom" in exc.value.detail


class TestDuplicateNodeGraph:
    """POST /{graph_uuid}/duplicate → service.duplicate_graph"""

    @pytest.mark.asyncio
    async def test_success_passes_name_and_returns_new_uuid(self):
        from api.node_graph import duplicate_node_graph

        mock_svc = MagicMock()
        mock_svc.duplicate_graph.return_value = ServiceResult.success(data={
            "new_portfolio_uuid": "new-1",
            "source_uuid": "src-1",
        })
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            result = await duplicate_node_graph("src-1", name="copy")

        mock_svc.duplicate_graph.assert_called_once_with("src-1", name="copy")
        assert isinstance(result, dict)
        assert result["data"]["new_portfolio_uuid"] == "new-1"

    @pytest.mark.asyncio
    async def test_failure_raises_400(self):
        """源图不存在抛 400（不再 501）"""
        from api.node_graph import duplicate_node_graph

        mock_svc = MagicMock()
        mock_svc.duplicate_graph.return_value = ServiceResult.error("source missing")
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                await duplicate_node_graph("src-1", name="copy")

        assert exc.value.status_code == 400


class TestCreateFromBacktest:
    """POST /from-backtest/{backtest_uuid} → backtest.portfolio_id → 现有图"""

    @pytest.mark.asyncio
    async def test_returns_existing_graph_for_backtest_portfolio(self):
        """查回测拿 portfolio_id，返回该组合的现有图（不创建新图）"""
        from api.node_graph import create_from_backtest

        mock_bt_svc = MagicMock()
        task = MagicMock()
        task.portfolio_id = "port-1"
        mock_bt_svc.get_by_id.return_value = ServiceResult.success(task)

        mock_mapping = MagicMock()
        mock_mapping.get_portfolio_graph.return_value = ServiceResult.success(
            data={"graph_data": {"nodes": []}, "metadata": {"name": "g"}}
        )

        with patch("ginkgo.data.containers.container.backtest_task_service",
                   return_value=mock_bt_svc), \
             patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_mapping):
            result = await create_from_backtest("bt-1")

        mock_bt_svc.get_by_id.assert_called_once_with("bt-1")
        mock_mapping.get_portfolio_graph.assert_called_once_with("port-1")
        assert result["data"]["portfolio_uuid"] == "port-1"
        assert result["data"]["graph_data"] == {"nodes": []}

    @pytest.mark.asyncio
    async def test_raises_404_when_backtest_missing(self):
        """回测不存在抛 404（不再 501）"""
        from api.node_graph import create_from_backtest

        mock_bt_svc = MagicMock()
        mock_bt_svc.get_by_id.return_value = ServiceResult.error("not found")

        with patch("ginkgo.data.containers.container.backtest_task_service",
                   return_value=mock_bt_svc):
            with pytest.raises(HTTPException) as exc:
                await create_from_backtest("bt-missing")

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_backtest_has_no_portfolio(self):
        """回测无 portfolio_id 抛 404"""
        from api.node_graph import create_from_backtest

        mock_bt_svc = MagicMock()
        task = MagicMock()
        task.portfolio_id = ""
        mock_bt_svc.get_by_id.return_value = ServiceResult.success(task)

        with patch("ginkgo.data.containers.container.backtest_task_service",
                   return_value=mock_bt_svc):
            with pytest.raises(HTTPException) as exc:
                await create_from_backtest("bt-1")

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_graph_missing(self):
        """回测存在但组合图不存在抛 404"""
        from api.node_graph import create_from_backtest

        mock_bt_svc = MagicMock()
        task = MagicMock()
        task.portfolio_id = "port-1"
        mock_bt_svc.get_by_id.return_value = ServiceResult.success(task)

        mock_mapping = MagicMock()
        mock_mapping.get_portfolio_graph.return_value = ServiceResult.error("no graph")

        with patch("ginkgo.data.containers.container.backtest_task_service",
                   return_value=mock_bt_svc), \
             patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_mapping):
            with pytest.raises(HTTPException) as exc:
                await create_from_backtest("bt-1")

        assert exc.value.status_code == 404
