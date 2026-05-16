# See #22: data layer NotificationService facade for notifier module
# Tests verify that the service wraps CRUD calls and returns ServiceResult

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.services.notification_service import NotificationService
from ginkgo.data.services.base_service import ServiceResult


pytestmark = pytest.mark.unit


def _service_with_mock_cruds():
    """Create NotificationService with mocked CRUDs (no database needed)"""
    with patch.object(NotificationService, '__init__', lambda self: None):
        service = NotificationService()
    service.template_crud = MagicMock()
    service.record_crud = MagicMock()
    return service


class TestGetTemplateById:
    """See #22: wraps NotificationTemplateCRUD.get_by_template_id"""

    def test_returns_success_when_found(self):
        service = _service_with_mock_cruds()
        mock_template = MagicMock(name="template")
        service.template_crud.get_by_template_id.return_value = mock_template

        result = service.get_template_by_id("tpl-001")

        assert result.success is True
        assert result.data == mock_template
        service.template_crud.get_by_template_id.assert_called_once_with("tpl-001")

    def test_returns_not_found_when_missing(self):
        service = _service_with_mock_cruds()
        service.template_crud.get_by_template_id.return_value = None

        result = service.get_template_by_id("nonexistent")

        assert result.success is False

    def test_returns_error_on_exception(self):
        service = _service_with_mock_cruds()
        service.template_crud.get_by_template_id.side_effect = Exception("db error")

        result = service.get_template_by_id("tpl-001")

        assert result.success is False
        assert "db error" in result.error


class TestCreateRecord:
    """See #22: wraps NotificationRecordCRUD.add"""

    def test_returns_success_with_uuid(self):
        service = _service_with_mock_cruds()
        service.record_crud.add.return_value = "rec-uuid-001"
        record = MagicMock(name="record")

        result = service.create_record(record)

        assert result.success is True
        assert result.data["uuid"] == "rec-uuid-001"
        service.record_crud.add.assert_called_once_with(record)

    def test_returns_error_when_add_fails(self):
        service = _service_with_mock_cruds()
        service.record_crud.add.return_value = None
        record = MagicMock(name="record")

        result = service.create_record(record)

        assert result.success is False

    def test_returns_error_on_exception(self):
        service = _service_with_mock_cruds()
        service.record_crud.add.side_effect = Exception("write error")

        result = service.create_record(MagicMock())

        assert result.success is False


class TestUpdateRecordStatus:
    """See #22: wraps NotificationRecordCRUD.update_status"""

    def test_returns_success(self):
        service = _service_with_mock_cruds()
        service.record_crud.update_status.return_value = 1

        result = service.update_record_status("msg-001", 2, "delivered")

        assert result.success is True
        service.record_crud.update_status.assert_called_once_with("msg-001", 2, "delivered")

    def test_returns_error_on_exception(self):
        service = _service_with_mock_cruds()
        service.record_crud.update_status.side_effect = Exception("db error")

        result = service.update_record_status("msg-001", 2)

        assert result.success is False


class TestGetRecordsByUser:
    """See #22: wraps NotificationRecordCRUD.get_by_user"""

    def test_returns_records(self):
        service = _service_with_mock_cruds()
        mock_records = [MagicMock(name="rec1"), MagicMock(name="rec2")]
        service.record_crud.get_by_user.return_value = mock_records

        result = service.get_records_by_user("user-001", limit=50, status=1)

        assert result.success is True
        assert result.data == mock_records
        service.record_crud.get_by_user.assert_called_once_with("user-001", limit=50, status=1)

    def test_returns_error_on_exception(self):
        service = _service_with_mock_cruds()
        service.record_crud.get_by_user.side_effect = Exception("db error")

        result = service.get_records_by_user("user-001")

        assert result.success is False


class TestGetRecentFailedRecords:
    """See #22: wraps NotificationRecordCRUD.get_recent_failed"""

    def test_returns_records(self):
        service = _service_with_mock_cruds()
        mock_records = [MagicMock(name="failed_rec")]
        service.record_crud.get_recent_failed.return_value = mock_records

        result = service.get_recent_failed_records(limit=30)

        assert result.success is True
        assert result.data == mock_records
        service.record_crud.get_recent_failed.assert_called_once_with(limit=30)


class TestGetRecordsByTemplate:
    """See #22: wraps NotificationRecordCRUD.get_by_template_id"""

    def test_returns_records(self):
        service = _service_with_mock_cruds()
        mock_records = [MagicMock(name="rec")]
        service.record_crud.get_by_template_id.return_value = mock_records

        result = service.get_records_by_template("tpl-001", limit=20)

        assert result.success is True
        assert result.data == mock_records
        service.record_crud.get_by_template_id.assert_called_once_with("tpl-001", limit=20)
