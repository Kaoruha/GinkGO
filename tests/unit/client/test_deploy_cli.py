# Related: #5939
# deploy info <deployment_id> 透传 service.get_deployment_info(deployment_id)
import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ginkgo.client import deploy_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.mark.unit
@pytest.mark.cli
class TestDeployInfo:
    """#5939: deploy info 按 deployment_id 查, 非 portfolio_id。

    根因: info 命令参数按 portfolio_id 查(get_by_target_portfolio), 但 deploy 返回的主标识是
    deployment_id(部署记录 uuid)。用户传 deployment_id 查不到。修复: info 改按 deployment_id 查。
    """

    def _info_data(self, deployment_id="d1"):
        return {
            "deployment_id": deployment_id,
            "source_task_id": None,
            "target_portfolio_id": "tgt-1",
            "source_portfolio_id": "src-1",
            "mode": 1,
            "account_id": None,
            "status": 2,
            "create_at": None,
        }

    def test_info_routes_deployment_id_to_service(self, cli_runner):
        """info <deployment_id> 透传到 service.get_deployment_info(deployment_id)。"""
        svc = MagicMock()
        svc.get_deployment_info.return_value = ServiceResult(
            success=True, data=self._info_data("d-abc"))
        with patch("ginkgo.trading.containers.trading_container") as mc:
            mc.deployment_service.return_value = svc
            r = cli_runner.invoke(deploy_cli.app, ["info", "d-abc"])

        assert r.exit_code == 0, r.output
        svc.get_deployment_info.assert_called_once_with("d-abc")

    def test_info_not_found_exits_nonzero(self, cli_runner):
        """deployment_id 查不到 → 非零退出 + 错误提示。"""
        svc = MagicMock()
        svc.get_deployment_info.return_value = ServiceResult(
            success=False, error="未找到部署记录")
        with patch("ginkgo.trading.containers.trading_container") as mc:
            mc.deployment_service.return_value = svc
            r = cli_runner.invoke(deploy_cli.app, ["info", "nope"])

        assert r.exit_code != 0
        assert "未找到" in r.output

    def test_info_help_says_deployment_id(self, cli_runner):
        """info --help 参数说明应明示 deployment_id(非 portfolio_id)。"""
        r = cli_runner.invoke(deploy_cli.app, ["info", "--help"])
        assert r.exit_code == 0
        # 参数语义对齐 deployment_id
        assert "deployment" in r.output.lower() or "部署记录" in r.output
