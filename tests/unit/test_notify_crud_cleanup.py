# Issue #22: notify.py CRUD elimination
# Tests that notify.py uses service facades instead of direct CRUD access.

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import RECIPIENT_TYPES
from ginkgo.data.services.base_service import ServiceResult


class TestNotificationRecipientServiceGetUserUuids:
    """Test get_all_recipient_user_uuids() resolves recipients to user UUIDs."""

    def test_returns_deduplicated_user_uuids_from_mixed_recipients(self):
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        user_r = MagicMock()
        user_r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER
        user_r.user_id = "user-1"

        group_r = MagicMock()
        group_r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER_GROUP
        group_r.user_group_id = "group-1"

        mock_recipient_crud = MagicMock()
        mock_recipient_crud.get_active_recipients.return_value = [user_r, group_r]

        mapping = MagicMock()
        mapping.user_uuid = "user-2"
        mock_mapping_crud = MagicMock()
        mock_mapping_crud.find.return_value = [mapping]

        service = NotificationRecipientService(
            recipient_crud=mock_recipient_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=mock_mapping_crud,
        )

        result = service.get_all_recipient_user_uuids()

        assert result.success
        assert set(result.data) == {"user-1", "user-2"}

    def test_returns_empty_list_when_no_recipients(self):
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        mock_crud = MagicMock()
        mock_crud.get_active_recipients.return_value = []

        service = NotificationRecipientService(
            recipient_crud=mock_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )

        result = service.get_all_recipient_user_uuids()

        assert result.success
        assert result.data == []

    def test_deduplicates_across_user_and_group(self):
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        user_r = MagicMock()
        user_r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER
        user_r.user_id = "user-1"

        group_r = MagicMock()
        group_r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER_GROUP
        group_r.user_group_id = "group-1"

        mock_recipient_crud = MagicMock()
        mock_recipient_crud.get_active_recipients.return_value = [user_r, group_r]

        # Group contains the same user as the USER recipient
        mapping = MagicMock()
        mapping.user_uuid = "user-1"
        mock_mapping_crud = MagicMock()
        mock_mapping_crud.find.return_value = [mapping]

        service = NotificationRecipientService(
            recipient_crud=mock_recipient_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=mock_mapping_crud,
        )

        result = service.get_all_recipient_user_uuids()

        assert result.success
        assert result.data == ["user-1"]


class TestNotificationRecipientServiceCrudIsPrivate:
    """CLAUDE.md: Service 层禁止直接暴露 CRUD 实例"""

    def test_recipient_crud_not_public(self):
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService
        service = NotificationRecipientService(
            recipient_crud=MagicMock(),
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )
        assert not hasattr(service, "recipient_crud")

    def test_user_contact_crud_not_public(self):
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService
        service = NotificationRecipientService(
            recipient_crud=MagicMock(),
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )
        assert not hasattr(service, "user_contact_crud")

    def test_user_group_mapping_crud_not_public(self):
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService
        service = NotificationRecipientService(
            recipient_crud=MagicMock(),
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )
        assert not hasattr(service, "user_group_mapping_crud")


class TestGetAllRecipientUserUuidsUsesGroupServiceFacade:
    """Test get_all_recipient_user_uuids() resolves groups via user_group_service, not CRUD."""

    def test_calls_user_group_service_not_crud(self):
        """USER_GROUP recipients must be resolved via user_group_service facade."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        group_r = MagicMock()
        group_r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER_GROUP
        group_r.user_group_id = "group-1"

        mock_recipient_crud = MagicMock()
        mock_recipient_crud.get_active_recipients.return_value = [group_r]

        mock_group_service = MagicMock()
        mock_group_service.get_group_member_uuids.return_value = ServiceResult.success(["user-2"])

        service = NotificationRecipientService(
            recipient_crud=mock_recipient_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
            user_group_service=mock_group_service,
        )

        result = service.get_all_recipient_user_uuids()

        assert result.success
        assert result.data == ["user-2"]
        mock_group_service.get_group_member_uuids.assert_called_once_with("group-1")

    def test_handles_group_service_failure_gracefully(self):
        """If user_group_service fails, skip that group's members."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        group_r = MagicMock()
        group_r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER_GROUP
        group_r.user_group_id = "group-1"

        mock_recipient_crud = MagicMock()
        mock_recipient_crud.get_active_recipients.return_value = [group_r]

        mock_group_service = MagicMock()
        mock_group_service.get_group_member_uuids.return_value = ServiceResult.error("not found")

        service = NotificationRecipientService(
            recipient_crud=mock_recipient_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
            user_group_service=mock_group_service,
        )

        result = service.get_all_recipient_user_uuids()

        assert result.success
        assert result.data == []


class TestGetNotificationServiceUsesContainer:
    """Test _get_notification_service() uses notifier container, not manual CRUD assembly."""

    @patch("ginkgo.notifier.core.notify._notification_service_instance", None)
    def test_calls_container_notification_service(self):
        with patch("ginkgo.notifier.containers.container") as mock_container:
            mock_service = MagicMock()
            mock_container.notification_service.return_value = mock_service

            from ginkgo.notifier.core.notify import _get_notification_service

            # Reset singleton
            import ginkgo.notifier.core.notify as notify_mod
            notify_mod._notification_service_instance = None

            result = _get_notification_service()

            mock_container.notification_service.assert_called_once()
            assert result == mock_service


class TestNotifyUsesServiceFacade:
    """Test notify() resolves recipients through service, not direct CRUD."""

    @patch("ginkgo.notifier.core.notify._notification_service_instance", None)
    @patch("ginkgo.notifier.core.notify._get_recipient_user_uuids")
    @patch("ginkgo.notifier.core.notify._get_notification_service")
    def test_notify_async_calls_send_async_per_user(self, mock_get_svc, mock_get_uuids):
        mock_service = MagicMock()
        mock_service.send_async.return_value = MagicMock(is_success=True)
        mock_get_svc.return_value = mock_service
        mock_get_uuids.return_value = ["user-1", "user-2"]

        from ginkgo.notifier.core.notify import notify

        result = notify("test message", async_mode=True)

        assert result is True
        assert mock_service.send_async.call_count == 2

    @patch("ginkgo.notifier.core.notify._notification_service_instance", None)
    @patch("ginkgo.notifier.core.notify._get_recipient_user_uuids")
    @patch("ginkgo.notifier.core.notify._get_notification_service")
    def test_notify_returns_false_when_no_recipients(self, mock_get_svc, mock_get_uuids):
        mock_get_svc.return_value = MagicMock()
        mock_get_uuids.return_value = []

        from ginkgo.notifier.core.notify import notify

        result = notify("test message")

        assert result is False


class TestNotifyWithFieldsUsesServiceFacade:
    """Test notify_with_fields() resolves recipients through service."""

    @patch("ginkgo.notifier.core.notify._notification_service_instance", None)
    @patch("ginkgo.notifier.core.notify._get_recipient_user_uuids")
    @patch("ginkgo.notifier.core.notify._get_notification_service")
    def test_sync_mode_sends_via_service(self, mock_get_svc, mock_get_uuids):
        mock_service = MagicMock()
        mock_service.user_service.get_active_contacts.return_value = ServiceResult.success([])
        mock_get_svc.return_value = mock_service
        mock_get_uuids.return_value = []

        from ginkgo.notifier.core.notify import notify_with_fields

        result = notify_with_fields(
            content="test", fields=[{"name": "k", "value": "v"}], async_mode=False
        )

        assert result is False  # No contacts found


# Issue #3429: list_all() undefined variables
class TestListAllReturnsRecipients:
    """Test list_all() returns recipients from CRUD."""

    def test_returns_recipients_with_basic_fields(self):
        """list_all() should return recipient list with uuid, name, type."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        r = MagicMock()
        r.uuid = "r-1"
        r.name = "alice"
        r.user_id = "u-1"
        r.user_group_id = None
        r.is_default = False
        r.description = "desc"
        r.create_at = None
        r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER

        mock_crud = MagicMock()
        mock_crud.find.return_value = [r]

        service = NotificationRecipientService(
            recipient_crud=mock_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )

        result = service.list_all()

        assert result.success
        assert result.data["count"] == 1
        assert result.data["recipients"][0]["uuid"] == "r-1"
        assert result.data["recipients"][0]["name"] == "alice"
        assert result.data["recipients"][0]["recipient_type"] == "USER"


class TestListAllReturnsEmpty:
    """Test list_all() returns empty list when no recipients."""

    def test_returns_empty_when_no_recipients(self):
        """list_all() with no recipients should return success with empty list."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        mock_crud = MagicMock()
        mock_crud.find.return_value = []

        service = NotificationRecipientService(
            recipient_crud=mock_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )

        result = service.list_all()

        assert result.success
        assert result.data["count"] == 0
        assert result.data["recipients"] == []


class TestListAllFilterByType:
    """Test list_all() filters by recipient_type."""

    def test_passes_recipient_type_to_crud_filter(self):
        """list_all(recipient_type=USER) should include recipient_type in filters."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        mock_crud = MagicMock()
        mock_crud.find.return_value = []

        service = NotificationRecipientService(
            recipient_crud=mock_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )

        service.list_all(recipient_type=RECIPIENT_TYPES.USER)

        call_filters = mock_crud.find.call_args[1]["filters"]
        assert call_filters["recipient_type"] == RECIPIENT_TYPES.USER.value


class TestListAllFilterByDefault:
    """Test list_all() filters by is_default."""

    def test_passes_is_default_to_crud_filter(self):
        """list_all(is_default=True) should include is_default in filters."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        mock_crud = MagicMock()
        mock_crud.find.return_value = []

        service = NotificationRecipientService(
            recipient_crud=mock_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )

        service.list_all(is_default=True)

        call_filters = mock_crud.find.call_args[1]["filters"]
        assert call_filters["is_default"] is True


class TestListAllUserEnrichment:
    """Test list_all() enriches USER recipients with user_info."""

    def test_user_recipient_includes_user_info(self):
        """USER type recipient should include user_info from user CRUD."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        r = MagicMock()
        r.uuid = "r-1"
        r.name = "alice"
        r.user_id = "u-1"
        r.user_group_id = None
        r.is_default = False
        r.description = ""
        r.create_at = None
        r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER

        mock_crud = MagicMock()
        mock_crud.find.return_value = [r]

        mock_user = MagicMock()
        mock_user.uuid = "u-1"
        mock_user.username = "alice_w"
        mock_user.display_name = "Alice Wang"

        mock_user_crud = MagicMock()
        mock_user_crud.find.return_value = [mock_user]

        service = NotificationRecipientService(
            recipient_crud=mock_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.user_crud.return_value = mock_user_crud
            result = service.list_all()

        assert result.success
        item = result.data["recipients"][0]
        assert "user_info" in item
        assert item["user_info"]["username"] == "alice_w"


class TestListAllGroupEnrichment:
    """Test list_all() enriches USER_GROUP recipients with user_group_info."""

    def test_group_recipient_includes_group_info(self):
        """USER_GROUP type recipient should include user_group_info from group CRUD."""
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        r = MagicMock()
        r.uuid = "r-2"
        r.name = "ops-team"
        r.user_id = None
        r.user_group_id = "g-1"
        r.is_default = True
        r.description = ""
        r.create_at = None
        r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER_GROUP

        mock_crud = MagicMock()
        mock_crud.find.return_value = [r]

        mock_group = MagicMock()
        mock_group.uuid = "g-1"
        mock_group.name = "Operations"

        mock_group_crud = MagicMock()
        mock_group_crud.find.return_value = [mock_group]

        service = NotificationRecipientService(
            recipient_crud=mock_crud,
            user_contact_crud=MagicMock(),
            user_group_mapping_crud=MagicMock(),
        )

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.user_group_crud.return_value = mock_group_crud
            result = service.list_all()

        assert result.success
        item = result.data["recipients"][0]
        assert "user_group_info" in item
        assert item["user_group_info"]["name"] == "Operations"
