"""
#4719 deploy list ID 截断修复
- list 输出的 deployment_id / target_portfolio_id 必须完整（不再 [:8]+"..."）
- list 输出的 id 可直接被 info 消费（round-trip 契约的生产者侧）
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import deploy_cli
from ginkgo.data.services.base_service import ServiceResult

# 32 字符 hex UUID（与库内存储格式一致：hex 无横线，见 arch_uuid_storage_no_dashes）
DEPLOY_ID = "4f08f8a1" + "0" * 24  # 32 chars
TGT_PORTFOLIO_ID = "816f2559" + "a" * 24  # 32 chars


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_terminal(monkeypatch):
    """rich Console 非 tty 时读 COLUMNS 环境变量定宽。
    模拟现代宽终端（120+），让 32 字符 UUID 单行完整渲染——这是真实用户体验，
    不被 CliRunner 默认 80 列的 fold artefact 干扰。"""
    monkeypatch.setenv("COLUMNS", "200")


def _compact(s: str) -> str:
    """去所有空白——免疫 rich Table 渲染细节，只验数据完整性"""
    return "".join(s.split())


def _mock_svc_with_list():
    svc = MagicMock()
    svc.list_deployments.return_value = ServiceResult(
        success=True,
        data=[
            {
                "deployment_id": DEPLOY_ID,
                "source_task_id": "bt_task_777",
                "target_portfolio_id": TGT_PORTFOLIO_ID,
                "mode": 1,
                "status": 1,
                "status_name": "DEPLOYED",
                "create_at": "2026-07-03 10:00:00",
            }
        ],
    )
    return svc


class TestDeployListFullId:
    """#4719: list 输出完整 ID，不截断"""

    def test_list_help_shows_page_options(self, cli_runner):
        result = cli_runner.invoke(deploy_cli.app, ["list", "--help"])
        assert result.exit_code == 0
        assert "--page" in result.output
        assert "--page-size" in result.output

    def test_list_passes_page_and_page_size(self, cli_runner):
        svc = _mock_svc_with_list()
        with patch(
            "ginkgo.trading.containers.trading_container.deployment_service",
            return_value=svc,
        ):
            result = cli_runner.invoke(deploy_cli.app, ["list", "--page", "1", "--page-size", "5"])

        assert result.exit_code == 0, result.output
        svc.list_deployments.assert_called_once_with(portfolio_id=None, page=1, page_size=5)

    def test_list_shows_full_deployment_id(self, cli_runner):
        # RED: 当前代码 d["deployment_id"][:8]+"..." 截断，完整 id 不会出现
        with patch(
            "ginkgo.trading.containers.trading_container.deployment_service",
            return_value=_mock_svc_with_list(),
        ):
            result = cli_runner.invoke(deploy_cli.app, ["list"])

        assert result.exit_code == 0, result.output
        # 完整 32 字符 deployment_id 出现在输出中（可复制喂给 deploy info）
        assert DEPLOY_ID in _compact(result.output)
        # 截断标记不应附着在 deployment_id 列（确保不是 [:8]+"..."）
        assert DEPLOY_ID[:8] + "..." not in result.output

    def test_list_shows_full_target_portfolio_id(self, cli_runner):
        with patch(
            "ginkgo.trading.containers.trading_container.deployment_service",
            return_value=_mock_svc_with_list(),
        ):
            result = cli_runner.invoke(deploy_cli.app, ["list"])

        assert result.exit_code == 0, result.output
        assert TGT_PORTFOLIO_ID in _compact(result.output)
        assert TGT_PORTFOLIO_ID[:8] + "..." not in result.output

    def test_list_id_round_trips_to_info(self, cli_runner):
        """list 输出的 deployment_id 可直接传给 info（round-trip 契约）"""
        svc = MagicMock()
        svc.list_deployments.return_value = _mock_svc_with_list().list_deployments.return_value
        svc.get_deployment_by_id.return_value = ServiceResult(
            success=True,
            data={
                "deployment_id": DEPLOY_ID,
                "source_task_id": "bt_task_777",
                "source_portfolio_id": "src_pid",
                "target_portfolio_id": TGT_PORTFOLIO_ID,
                "mode": 1,
                "account_id": None,
                "status": 1,
                "status_name": "DEPLOYED",
                "create_at": "2026-07-03 10:00:00",
            },
        )
        with patch(
            "ginkgo.trading.containers.trading_container.deployment_service",
            return_value=svc,
        ):
            list_result = cli_runner.invoke(deploy_cli.app, ["list"])
            assert list_result.exit_code == 0, list_result.output
            # 从 list 输出取完整 deployment_id（出现在 output 即为可复制）
            assert DEPLOY_ID in _compact(list_result.output)

            info_result = cli_runner.invoke(deploy_cli.app, ["info", DEPLOY_ID])
            assert info_result.exit_code == 0, info_result.output
            svc.get_deployment_by_id.assert_called_once_with(DEPLOY_ID)
