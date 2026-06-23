"""
#6285 deploy CLI 输出断言测试
- info: 状态显示枚举名 status_name（非裸 int）
- deploy: --source-task 透传到 svc.deploy
"""
import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import deploy_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


def _mock_svc():
    svc = MagicMock()
    svc.get_deployment_info.return_value = ServiceResult(
        success=True,
        data={
            "source_task_id": "bt_task_123",
            "source_portfolio_id": "src_pid",
            "target_portfolio_id": "tgt_pid",
            "mode": 1,
            "account_id": None,
            "status": 1,
            "status_name": "DEPLOYED",
            "create_at": "2026-06-22 10:00:00",
        },
    )
    svc.deploy.return_value = ServiceResult(
        success=True, data={"portfolio_id": "tgt_pid", "deployment_id": "d1"}
    )
    return svc


class TestDeployInfoStatusDisplay:
    """#6285: info 状态显示枚举名"""

    def test_info_shows_status_name_not_raw_int(self, cli_runner):
        with patch(
            "ginkgo.trading.containers.trading_container.deployment_service",
            return_value=_mock_svc(),
        ):
            result = cli_runner.invoke(deploy_cli.app, ["info", "tgt_pid"])

        assert result.exit_code == 0, result.output
        # 枚举名出现，裸 int "1" 不作为状态值独立出现
        assert "DEPLOYED" in result.output
        # 源回测任务回显
        assert "bt_task_123" in result.output


class TestDeploySourceTaskPassthrough:
    """#6285: deploy --source-task 透传到 svc.deploy"""

    def test_deploy_passes_source_task_id(self, cli_runner):
        with patch(
            "ginkgo.trading.containers.trading_container.deployment_service",
            return_value=_mock_svc(),
        ) as factory:
            result = cli_runner.invoke(
                deploy_cli.app,
                ["deploy", "src_pid", "--mode", "paper", "--source-task", "bt_task_456"],
            )

        assert result.exit_code == 0, result.output
        svc = factory.return_value
        svc.deploy.assert_called_once()
        _, kwargs = svc.deploy.call_args
        assert kwargs.get("source_task_id") == "bt_task_456"
