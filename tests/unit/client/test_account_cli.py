"""#6284: 补齐实盘账户 CLI (account create/list/get)

背景: LiveAccountService/CRUD 已就绪（create_account/get_user_accounts/get_account_by_uuid），
但无 CLI 入口 —— 用户无法通过 ginkgo 命令行创建实盘账户，导致 `deploy --mode live --account <uuid>`
的 uuid 无从获得（#6281 已暴露此断点）。

收敛: 新建 account_cli.py，走 `data_container.live_account_service()`，在 main.py 注册 `account` 命令组。
验收: 创建的 uuid 能被 deploy 接受; list/get 不回显 api_key/api_secret/passphrase 明文。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client.account_cli import app

runner = CliRunner()


class TestAccountCreate:
    """ginkgo account create 直调 live_account_service.create_account"""

    @pytest.mark.unit
    def test_create_account_calls_service_and_prints_uuid(self):
        """account create 应调 create_account 并回显 account_uuid（deploy 需此 uuid）

        RED: account_cli 尚不存在 → ImportError。
        """
        mock_svc = MagicMock()
        # service 返回纯 dict（非 ServiceResult），用真实 dict 避免 MagicMock auto-truthy 陷阱
        mock_svc.create_account.return_value = {
            "success": True,
            "data": {"account_uuid": "abc123def456"},
            "message": "created",
            "error": "",
        }

        with patch("ginkgo.data.containers.container.live_account_service", return_value=mock_svc):
            result = runner.invoke(app, [
                "create", "user-001",
                "--exchange", "okx",
                "--name", "MyOKX",
                "--api-key", "k1",
                "--api-secret", "s1",
                "--passphrase", "p1",
            ])

        assert result.exit_code == 0, \
            f"CLI 崩溃 (exit={result.exit_code}): {result.output}\nexc={result.exception}"
        mock_svc.create_account.assert_called_once()
        _, kwargs = mock_svc.create_account.call_args
        assert kwargs["user_id"] == "user-001"
        assert kwargs["exchange"] == "okx"
        assert kwargs["name"] == "MyOKX"
        assert kwargs["api_key"] == "k1"
        assert kwargs["api_secret"] == "s1"
        assert kwargs["passphrase"] == "p1"
        # 回显 account_uuid（deploy --account 需要它）
        assert "abc123def456" in result.output


class TestAccountList:
    """ginkgo account list 直调 live_account_service.get_user_accounts"""

    @pytest.mark.unit
    def test_list_accounts_calls_service_and_no_credentials(self):
        """account list 应调 get_user_accounts 且输出不含 api_secret/api_key 明文（to_dict 已脱敏）

        RED: list 命令不存在 → 命令组无法解析。
        """
        mock_svc = MagicMock()
        mock_svc.get_user_accounts.return_value = {
            "success": True,
            "data": {
                "accounts": [
                    {"uuid": "acc-aaa", "name": "MyOKX", "exchange": "okx",
                     "environment": "testnet", "status": "active"},
                ],
                "total": 1, "page": 1, "page_size": 20, "total_pages": 1,
            },
        }

        with patch("ginkgo.data.containers.container.live_account_service", return_value=mock_svc):
            result = runner.invoke(app, ["list", "user-001"])

        assert result.exit_code == 0, \
            f"CLI 崩溃 (exit={result.exit_code}): {result.output}\nexc={result.exception}"
        mock_svc.get_user_accounts.assert_called_once()
        assert mock_svc.get_user_accounts.call_args.kwargs["user_id"] == "user-001"
        # 输出含账号名（可读性），不含凭据明文（安全验收）
        assert "MyOKX" in result.output
        assert "api_secret" not in result.output.lower()
        assert "api_key" not in result.output.lower()


class TestAccountGet:
    """ginkgo account get 直调 live_account_service.get_account_by_uuid"""

    @pytest.mark.unit
    def test_get_account_calls_service_and_no_credentials(self):
        """account get 应调 get_account_by_uuid 且输出不含 api_secret/api_key 明文"""
        mock_svc = MagicMock()
        mock_svc.get_account_by_uuid.return_value = {
            "success": True,
            "data": {
                "uuid": "acc-aaa", "name": "MyOKX", "exchange": "okx",
                "environment": "testnet", "status": "active",
            },
        }

        with patch("ginkgo.data.containers.container.live_account_service", return_value=mock_svc):
            result = runner.invoke(app, ["get", "acc-aaa"])

        assert result.exit_code == 0, \
            f"CLI 崩溃 (exit={result.exit_code}): {result.output}\nexc={result.exception}"
        mock_svc.get_account_by_uuid.assert_called_once_with("acc-aaa")
        assert "MyOKX" in result.output
        assert "acc-aaa" in result.output
        assert "api_secret" not in result.output.lower()
        assert "api_key" not in result.output.lower()
