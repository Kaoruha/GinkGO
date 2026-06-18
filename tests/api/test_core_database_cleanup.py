"""#6177: api 层不得再引用已弃用且被 gitignore 的 core.database 模块。

core.database (api/core/database.py) 被 .gitignore:192 (database.*) 排除，
只在本地存在、从未提交，master / CI 上根本没有。任何 api 源文件 import 它
都会在 import 阶段崩 ModuleNotFoundError，导致 `ginkgo serve api` 启动失败。

这些测试驱动把三处废弃引用清理掉，改走服务层 ginkgo.data.containers.container：
  - api/api/node_graph.py        —— get_db 仅作 Depends 注入，db 参数从未使用（死依赖）
  - api/api/portfolio.py         —— get_db 导入后全文未引用（完全死导入）
  - api/services/backtest_progress_consumer.py —— get_db_cursor 真用到了，4 处裸 SQL
    迁移到 BacktestTaskService（对齐 producer 端 progress_tracker.py 的正确写法）
"""

import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# conftest 的 api_modules fixture（autouse）已把 <worktree>/api 加入 sys.path，
# 因此可直接 `import api.node_graph`（即 api/api/node_graph.py）等。


class TestNodeGraphNoCoreDatabase:
    """node_graph 模块必须能在 app_dir 布局下干净 import（不依赖 core.database）"""

    @pytest.mark.unit
    def test_node_graph_imports_without_core_database(self):
        mod = importlib.import_module("api.node_graph")
        assert mod is not None
        assert hasattr(mod, "router")


class TestPortfolioNoCoreDatabase:
    """portfolio 模块必须能在 app_dir 布局下干净 import（不依赖 core.database）"""

    @pytest.mark.unit
    def test_portfolio_imports_without_core_database(self):
        mod = importlib.import_module("api.portfolio")
        assert mod is not None
        assert hasattr(mod, "router")


class TestProgressConsumerNoCoreDatabase:
    """进度消费者不得再用 core.database 的裸 SQL，改走 BacktestTaskService（对齐 producer）"""

    @pytest.mark.unit
    def test_module_imports_without_core_database(self):
        mod = importlib.import_module("services.backtest_progress_consumer")
        assert mod is not None
        assert hasattr(mod, "BacktestProgressConsumer")

    # --- 4 处状态写入必须委托 BacktestTaskService（对齐 producer progress_tracker.py）---
    # 旧实现用 core.database.get_db_cursor 裸 SQL UPDATE backtest_tasks，还写错了
    # 列名（state/error，schema 实为 status/error_message）和取值大小写（COMPLETED vs
    # completed）。这里钉死委托契约，防止回退到裸 SQL。

    def _make_consumer_with_mock_service(self):
        """构造 consumer + mock service，Redis 写入桩掉，返回 (consumer, mock_svc)"""
        from services.backtest_progress_consumer import BacktestProgressConsumer
        consumer = BacktestProgressConsumer()
        mock_svc = MagicMock()
        return consumer, mock_svc

    @pytest.mark.unit
    def test_update_progress_delegates_to_service(self):
        """progress 消息 → update_progress(uuid, progress, current_date)，不传 state（对齐 producer）"""
        consumer, mock_svc = self._make_consumer_with_mock_service()
        with patch("services.backtest_progress_consumer._get_task_service", return_value=mock_svc), \
                patch("services.backtest_progress_consumer.set_backtest_progress", new_callable=AsyncMock):
            asyncio.run(consumer._update_progress(
                task_uuid="uuid-12345678", progress=42.0, current_date="2024-06-01", state="RUNNING"
            ))
        # state 不落库（producer report_progress 也不持久化 state）
        mock_svc.update_progress.assert_called_once_with(
            "uuid-12345678", progress=42.0, current_date="2024-06-01"
        )

    @pytest.mark.unit
    def test_update_completed_delegates_to_service(self):
        """completed 消息 → update_status(uuid, "completed", result=result)"""
        consumer, mock_svc = self._make_consumer_with_mock_service()
        result = {"final_pnl": "100"}
        with patch("services.backtest_progress_consumer._get_task_service", return_value=mock_svc), \
                patch("services.backtest_progress_consumer.set_backtest_progress", new_callable=AsyncMock):
            asyncio.run(consumer._update_completed(task_uuid="uuid-12345678", result=result))
        mock_svc.update_status.assert_called_once_with("uuid-12345678", "completed", result=result)

    @pytest.mark.unit
    def test_update_failed_delegates_to_service(self):
        """failed 消息 → update_status(uuid, "failed", error_message=error)"""
        consumer, mock_svc = self._make_consumer_with_mock_service()
        with patch("services.backtest_progress_consumer._get_task_service", return_value=mock_svc), \
                patch("services.backtest_progress_consumer.set_backtest_progress", new_callable=AsyncMock):
            asyncio.run(consumer._update_failed(task_uuid="uuid-12345678", error="boom"))
        mock_svc.update_status.assert_called_once_with("uuid-12345678", "failed", error_message="boom")

    @pytest.mark.unit
    def test_update_cancelled_uses_stopped_status(self):
        """cancelled 消息 → update_status(uuid, "stopped")（service 不接受 cancelled）"""
        consumer, mock_svc = self._make_consumer_with_mock_service()
        with patch("services.backtest_progress_consumer._get_task_service", return_value=mock_svc), \
                patch("services.backtest_progress_consumer.set_backtest_progress", new_callable=AsyncMock):
            asyncio.run(consumer._update_cancelled(task_uuid="uuid-12345678"))
        mock_svc.update_status.assert_called_once_with("uuid-12345678", "stopped")
