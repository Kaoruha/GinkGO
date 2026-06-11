# Issue: #5588, #5910 — Events SSE 无限挂起
# Issue: #5634, #5585 — 响应格式不统一
# Issue: #5903, #5889 — Backtest 创建 Breaking Change
# Issue: #5858, #5777 — start_backtest 不传 config
#
# TDD tests for backtest API root cause fixes

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def run_async(coro):
    return asyncio.run(coro)


# ============================================================
# Root Cause A: Events SSE 无限挂起 (#5588, #5910)
# ============================================================

class TestBacktestEventsTimeout:
    """Events SSE 端点应在超时后自动断开，不应无限挂起"""

    def test_events_stream_terminates_when_no_progress(self):
        """当 Redis 无进度数据时，SSE 流应在有限时间内终止（非无限循环）"""
        from api.backtest import backtest_events

        async def _run():
            with patch("api.backtest.get_backtest_progress", new_callable=AsyncMock) as mock_progress:
                # 永远返回 None — 模拟任务不存在或 Redis 无数据
                mock_progress.return_value = None

                response = await backtest_events("nonexistent-uuid")
                assert response.media_type == "text/event-stream"

                # 在同一事件循环中消费 SSE 流
                events = await asyncio.wait_for(
                    _collect_sse_events(response.body_iterator),
                    timeout=5.0,
                )

                # 流应该已终止，收集到至少一个事件
                assert len(events) >= 1
                # 最后一个事件应包含 timeout 或 stream_end 标记
                last = events[-1]
                assert "timeout" in last or "stream_end" in last or "error" in last

        asyncio.run(_run())

    def test_events_stream_exits_on_terminal_state(self):
        """当任务状态为 COMPLETED/FAILED/CANCELLED 时，流应终止"""
        from api.backtest import backtest_events

        async def _run():
            with patch("api.backtest.get_backtest_progress", new_callable=AsyncMock) as mock_progress:
                mock_progress.return_value = {"state": "COMPLETED", "progress": 100}

                response = await backtest_events("done-uuid")
                events = await asyncio.wait_for(
                    _collect_sse_events(response.body_iterator),
                    timeout=3.0,
                )

                assert len(events) >= 1
                assert any("progress" in e for e in events)

        asyncio.run(_run())


async def _collect_sse_events(body_iterator):
    """消费 SSE 流，返回所有事件字符串列表"""
    events = []
    async for chunk in body_iterator:
        events.append(chunk)
    return events


# ============================================================
# Root Cause B: 响应格式不统一 (#5634, #5585)
# ============================================================

class TestBacktestResponseFormat:
    """回测数据端点响应格式应统一 — 使用 paginated() 而非嵌套 ok()"""

    def _make_mock_items(self, count=2):
        """创建 mock 数据对象列表"""
        items = []
        for i in range(count):
            obj = MagicMock()
            obj.dict.return_value = {"uuid": f"item-{i}", "code": f"00000{i}"}
            items.append(obj)
        return items

    def _make_service_result(self, items, total):
        """构造 ServiceResult，带 metadata"""
        from ginkgo.data.services.base_service import ServiceResult
        sr = ServiceResult.success(data=items)
        sr.set_metadata("total", total)
        return sr

    def test_orders_returns_paginated_format(self):
        """orders 端点应返回 data 为列表 + meta.total，而非 data.data[] 嵌套"""
        from api.backtest import get_backtest_orders

        items = self._make_mock_items(3)
        mock_svc = MagicMock()
        mock_svc.list_orders.return_value = self._make_service_result(items, 3)

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            result = run_async(get_backtest_orders("test-uuid"))

        # paginated() → data 是列表，meta 包含 total
        assert isinstance(result["data"], list), f"data 应为列表，实际为 {type(result['data'])}"
        assert len(result["data"]) == 3
        assert "meta" in result
        assert result["meta"]["total"] == 3

    def test_positions_returns_paginated_format(self):
        """positions 端点应返回 paginated 格式"""
        from api.backtest import get_backtest_positions

        items = self._make_mock_items(2)
        mock_svc = MagicMock()
        mock_svc.list_positions.return_value = self._make_service_result(items, 5)

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            result = run_async(get_backtest_positions("test-uuid"))

        assert isinstance(result["data"], list)
        assert len(result["data"]) == 2
        assert result["meta"]["total"] == 5


# ============================================================
# Root Cause F: Backtest 创建 Breaking Change (#5903, #5889)
# ============================================================

class TestBacktestCreateCompatibility:
    """Backtest 创建应支持旧 portfolio_id 字段"""

    def test_create_accepts_portfolio_id_string_as_alias(self):
        """旧客户端发送 portfolio_id (str) 应被转为 portfolio_uuids (list)"""
        from ginkgo.data.services.backtest_task_schemas import BacktestTaskCreate

        bt = BacktestTaskCreate(
            name="test",
            portfolio_id="uuid-1",  # 旧格式：单个字符串
            engine_config={
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
            }
        )
        assert bt.portfolio_uuids == ["uuid-1"]

    def test_create_prefers_portfolio_uuids_when_both_present(self):
        """同时传 portfolio_uuids 和 portfolio_id 时，优先用 portfolio_uuids"""
        from ginkgo.data.services.backtest_task_schemas import BacktestTaskCreate

        bt = BacktestTaskCreate(
            name="test",
            portfolio_uuids=["uuid-a", "uuid-b"],
            portfolio_id="uuid-old",
            engine_config={
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
            }
        )
        assert bt.portfolio_uuids == ["uuid-a", "uuid-b"]


# ============================================================
# Root Cause G: start_backtest 不传 config (#5858, #5777)
# ============================================================

class TestBacktestStartConfig:
    """start_backtest 应委托 service 层启动（service 内部负责 Kafka 发送）"""

    def test_start_delegates_to_service(self):
        """start_backtest 应调用 task_service.start_task，Kafka 由 service 层统一处理"""
        from api.backtest import start_backtest
        from ginkgo.data.services.base_service import ServiceResult

        task = MagicMock()
        task.uuid = "test-uuid"
        task.task_id = "task-123"

        mock_task_svc = MagicMock()
        mock_task_svc.get_by_id.return_value = ServiceResult.success(data=task)
        mock_task_svc.start_task.return_value = ServiceResult.success(
            data={"task_id": "task-123"}
        )

        with patch("api.backtest.get_backtest_task_service", return_value=mock_task_svc):
            result = run_async(start_backtest("test-uuid"))

        # API 层应调用 service.start_task（内部已发 Kafka）
        mock_task_svc.start_task.assert_called_once_with("test-uuid")
        assert result["data"]["uuid"] == "test-uuid"


# ============================================================
# Root Cause C: Analyzer Catalog 空 (#5876, #5912)
# ============================================================

class TestAnalyzerCatalog:
    """分析器类型列表不应为空"""

    def test_analyzer_list_returns_known_types(self):
        """list_analyzers 应返回至少一个分析器类型（内置回退）"""
        from api.backtest import list_analyzers

        mock_analyzer_svc = MagicMock()
        mock_analyzer_svc.get_analyzer_types.return_value = MagicMock(
            is_success=lambda: False, data=None, error="not implemented"
        )

        with patch("api.backtest.container") as mock_container:
            mock_container.analyzer_service.return_value = mock_analyzer_svc
            result = run_async(list_analyzers())

        # 即使 service 返回空，API 也应有内置回退列表
        data = result.get("data", [])
        assert isinstance(data, list)
        assert len(data) > 0, "Analyzer catalog 不应为空"


# ============================================================
# Root Cause D: PT status 硬编码 (#5904, #5877)
# ============================================================

class TestPaperTradingStatus:
    """Paper Trading status 应从实际状态查询，不应硬编码"""

    def test_account_status_reflects_db_state(self):
        """list_paper_accounts 的 status 应反映 DB portfolio.state，而非硬编码 stopped

        #5392 #5401: 早期 _get_pt_status 读死 Redis 导致永远 stopped；现由
        _map_pt_status 读 portfolio.state 映射。此处通过给 mock portfolio 设
        RUNNING 状态，验证端点正确产出 'running'。
        """
        from api.trading import list_paper_accounts
        from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES

        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "pt-1"
        mock_portfolio.name = "Test PT"
        mock_portfolio.initial_capital = 100000
        mock_portfolio.cash = 95000
        mock_portfolio.create_at = None
        # worker deploy 时写入的运行状态；_map_pt_status 据此映射
        mock_portfolio.state = PORTFOLIO_RUNSTATE_TYPES.RUNNING

        mock_svc = MagicMock()
        result_mock = MagicMock()
        result_mock.is_success.return_value = True
        result_mock.data = [mock_portfolio]
        mock_svc.get.return_value = result_mock

        with patch("api.trading._get_portfolio_service", return_value=mock_svc):
            result = run_async(list_paper_accounts())

        accounts = result["data"]
        assert len(accounts) == 1
        # status 不应是硬编码的 "stopped"，应反映 RUNNING
        assert accounts[0]["status"] == "running"


# ============================================================
# Root Cause E: Paper Trading 旧路由兼容 (#5647, #5781)
# ============================================================

class TestPaperTradingLegacyRoutes:
    """Paper Trading 应提供旧路由兼容"""

    def test_root_route_lists_accounts(self):
        """GET / 应等价于 GET /accounts"""
        from api.trading import router

        route_names = [r.name for r in router.routes]
        # 应有根路由或兼容路由
        assert "list_paper_accounts" in route_names
        # 检查是否有 "/" 路由（旧前端使用）
        root_routes = [r for r in router.routes
                       if hasattr(r, 'path') and r.path == "/"]
        assert len(root_routes) > 0, "缺少 GET / 旧路由兼容"


# ============================================================
# Root Cause H: Paper Trading 列表查询过滤 (#5449)
# ============================================================

class TestPaperTradingListFilter:
    """Paper Trading 列表应只返回 PAPER 模式的 Portfolio"""

    def test_list_calls_get_with_paper_mode(self):
        """list_paper_accounts 应传 mode=PAPER 给 service"""
        from api.trading import list_paper_accounts

        mock_svc = MagicMock()
        result_mock = MagicMock()
        result_mock.is_success.return_value = True
        result_mock.data = []
        mock_svc.get.return_value = result_mock

        with patch("api.trading._get_portfolio_service", return_value=mock_svc):
            result = run_async(list_paper_accounts())

        # 应传 mode 参数
        call_kwargs = mock_svc.get.call_args[1] if mock_svc.get.call_args else {}
        assert "mode" in call_kwargs, "应传 mode 参数过滤 PAPER 模式"
