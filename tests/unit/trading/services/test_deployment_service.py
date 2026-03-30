# TDD Red阶段：测试用例尚未实现
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest
from unittest.mock import MagicMock, patch
from ginkgo.enums import PORTFOLIO_MODE_TYPES


class TestDeploymentServiceDeploy:
    def test_deploy_rejects_non_completed_backtest(self):
        """回测未完成时应拒绝部署"""
        from ginkgo.trading.services.deployment_service import DeploymentService

        mock_task_service = MagicMock()
        mock_task_service.get_by_run_id.return_value = MagicMock(
            success=True,
            data={"status": "running"}
        )

        svc = DeploymentService.__new__(DeploymentService)
        svc._task_service = mock_task_service

        result = svc.deploy(
            backtest_task_id="task_001",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
        )
        assert not result.success
        assert "completed" in result.error.lower() or "完成" in result.error

    def test_deploy_rejects_live_without_account(self):
        """实盘模式缺少account_id应拒绝"""
        from ginkgo.trading.services.deployment_service import DeploymentService

        mock_task_service = MagicMock()
        mock_task_service.get_by_run_id.return_value = MagicMock(
            success=True,
            data={"status": "completed", "portfolio_id": "p1"}
        )

        svc = DeploymentService.__new__(DeploymentService)
        svc._task_service = mock_task_service

        result = svc.deploy(
            backtest_task_id="task_001",
            mode=PORTFOLIO_MODE_TYPES.LIVE,
            account_id=None,
        )
        assert not result.success
        assert "account" in result.error.lower() or "账号" in result.error

    def test_deploy_paper_calls_clone_and_copy(self):
        """纸上交易部署应调用clone、copy_mapping、create_portfolio"""
        from ginkgo.trading.services.deployment_service import DeploymentService

        mock_task_service = MagicMock()
        mock_task_service.get_by_run_id.return_value = MagicMock(
            success=True,
            data={"status": "completed", "portfolio_id": "p1", "name": "BT-001"}
        )

        mock_portfolio_service = MagicMock()
        mock_portfolio_service.add.return_value = MagicMock(
            is_success=lambda: True,
            success=True,
            data={"uuid": "p_new"}
        )

        mock_mapping_service = MagicMock()
        mock_mapping_service.get_portfolio_mappings.return_value = MagicMock(
            success=True,
            data=[]
        )

        mock_file_service = MagicMock()
        mock_deployment_crud = MagicMock()

        svc = DeploymentService.__new__(DeploymentService)
        svc._task_service = mock_task_service
        svc._portfolio_service = mock_portfolio_service
        svc._mapping_service = mock_mapping_service
        svc._file_service = mock_file_service
        svc._deployment_crud = mock_deployment_crud

        result = svc.deploy(
            backtest_task_id="task_001",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            name="Paper-001",
        )
        assert result.success
        mock_portfolio_service.add.assert_called_once()
        call_kwargs = mock_portfolio_service.add.call_args
        assert call_kwargs[1]["mode"] == PORTFOLIO_MODE_TYPES.PAPER
