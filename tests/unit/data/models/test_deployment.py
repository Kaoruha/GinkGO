# TDD Red阶段：测试用例尚未实现
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest
from ginkgo.data.models.model_deployment import MDeployment, DEPLOYMENT_STATUS


class TestMDeployment:
    def test_create_deployment_with_required_fields(self):
        d = MDeployment(
            source_task_id="task_001",
            target_portfolio_id="portfolio_new",
            source_portfolio_id="portfolio_old",
            mode=1,  # PAPER
            status=DEPLOYMENT_STATUS.PENDING,
        )
        assert d.source_task_id == "task_001"
        assert d.target_portfolio_id == "portfolio_new"
        assert d.source_portfolio_id == "portfolio_old"
        assert d.mode == 1
        assert d.status == DEPLOYMENT_STATUS.PENDING
        assert d.account_id is None

    def test_create_deployment_live_with_account(self):
        d = MDeployment(
            source_task_id="task_001",
            target_portfolio_id="portfolio_new",
            source_portfolio_id="portfolio_old",
            mode=2,  # LIVE
            account_id="account_001",
            status=DEPLOYMENT_STATUS.PENDING,
        )
        assert d.account_id == "account_001"
        assert d.mode == 2

    def test_deployment_status_enum(self):
        assert DEPLOYMENT_STATUS.PENDING == 0
        assert DEPLOYMENT_STATUS.DEPLOYED == 1
        assert DEPLOYMENT_STATUS.FAILED == 2
        assert DEPLOYMENT_STATUS.STOPPED == 3
