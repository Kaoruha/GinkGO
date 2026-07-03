"""
性能: 222MB RSS, 2.03s, 20 tests [FAIL(1)]
Unit tests for notify_cli.py commands: send, template, history, search, channels,
and recipients subcommands (list, add, delete, update, contacts, toggle).

Mock strategy:
  - Patch "ginkgo.data.containers.container" for recipients service access.
  - service_hub.notifier is a property; use patch.object on the module class.
  - Use ServiceResult.success() / ServiceResult.error() for return values.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from ginkgo.client import notify_cli
from ginkgo.data.services.base_service import ServiceResult

import ginkgo.service_hub as service_hub_module


# ============================================================================
# Helpers
# ============================================================================


def _patch_notifier_service(mock_service):
    """Patch service_hub.notifier to return mock_service from notification_service()."""
    # service_hub_module 实际是 ServiceHub 实例（由 ginkgo.__init__ 导出导致）
    # 触发懒加载，让 __getattr__ 缓存到实例上
    _ = service_hub_module.notifier
    mock_notifier = MagicMock()
    mock_notifier.notification_service.return_value = mock_service
    return patch.object(
        service_hub_module, "notifier",
        new_callable=PropertyMock, return_value=mock_notifier,
    )


# ============================================================================
# 1. Help tests (2)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestNotifyCLIHelp:
    """Verify help output for notify commands."""

    def test_root_help_shows_all_commands(self, cli_runner):
        result = cli_runner.invoke(notify_cli.app, ["--help"])
        assert result.exit_code == 0
        for name in ("send", "template", "history", "search", "channels", "recipients"):
            assert name in result.output

    def test_recipients_help_shows_subcommands(self, cli_runner):
        result = cli_runner.invoke(notify_cli.app, ["recipients", "--help"])
        assert result.exit_code == 0
        for name in ("list", "add", "delete", "update", "contacts", "toggle"):
            assert name in result.output


# ============================================================================
# 2. Main commands happy path (6)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestSend:
    """Tests for the 'send' command."""

    def test_send_to_user_sync(self, cli_runner):
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {"message_id": "msg-001"}

        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid-001"
        mock_service.send_to_user.return_value = mock_result

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, ["send", "-u", "Alice", "-c", "Hello World"])

        assert result.exit_code == 0
        assert "Success" in result.output or "success" in result.output.lower()

    def test_send_to_group_sync(self, cli_runner):
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {"message_id": "msg-002"}

        mock_service = MagicMock()
        mock_service._resolve_group_uuids.return_value = {"group-user-1"}
        mock_service.send_to_user.return_value = mock_result

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, ["send", "-g", "traders", "-c", "Trade alert"])

        assert result.exit_code == 0

    def test_send_async_mode(self, cli_runner):
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {"message_id": "msg-003"}

        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid-002"
        mock_service.send_async.return_value = mock_result

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, ["send", "-u", "Bob", "-c", "Async msg", "--async"])

        assert result.exit_code == 0
        assert "Async" in result.output or "Kafka" in result.output

    def test_send_with_title_and_priority(self, cli_runner):
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {"message_id": "msg-004"}

        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid-003"
        mock_service.send_to_user.return_value = mock_result

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, [
                "send", "-u", "Carol", "-t", "Alert", "-c", "High priority", "-p", "3"
            ])

        assert result.exit_code == 0

    def test_send_with_json_fields(self, cli_runner):
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {"message_id": "msg-005"}

        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid-004"
        mock_service.send_to_user.return_value = mock_result

        fields_json = json.dumps([{"name": "Status", "value": "OK", "inline": True}])

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, [
                "send", "-u", "Dave", "-c", "Status update", "-f", fields_json
            ])

        assert result.exit_code == 0

    def test_send_to_user_and_group(self, cli_runner):
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {"message_id": "msg-006"}

        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid-005"
        mock_service._resolve_group_uuids.return_value = {"group-user-2"}
        mock_service.send_to_user.return_value = mock_result

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, [
                "send", "-u", "Eve", "-g", "admins", "-c", "Combined"
            ])

        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestChannels:
    """Tests for the 'channels' command."""

    def test_channels_lists_available(self, cli_runner):
        result = cli_runner.invoke(notify_cli.app, ["channels"])
        assert result.exit_code == 0
        assert "console" in result.output
        assert "discord" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestRecipientsList:
    """Tests for the 'recipients list' command."""

    def test_recipients_list_success(self, cli_runner):
        mock_service = MagicMock()
        mock_service.list_all.return_value = MagicMock(
            is_success=lambda: True,
            data={"recipients": [], "count": 0}
        )

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.notification_recipient_service.return_value = mock_service
            result = cli_runner.invoke(notify_cli.app, ["recipients", "list"])

        assert result.exit_code == 0

    def test_recipients_list_with_data(self, cli_runner):
        mock_service = MagicMock()
        mock_service.list_all.return_value = MagicMock(
            is_success=lambda: True,
            data={
                "recipients": [
                    {
                        "uuid": "recipient-001",
                        "name": "Admin Alerts",
                        "recipient_type": "USER",
                        "user_info": {"username": "admin"},
                        "user_id": "user-001",
                        "is_default": True,
                        "description": "Admin notifications",
                    }
                ],
                "count": 1,
            }
        )

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.notification_recipient_service.return_value = mock_service
            result = cli_runner.invoke(notify_cli.app, ["recipients", "list"])

        assert result.exit_code == 0
        assert "Admin Alerts" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestRecipientsAdd:
    """Tests for the 'recipients add' command."""

    def test_recipients_add_user(self, cli_runner):
        mock_service = MagicMock()
        mock_service.add_recipient.return_value = MagicMock(
            is_success=lambda: True,
            data={"uuid": "new-uuid", "name": "Test", "recipient_type": "USER", "is_default": False}
        )

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.notification_recipient_service.return_value = mock_service
            result = cli_runner.invoke(notify_cli.app, [
                "recipients", "add", "-n", "Test", "-t", "USER", "-u", "user-uuid"
            ])

        assert result.exit_code == 0
        assert "created successfully" in result.output.lower() or "success" in result.output.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestRecipientsDelete:
    """Tests for the 'recipients delete' command."""

    def test_recipients_delete_success(self, cli_runner):
        mock_service = MagicMock()
        mock_service.delete_recipient.return_value = MagicMock(
            is_success=lambda: True,
        )

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.notification_recipient_service.return_value = mock_service
            result = cli_runner.invoke(notify_cli.app, ["recipients", "delete", "recipient-uuid"])

        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


# ============================================================================
# 3. Validation / errors (5)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestNotifyCLIValidation:
    """Validation tests for notify commands."""

    def test_send_missing_user_and_group(self, cli_runner):
        result = cli_runner.invoke(notify_cli.app, ["send", "-c", "Hello"])
        assert result.exit_code != 0

    def test_send_no_valid_users_found(self, cli_runner):
        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = None
        mock_service._resolve_group_uuids.return_value = None

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, ["send", "-u", "nonexistent", "-c", "Hello"])

        assert result.exit_code != 0

    def test_send_invalid_fields_json(self, cli_runner):
        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid"

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, [
                "send", "-u", "Alice", "-c", "Test", "-f", "not-json"
            ])

        assert result.exit_code != 0

    def test_send_fields_not_array(self, cli_runner):
        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid"

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, [
                "send", "-u", "Alice", "-c", "Test", "-f", '{"name": "val"}'
            ])

        assert result.exit_code != 0

    def test_recipients_delete_failure(self, cli_runner):
        mock_service = MagicMock()
        mock_service.delete_recipient.return_value = MagicMock(
            is_success=lambda: False,
            message="Recipient not found"
        )

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.notification_recipient_service.return_value = mock_service
            result = cli_runner.invoke(notify_cli.app, ["recipients", "delete", "bad-uuid"])

        assert result.exit_code != 0


# ============================================================================
# 4. Exception handling (2)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestNotifyCLIExceptions:
    """Exception handling tests for notify commands."""

    def test_send_service_exception(self, cli_runner):
        mock_notifier = MagicMock()
        mock_notifier.notification_service.side_effect = Exception("service down")

        with patch.object(
            service_hub_module, "notifier",
            new_callable=PropertyMock, return_value=mock_notifier,
        ):
            result = cli_runner.invoke(notify_cli.app, ["send", "-u", "Alice", "-c", "Hello"])

        # send_notification catches exceptions and raises typer.Exit(1)
        assert result.exit_code != 0

    def test_recipients_list_exception(self, cli_runner):
        mock_container = MagicMock()
        mock_container.notification_recipient_service.side_effect = Exception("db error")

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(notify_cli.app, ["recipients", "list"])

        # list_recipients catches exceptions and raises typer.Exit(1)
        assert result.exit_code != 0


# ============================================================================
# 5. History command (--page-size alignment, #5188)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestNotifyHistoryPageSize:
    """history 命令支持 --page-size，与其他 list 命令一致（#5188）。"""

    def _patch_notifier(self, mock_service):
        """直接 patch service_hub.notifier 为返回 mock_service 的 mock_notifier。

        注：模块内的 _patch_notifier_service 用 PropertyMock patch 实例属性，
        但 ServiceHub.notifier 是 __getattr__ 懒加载的实例属性（非类级 property），
        PropertyMock 作为实例属性不会触发描述符协议——故此处用普通 MagicMock。
        """
        mock_notifier = MagicMock()
        mock_notifier.notification_service.return_value = mock_service
        return patch.object(service_hub_module, "notifier", mock_notifier)

    def _mock_history_service(self):
        """mock notification_service，get_notification_history 返回成功空列表。"""
        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid-001"
        mock_service.get_notification_history.return_value = MagicMock(
            is_success=lambda: True,
            data={"records": [], "count": 0},
        )
        return mock_service

    def test_history_supports_page_size_option(self, cli_runner):
        """tracer: --page-size 不再报 'No such option'，命令 exit 0。"""
        with self._patch_notifier(self._mock_history_service()):
            result = cli_runner.invoke(
                notify_cli.app, ["history", "-u", "Alice", "--page-size", "5"]
            )
        assert result.exit_code == 0, result.output
        assert "No such option" not in result.output

    def test_page_size_passed_to_service_as_limit(self, cli_runner):
        """--page-size 5 映射到 service.get_notification_history(limit=5)。"""
        mock_service = self._mock_history_service()
        with self._patch_notifier(mock_service):
            cli_runner.invoke(
                notify_cli.app, ["history", "-u", "Alice", "--page-size", "5"]
            )
        mock_service.get_notification_history.assert_called_once()
        call_kwargs = mock_service.get_notification_history.call_args.kwargs
        assert call_kwargs["limit"] == 5

    def test_default_page_size_is_20(self, cli_runner):
        """默认 page-size=20（对齐 backtest_cli/logging_cli 约定）。"""
        mock_service = self._mock_history_service()
        with self._patch_notifier(mock_service):
            cli_runner.invoke(notify_cli.app, ["history", "-u", "Alice"])
        call_kwargs = mock_service.get_notification_history.call_args.kwargs
        assert call_kwargs["limit"] == 20

    def test_history_help_lists_page_size_option(self, cli_runner):
        """history --help 列出 --page-size（验收：用户可见该选项）。"""
        result = cli_runner.invoke(notify_cli.app, ["history", "--help"])
        assert result.exit_code == 0
        assert "--page-size" in result.output

    def test_only_one_history_command_registered(self, cli_runner):
        """验收：commands 中 history 唯一，无重名冲突（#5188 根因）。"""
        history_cmds = [c for c in notify_cli.app.registered_commands if c.name == "history"]
        assert len(history_cmds) == 1, f"expected 1 history command, got {len(history_cmds)}"
