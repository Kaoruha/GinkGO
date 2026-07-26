# Issue #6786 AC2: create_backtest_task 持久化 trace_id 到 task.meta JSON
#
# 方案：复用 MMysqlBase.meta JSON 字段（String(255) default "{}"），避免 schema 变更
# 触发安全阀。create_backtest_task 从 GLOG contextvars 取 trace_id（#6784 TraceIdMiddleware
# 注入），json.dumps({"trace_id": tid}) 写入 service.create 的 meta kwarg；service.create
# **kwargs 展开落 crud.create → model.meta 字段。worker/CLI 后续从 meta 读 trace_id
# （AC5 backtest cat 显示），即使 Kafka header 丢失，meta 仍可回查。

import json
import pytest
from unittest.mock import patch, MagicMock


class TestCreateBacktestTaskPersistsTraceIdToMeta:
    """#6786 AC2: create_backtest_task 把 trace_id 持久化到 task.meta JSON"""

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_create_persists_trace_id_to_meta(self, mock_get_service, mock_portfolio, api_modules):
        """GLOG contextvars 有 trace_id 时，service.create 收到 meta JSON 含 trace_id。"""
        from api.backtest import create_backtest_task, BacktestTaskCreate, EngineConfig
        from ginkgo.libs import GLOG

        mock_portfolio.return_value = {"uuid": "p-1", "name": "Portfolio1"}
        mock_task = MagicMock()
        mock_task.uuid = "task-uuid"
        mock_task.created_at = "2025-01-01T00:00:00Z"
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = mock_task
        mock_service = MagicMock()
        mock_service.create.return_value = mock_result
        mock_get_service.return_value = mock_service

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["p-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
        )

        with GLOG.with_trace_id("tid-meta-456"):
            create_backtest_task(data)

        call_kwargs = mock_service.create.call_args.kwargs
        assert "meta" in call_kwargs, f"create() 未收到 meta, 实际: {list(call_kwargs.keys())}"
        meta = json.loads(call_kwargs["meta"])
        assert meta.get("trace_id") == "tid-meta-456"

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_create_no_trace_id_no_meta(self, mock_get_service, mock_portfolio, api_modules):
        """无 trace_id 上下文时不写 meta（向后兼容，保持 model 默认 "{}"）。"""
        from api.backtest import create_backtest_task, BacktestTaskCreate, EngineConfig
        from ginkgo.libs.core.logger import _trace_id_ctx

        mock_portfolio.return_value = {"uuid": "p-1", "name": "Portfolio1"}
        mock_task = MagicMock()
        mock_task.uuid = "task-uuid"
        mock_task.created_at = "2025-01-01T00:00:00Z"
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = mock_task
        mock_service = MagicMock()
        mock_service.create.return_value = mock_result
        mock_get_service.return_value = mock_service

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["p-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
        )

        token = _trace_id_ctx.set(None)
        try:
            create_backtest_task(data)
        finally:
            _trace_id_ctx.reset(token)

        call_kwargs = mock_service.create.call_args.kwargs
        assert "meta" not in call_kwargs, "无 trace_id 时不应写 meta（保持 model 默认）"
