"""
Tests for NotificationRecipientService.list_all() CRUD elimination.

Verifies that list_all() uses UserService/UserGroupService facades
instead of direct CRUD access for user/group enrichment.

Issue: #3443
"""

import pytest
from unittest.mock import MagicMock

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import RECIPIENT_TYPES
from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService


def _make_recipient(user_id=None, user_group_id=None):
    """Create a mock MNotificationRecipient."""
    r = MagicMock()
    r.uuid = "r-1"
    r.name = "test-recipient"
    r.user_id = user_id
    r.user_group_id = user_group_id
    r.is_default = True
    r.description = "desc"
    r.create_at = None
    r.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER
    return r


def _make_service():
    """Create NotificationRecipientService with mocked dependencies."""
    recipient_crud = MagicMock()
    user_contact_crud = MagicMock()
    user_group_mapping_crud = MagicMock()

    user_service = MagicMock()
    group_service = MagicMock()

    service = NotificationRecipientService(
        recipient_crud=recipient_crud,
        user_contact_crud=user_contact_crud,
        user_group_mapping_crud=user_group_mapping_crud,
        user_group_service=group_service,
        user_service=user_service,
    )
    return service


class TestListAllUserServiceEnrichment:
    """list_all() should use UserService.get_user() for user enrichment."""

    def test_calls_user_service_not_crud(self):
        service = _make_service()
        recipient = _make_recipient(user_id="user-1")
        service._recipient_crud.find.return_value = [recipient]

        mock_user = MagicMock()
        mock_user.uuid = "user-1"
        mock_user.username = "alice"
        mock_user.display_name = "Alice"
        service.user_service.get_user.return_value = ServiceResult.success(
            data=mock_user, message="ok"
        )

        result = service.list_all()
        assert result.success is True
        service.user_service.get_user.assert_called_once_with("user-1")

    def test_user_info_included_in_result(self):
        service = _make_service()
        recipient = _make_recipient(user_id="user-1")
        service._recipient_crud.find.return_value = [recipient]

        mock_user = MagicMock()
        mock_user.uuid = "user-1"
        mock_user.username = "alice"
        mock_user.display_name = "Alice"
        service.user_service.get_user.return_value = ServiceResult.success(
            data=mock_user, message="ok"
        )

        result = service.list_all()
        assert result.success is True
        recipients = result.data["recipients"]
        assert recipients[0]["user_info"]["username"] == "alice"


class TestListAllGroupServiceEnrichment:
    """list_all() should use UserGroupService for group enrichment."""

    def test_calls_group_service_for_group_enrichment(self):
        service = _make_service()
        recipient = _make_recipient(user_group_id="group-1")
        recipient.get_recipient_type_enum.return_value = RECIPIENT_TYPES.USER_GROUP
        service._recipient_crud.find.return_value = [recipient]

        mock_group = MagicMock()
        mock_group.uuid = "group-1"
        mock_group.name = "traders"
        service.user_group_service.get_group_by_uuid.return_value = ServiceResult.success(
            data=mock_group, message="ok"
        )

        result = service.list_all()
        assert result.success is True
        service.user_group_service.get_group_by_uuid.assert_called_once_with("group-1")
        recipients = result.data["recipients"]
        assert recipients[0]["user_group_info"]["name"] == "traders"


class TestListAllNoDirectCRUDAccess:
    """list_all() must not import or access data.containers."""

    def test_no_container_import(self):
        """list_all should not import from ginkgo.data.containers."""
        import inspect
        from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

        source = inspect.getsource(NotificationRecipientService.list_all)
        assert "from ginkgo.data.containers" not in source
        assert "container.user_crud" not in source
        assert "container.user_group_crud" not in source
