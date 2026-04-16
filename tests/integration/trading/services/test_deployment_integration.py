import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from datetime import datetime


class TestDeploymentIntegration:
    """
    集成测试：端到端部署流程

    前置条件：ginkgo system config set --debug on
    需要数据库连接
    """

    def test_deploy_paper_rejects_nonexistent_task(self):
        """部署不存在的回测任务应返回错误"""
        from ginkgo.data.containers import container
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        deployment_service = container.deployment_service()
        result = deployment_service.deploy(
            backtest_task_id="nonexistent_task_id",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
        )

        assert not result.success
        assert result.error

    def test_list_deployments_returns_list(self):
        """列出部署记录应返回列表"""
        from ginkgo.data.containers import container

        deployment_service = container.deployment_service()
        result = deployment_service.list_deployments()

        assert result.success
        assert isinstance(result.data, list)
