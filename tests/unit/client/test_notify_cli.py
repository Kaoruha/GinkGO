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
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from ginkgo.client import notify_cli
from ginkgo.data.services.base_service import ServiceResult

import ginkgo.service_hub as service_hub_module


# ============================================================================
# Helpers
# ============================================================================


@contextmanager
def _patch_notifier_service(mock_service):
    """Patch service_hub.notifier to return mock_service from notification_service()."""
    mock_notifier = MagicMock()
    mock_notifier.notification_service.return_value = mock_service
    service_hub_module.register_override("notifier", mock_notifier)
    try:
        yield
    finally:
        service_hub_module.clear_override("notifier")


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

    def test_history_help_does_not_advertise_no_arg_mode(self, cli_runner):
        result = cli_runner.invoke(notify_cli.app, ["history", "--help"])

        assert result.exit_code == 0
        assert "Show recent 50 records" not in result.output
        assert 'history --user "Alice"' in result.output


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
class TestNotifyHistoryCommand:
    """``history`` 命令的回归测试（#6086 AC3）。

    两个 PR 各自实现了 ``history`` 命令，Typer 同名 ``@app.command`` 静默覆盖
    （后者生效），导致 #5968 的字段名修复进了**死代码**分支，active 版用错
    字段名（timestamp/channel 单数/title）重现 bug。本类固化两件事：
    1. 全仓只注册一个 ``history`` 命令（结构层抓双注册）；
    2. active ``history`` 渲染模型真实字段 ``create_at``/``channels``(复数)，
       不读模型不存的 ``title``。
    """

    def test_only_one_history_command_registered(self):
        """Typer 同名 ``@app.command`` 静默覆盖；必须只剩一个 ``history``。"""
        history_cmds = [
            c for c in notify_cli.app.registered_commands
            if getattr(c, "name", None) == "history"
        ]
        assert len(history_cmds) == 1, (
            f"history 命令应只注册一次，实际 {len(history_cmds)} 次"
            "（Typer 同名静默覆盖会让字段修复进死代码分支）"
        )

    def test_history_renders_create_at_and_channels_not_title(self, cli_runner, monkeypatch):
        """active history 读模型真实字段 create_at/channels(复数)，不读 title。

        回归锚点：active 版曾读 ``timestamp``/``channel``(单数)/``title``，
        而 MNotificationRecord 只存 ``create_at``/``channels``(复数)/无 title，
        导致时间恒 N/A、渠道恒空、Title 列恒空。
        """
        # CliRunner 默认 80 列，Rich 会把 Time 列压缩成 "2026-07-0…"，
        # 完整时间串不出现（假阴性）。patch console 宽度避免压缩。
        monkeypatch.setattr(notify_cli.console, "width", 200)

        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = {
            "count": 1,
            "records": [
                {
                    "message_id": "msg-001",
                    "content": "hello world",
                    "channels": ["email", "webhook"],
                    "status": 1,
                    "create_at": "2026-07-05T10:00:00",
                }
            ],
        }

        mock_service = MagicMock()
        mock_service._resolve_user_uuid.return_value = "user-uuid-1"
        mock_service.get_notification_history.return_value = mock_result

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(
                notify_cli.app, ["history", "--user", "alice"]
            )

        assert result.exit_code == 0, result.output
        # create_at 渲染为可读时间（非 N/A）
        assert "2026-07-05 10:00" in result.output, (
            "必须渲染 create_at 字段，不能读不存在的 timestamp"
        )
        # channels(复数) 至少渲染一个渠道（非空）
        assert "email" in result.output, "必须渲染 channels(复数) 列表元素"
        # 模型不存 title → 不应有 Title 列头
        assert "Title" not in result.output, "模型无 title 字段，不应渲染 Title 列"


@pytest.mark.unit
@pytest.mark.cli
class TestNotifySearchCommand:
    """``search`` 命令的用户字段漂移回归（#6086 AC4）。

    user_service.list_users 返回 ``username``/``display_name``（无 ``name``），
    但 search 命令读 ``u.get("name")`` → 过滤恒空（搜不到）+ Name 列恒空。
    本类固化：搜索能命中 display_name/username，且 Name 列渲染 display_name。
    """

    def test_search_matches_user_by_display_name(self, cli_runner, monkeypatch):
        """search 关键词应命中 display_name（非读不存在的 name 字段过滤）。"""
        monkeypatch.setattr(notify_cli.console, "width", 200)

        mock_user_service = MagicMock()
        mock_user_service.list_users.return_value = MagicMock(
            success=True,
            data={
                "users": [
                    {
                        "uuid": "u-1",
                        "username": "alice_co",
                        "display_name": "Alice Cohen",
                        "is_active": True,
                        "user_type": "USER",
                    }
                ]
            },
        )
        mock_group_service = MagicMock()
        mock_group_service.list_groups.return_value = MagicMock(
            success=True, data={"groups": []}
        )

        mock_container = MagicMock()
        mock_container.user_service.return_value = mock_user_service
        mock_container.user_group_service.return_value = mock_group_service

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(notify_cli.app, ["search", "alice"])

        assert result.exit_code == 0, result.output
        assert "Alice Cohen" in result.output, (
            "search 应按 display_name 命中并渲染（原 u.get('name') 恒空→搜不到+Name 列空）"
        )

    def test_search_falls_back_to_username_when_no_display_name(self, cli_runner, monkeypatch):
        """display_name 缺失时回退 username，保证可搜可显示。"""
        monkeypatch.setattr(notify_cli.console, "width", 200)

        mock_user_service = MagicMock()
        mock_user_service.list_users.return_value = MagicMock(
            success=True,
            data={
                "users": [
                    {
                        "uuid": "u-2",
                        "username": "bob_trader",
                        "display_name": "",  # 无 display_name
                        "is_active": True,
                        "user_type": "USER",
                    }
                ]
            },
        )
        mock_group_service = MagicMock()
        mock_group_service.list_groups.return_value = MagicMock(
            success=True, data={"groups": []}
        )

        mock_container = MagicMock()
        mock_container.user_service.return_value = mock_user_service
        mock_container.user_group_service.return_value = mock_group_service

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(notify_cli.app, ["search", "bob"])

        assert result.exit_code == 0, result.output
        assert "bob_trader" in result.output, (
            "display_name 空时应回退 username 渲染/过滤"
        )


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

    def test_history_without_user_does_not_print_raw_exit_code(self, cli_runner):
        mock_service = MagicMock()

        with _patch_notifier_service(mock_service):
            result = cli_runner.invoke(notify_cli.app, ["history"])

        assert result.exit_code != 0
        assert "Currently only --user filtering is supported" in result.output
        assert "Error: 1" not in result.output


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

        service_hub_module.register_override("notifier", mock_notifier)
        try:
            result = cli_runner.invoke(notify_cli.app, ["send", "-u", "Alice", "-c", "Hello"])
        finally:
            service_hub_module.clear_override("notifier")

        # send_notification catches exceptions and raises typer.Exit(1)
        assert result.exit_code != 0

    def test_recipients_list_exception(self, cli_runner):
        mock_container = MagicMock()
        mock_container.notification_recipient_service.side_effect = Exception("db error")

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(notify_cli.app, ["recipients", "list"])

        # list_recipients catches exceptions and raises typer.Exit(1)
        assert result.exit_code != 0
