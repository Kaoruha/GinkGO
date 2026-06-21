# Related: #5952, #5939
# deploy info 命令应把 deployment_id 转发给 service.get_deployment_info，
# 不再误用 portfolio_id 语义。覆盖 deploy_cli.py info 命令薄层。
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client import deploy_cli


def _found(deployment_id="dep-uuid-123"):
    return MagicMock(
        success=True,
        data={
            "deployment_id": deployment_id,
            "source_task_id": "t",
            "source_portfolio_id": "sp",
            "target_portfolio_id": "tp",
            "mode": 1,
            "account_id": "acc",
            "status": "ACTIVE",
            "create_at": None,
        },
    )


class TestDeployCliInfo:

    def test_info_forwards_deployment_id_to_service(self):
        """#5952: info 命令把参数作为 deployment_id 转发给 service"""
        fake_svc = MagicMock()
        fake_svc.get_deployment_info.return_value = _found()
        with patch("ginkgo.trading.containers.trading_container") as mock_container:
            mock_container.deployment_service.return_value = fake_svc
            result = CliRunner().invoke(deploy_cli.app, ["info", "dep-uuid-123"])

        assert result.exit_code == 0
        fake_svc.get_deployment_info.assert_called_once_with("dep-uuid-123")
        assert "dep-uuid-123" in result.stdout

    def test_info_shows_error_when_not_found(self):
        """#5952: 未找到时显示错误并退出码 1"""
        fake_svc = MagicMock()
        fake_svc.get_deployment_info.return_value = MagicMock(
            success=False, error="未找到部署记录"
        )
        with patch("ginkgo.trading.containers.trading_container") as mock_container:
            mock_container.deployment_service.return_value = fake_svc
            result = CliRunner().invoke(deploy_cli.app, ["info", "nonexistent"])

        assert result.exit_code == 1
        assert "未找到" in result.stdout
