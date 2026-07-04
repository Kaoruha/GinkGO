"""
#3867: BacktestTaskService 新增方法的单元测试

覆盖：
- get_latest_completed: 获取 portfolio 最新已完成回测的绩效指标
- count_by_portfolio: 统计 portfolio 的回测次数
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


class TestGetLatestCompleted:
    """BacktestTaskService.get_latest_completed 测试"""

    @pytest.fixture
    def service(self):
        crud = MagicMock()
        return BacktestTaskService(crud_repo=crud)

    @pytest.mark.unit
    def test_returns_metrics_from_latest_completed_task(self, service):
        """最新已完成回测返回绩效指标"""
        task = MagicMock()
        task.annual_return = 0.15
        task.sharpe_ratio = 1.2
        task.max_drawdown = 0.08
        task.win_rate = 0.6
        task.create_at = datetime(2026, 5, 1, 12, 0, 0)
        service._crud_repo.find.return_value = [task]

        result = service.get_latest_completed(portfolio_id="pf-001")

        assert result.is_success()
        assert result.data["annual_return"] == 0.15
        assert result.data["sharpe_ratio"] == 1.2
        assert result.data["max_drawdown"] == 0.08
        assert result.data["win_rate"] == 0.6
        assert result.data["last_backtest_date"] == "2026-05-01T12:00:00"

    @pytest.mark.unit
    def test_returns_empty_when_no_completed_tasks(self, service):
        """无已完成回测返回空数据"""
        service._crud_repo.find.return_value = []

        result = service.get_latest_completed(portfolio_id="pf-001")

        assert result.is_success()
        assert result.data == {}

    @pytest.mark.unit
    def test_handles_null_metric_fields(self, service):
        """None 指标字段默认为 0"""
        task = MagicMock()
        task.annual_return = None
        task.sharpe_ratio = None
        task.max_drawdown = None
        task.win_rate = None
        task.create_at = datetime(2026, 5, 1)
        service._crud_repo.find.return_value = [task]

        result = service.get_latest_completed(portfolio_id="pf-001")

        assert result.is_success()
        assert result.data["annual_return"] == 0.0
        assert result.data["sharpe_ratio"] == 0.0

    @pytest.mark.unit
    def test_returns_error_on_exception(self, service):
        """CRUD 异常返回错误结果"""
        service._crud_repo.find.side_effect = Exception("DB error")

        result = service.get_latest_completed(portfolio_id="pf-001")

        assert result.is_success() is False
        assert "DB error" in result.error


class TestGetLatestCompletedTaskId:
    """BacktestTaskService.get_latest_completed_task_id 测试 (#5196: deploy 溯源用)"""

    @pytest.fixture
    def service(self):
        crud = MagicMock()
        return BacktestTaskService(crud_repo=crud)

    @pytest.mark.unit
    def test_returns_task_id_from_latest_completed(self, service):
        """有 completed 回测时返回最新一条的 task_id"""
        task = MagicMock()
        task.task_id = "bt_task_abc123"
        service._crud_repo.find.return_value = [task]

        result = service.get_latest_completed_task_id(portfolio_id="pf-001")

        assert result.is_success()
        assert result.data == "bt_task_abc123"
        # 验证查询契约: portfolio_id + status=completed + 按 create_at 倒序取 1 条
        _, kwargs = service._crud_repo.find.call_args
        assert kwargs["filters"] == {"portfolio_id": "pf-001", "status": "completed", "is_del": False}
        assert kwargs["order_by"] == "create_at"
        assert kwargs["desc_order"] is True
        assert kwargs["page_size"] == 1

    @pytest.mark.unit
    def test_returns_none_when_no_completed_tasks(self, service):
        """无 completed 回测时返回 None(供 deploy 判断留空)"""
        service._crud_repo.find.return_value = []

        result = service.get_latest_completed_task_id(portfolio_id="pf-001")

        assert result.is_success()
        assert result.data is None

    @pytest.mark.unit
    def test_returns_error_on_exception(self, service):
        """CRUD 异常返回错误结果(不阻断 deploy, 调用方按 falsy 留空)"""
        service._crud_repo.find.side_effect = Exception("DB error")

        result = service.get_latest_completed_task_id(portfolio_id="pf-001")

        assert result.is_success() is False
        assert "DB error" in result.error


class TestCountByPortfolio:
    """BacktestTaskService.count_by_portfolio 测试"""

    @pytest.fixture
    def service(self):
        crud = MagicMock()
        return BacktestTaskService(crud_repo=crud)

    @pytest.mark.unit
    def test_returns_count(self, service):
        """返回 portfolio 的回测次数"""
        service._crud_repo.count.return_value = 5

        result = service.count_by_portfolio(portfolio_id="pf-001")

        assert result.is_success()
        assert result.data == 5

    @pytest.mark.unit
    def test_returns_zero_when_none(self, service):
        """count 返回 None 时默认为 0"""
        service._crud_repo.count.return_value = None

        result = service.count_by_portfolio(portfolio_id="pf-001")

        assert result.is_success()
        assert result.data == 0

    @pytest.mark.unit
    def test_returns_error_on_exception(self, service):
        """CRUD 异常返回错误结果"""
        service._crud_repo.count.side_effect = Exception("DB error")

        result = service.count_by_portfolio(portfolio_id="pf-001")

        assert result.is_success() is False
        assert "DB error" in result.error
