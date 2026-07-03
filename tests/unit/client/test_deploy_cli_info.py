# #5335 deploy info 始终返回未找到部署记录
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import re
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class TestDeployInfoByDeploymentId:
    """#5335 deploy info 应按 deployment_id 查询"""

    @patch("ginkgo.trading.containers.trading_container")
    def test_info_queries_by_deployment_id(self, mock_container):
        """#5335 info <deployment_id> 应调 get_deployment_by_id（非 get_deployment_info 按 portfolio_id）"""
        from ginkgo.client.deploy_cli import app

        mock_svc = MagicMock()
        mock_container.deployment_service.return_value = mock_svc
        r = MagicMock()
        r.success = True
        r.data = {
            "source_task_id": "task-1",
            "source_portfolio_id": "src-port-1234",
            "target_portfolio_id": "tgt-port-5678",
            "mode": 1,
            "account_id": "acc-1",
            "status": "running",
            "create_at": "2025-01-01",
        }
        mock_svc.get_deployment_by_id.return_value = r

        deployment_id = "d90b32ab6b5149f49802754ce0c1f0ef"
        result = runner.invoke(app, ["info", deployment_id])
        assert result.exit_code == 0, f"info 应成功：{result.output}"

        # 关键：按 deployment_id 调 get_deployment_by_id
        mock_svc.get_deployment_by_id.assert_called_once_with(deployment_id)
        # 旧路径 get_deployment_info 不应被调用
        mock_svc.get_deployment_info.assert_not_called()

        plain = _strip_ansi(result.output)
        assert "src-port-1234" in plain or "tgt-port-5678" in plain, (
            f"应显示源/目标 portfolio，实际：{plain!r}"
        )


class TestDeployInfoBySourcePortfolio:
    """#4982 deploy info 按源组合ID 查找部署记录"""

    @patch("ginkgo.trading.containers.trading_container")
    def test_info_falls_back_to_source_portfolio(self, mock_container):
        """#4982 当按 UUID 查无记录时，info<source_id> 应 fallback find_by_source_portfolio 并展示"""
        from ginkgo.client.deploy_cli import app

        mock_svc = MagicMock()
        mock_container.deployment_service.return_value = mock_svc

        # UUID 查无记录（输入是 portfolio_id 而非 deployment UUID）
        not_found = MagicMock()
        not_found.success = False
        not_found.error = "未找到部署记录"
        mock_svc.get_deployment_by_id.return_value = not_found

        # source 查到记录（find_by_source_portfolio 返回 list）
        record = {
            "deployment_id": "d90b32ab6b5149f49802754ce0c1f0ef",
            "source_task_id": "task-1",
            "source_portfolio_id": "9c7a58eb080d47baa98412c38728d9a8",
            "target_portfolio_id": "tgt-port-5678",
            "mode": 1,
            "account_id": "acc-1",
            "status": "running",
            "create_at": "2025-01-01",
        }
        found = MagicMock()
        found.success = True
        found.data = [record]
        mock_svc.find_by_source_portfolio.return_value = found

        source_portfolio_id = "9c7a58eb080d47baa98412c38728d9a8"
        result = runner.invoke(app, ["info", source_portfolio_id])
        assert result.exit_code == 0, f"info 应成功：{result.output}"

        # UUID 路径先尝试（保 #5335 优先级）
        mock_svc.get_deployment_by_id.assert_called_once_with(source_portfolio_id)
        # fallback 到 source
        mock_svc.find_by_source_portfolio.assert_called_once_with(source_portfolio_id)

        plain = _strip_ansi(result.output)
        assert "tgt-port-5678" in plain, f"应展示目标 portfolio，实际：{plain!r}"

    @patch("ginkgo.trading.containers.trading_container")
    def test_info_falls_back_to_target_portfolio(self, mock_container):
        """#4982 当 UUID 与 source 均查无记录时，info<target_id> 应 fallback find_by_target_portfolio"""
        from ginkgo.client.deploy_cli import app

        mock_svc = MagicMock()
        mock_container.deployment_service.return_value = mock_svc

        # UUID 查无
        not_found = MagicMock()
        not_found.success = False
        not_found.error = "未找到部署记录"
        mock_svc.get_deployment_by_id.return_value = not_found

        # source 查无（空列表）
        src_empty = MagicMock()
        src_empty.success = True
        src_empty.data = []
        mock_svc.find_by_source_portfolio.return_value = src_empty

        # target 查到
        record = {
            "deployment_id": "d90b32ab6b5149f49802754ce0c1f0ef",
            "source_task_id": "task-1",
            "source_portfolio_id": "src-port-1234",
            "target_portfolio_id": "aabbccddeeff00112233445566778899",
            "mode": 1,
            "account_id": "acc-1",
            "status": "running",
            "create_at": "2025-01-01",
        }
        tgt_found = MagicMock()
        tgt_found.success = True
        tgt_found.data = [record]
        mock_svc.find_by_target_portfolio.return_value = tgt_found

        target_portfolio_id = "aabbccddeeff00112233445566778899"
        result = runner.invoke(app, ["info", target_portfolio_id])
        assert result.exit_code == 0, f"info 应成功：{result.output}"

        mock_svc.find_by_target_portfolio.assert_called_once_with(target_portfolio_id)

        plain = _strip_ansi(result.output)
        assert "src-port-1234" in plain, f"应展示源 portfolio，实际：{plain!r}"
