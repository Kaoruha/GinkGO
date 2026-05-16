"""
Tests for NotificationDeliveryService.send_to_group / send_template_to_group
group_uuid support.

Verifies that these methods accept group_uuid as the primary identifier,
with group_name as a convenience wrapper that resolves to uuid.

Issue: #3445
"""

import pytest
from unittest.mock import MagicMock, patch, call

from ginkgo.data.services.base_service import ServiceResult


def _make_service():
    """Create NotificationDeliveryService with mocked dependencies."""
    from ginkgo.notifier.core.webhook_dispatcher import WebhookDispatcher
    with patch.object(WebhookDispatcher, "__init__", lambda self, svc: None):
        from ginkgo.notifier.core.notification_service import NotificationDeliveryService

        mock_notification_svc = MagicMock()
        mock_user_svc = MagicMock()
        mock_group_svc = MagicMock()

        # Default: group found by uuid
        mock_group = MagicMock()
        mock_group.uuid = "group-uuid-1"
        mock_group.name = "traders"
        mock_group_svc.get_group_by_uuid.return_value = ServiceResult.success(
            data=mock_group, message="ok"
        )
        mock_group_svc.get_group_by_name.return_value = ServiceResult.success(
            data=mock_group, message="ok"
        )
        mock_group_svc.get_group_member_uuids.return_value = ServiceResult.success(
            data=["user-1", "user-2"], message="ok"
        )

        service = NotificationDeliveryService(
            notification_service=mock_notification_svc,
            template_engine=MagicMock(),
            user_service=mock_user_svc,
            user_group_service=mock_group_svc,
        )

    # Mock send_to_user to avoid deep recursion
    service.send_to_user = MagicMock(return_value=ServiceResult.success(data={"message_id": "msg-1"}))
    service.send_template_to_user = MagicMock(return_value=ServiceResult.success(data={"message_id": "msg-1"}))

    return service


class TestSendToGroupByUuid:
    """send_to_group(group_uuid=...) sends to all group members."""

    def test_resolves_uuid_and_sends_to_members(self):
        service = _make_service()
        result = service.send_to_group(
            content="hello",
            group_uuid="group-uuid-1",
        )

        assert result.success is True
        # Should resolve group by uuid
        service.user_group_service.get_group_by_uuid.assert_called_once_with("group-uuid-1")
        # Should get members
        service.user_group_service.get_group_member_uuids.assert_called_once()
        # Should send to each member
        assert service.send_to_user.call_count == 2


class TestSendToGroupByName:
    """send_to_group(group_name=...) resolves name→uuid then sends."""

    def test_resolves_name_to_uuid_and_sends(self):
        service = _make_service()
        result = service.send_to_group(
            content="hello",
            group_name="traders",
        )

        assert result.success is True
        # Should resolve group by name
        service.user_group_service.get_group_by_name.assert_called_once_with("traders")
        # Should then get members and send
        service.user_group_service.get_group_member_uuids.assert_called_once()
        assert service.send_to_user.call_count == 2


class TestSendTemplateToGroupByUuid:
    """send_template_to_group(group_uuid=...) sends template to group members."""

    def test_resolves_uuid_and_sends_template(self):
        service = _make_service()
        result = service.send_template_to_group(
            template_id="trading_signal",
            context={"symbol": "AAPL"},
            group_uuid="group-uuid-1",
        )

        assert result.success is True
        service.user_group_service.get_group_by_uuid.assert_called_once_with("group-uuid-1")
        service.user_group_service.get_group_member_uuids.assert_called_once()
        assert service.send_template_to_user.call_count == 2


class TestSendTemplateToGroupByName:
    """send_template_to_group(group_name=...) resolves name→uuid then sends template."""

    def test_resolves_name_to_uuid_and_sends_template(self):
        service = _make_service()
        result = service.send_template_to_group(
            template_id="trading_signal",
            context={"symbol": "AAPL"},
            group_name="traders",
        )

        assert result.success is True
        service.user_group_service.get_group_by_name.assert_called_once_with("traders")
        service.user_group_service.get_group_member_uuids.assert_called_once()
        assert service.send_template_to_user.call_count == 2


class TestGroupNotFound:
    """When group cannot be resolved, returns error."""

    def test_send_to_group_uuid_not_found(self):
        service = _make_service()
        service.user_group_service.get_group_by_uuid.return_value = ServiceResult.error("not found")

        result = service.send_to_group(content="hello", group_uuid="missing")
        assert result.success is False

    def test_send_to_group_name_not_found(self):
        service = _make_service()
        service.user_group_service.get_group_by_name.return_value = ServiceResult.error("not found")

        result = service.send_to_group(content="hello", group_name="missing")
        assert result.success is False

    def test_send_template_to_group_uuid_not_found(self):
        service = _make_service()
        service.user_group_service.get_group_by_uuid.return_value = ServiceResult.error("not found")

        result = service.send_template_to_group(
            template_id="tpl", context={}, group_uuid="missing"
        )
        assert result.success is False

    def test_send_template_to_group_name_not_found(self):
        service = _make_service()
        service.user_group_service.get_group_by_name.return_value = ServiceResult.error("not found")

        result = service.send_template_to_group(
            template_id="tpl", context={}, group_name="missing"
        )
        assert result.success is False


class TestNeitherUuidNorName:
    """When neither group_uuid nor group_name is provided, returns error."""

    def test_send_to_group_requires_identifier(self):
        service = _make_service()
        result = service.send_to_group(content="hello")
        assert result.success is False

    def test_send_template_to_group_requires_identifier(self):
        service = _make_service()
        result = service.send_template_to_group(template_id="tpl", context={})
        assert result.success is False
