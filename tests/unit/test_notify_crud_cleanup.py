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
