# See #22: data layer NotificationManagementService facade for notifier module
# Tests verify CRUD is injected via constructor and facade methods work through public API

import pytest
from unittest.mock import MagicMock

from ginkgo.data.services.notification_service import NotificationManagementService
from ginkgo.data.services.base_service import ServiceResult


pytestmark = pytest.mark.unit


def _service(template_crud=None, record_crud=None):
    """Create NotificationManagementService with constructor-injected mocks"""
    return NotificationManagementService(
        template_crud=template_crud or MagicMock(),
        record_crud=record_crud or MagicMock(),
    )


class TestCrudInjectedViaConstructor:
    """CRUD instances must be injected, not exposed as public attributes"""

    def test_template_crud_not_publicly_accessible(self):
        service = _service()
        assert not hasattr(service, "template_crud")

    def test_record_crud_not_publicly_accessible(self):
        service = _service()
        assert not hasattr(service, "record_crud")


class TestGetTemplateById:
    """See #22: wraps NotificationTemplateCRUD.get_by_template_id"""

    def test_returns_success_when_found(self):
        mock_template = MagicMock(name="template")
        mock_crud = MagicMock()
        mock_crud.get_by_template_id.return_value = mock_template

        service = _service(template_crud=mock_crud)
        result = service.get_template_by_id("tpl-001")

        assert result.success is True
        assert result.data == mock_template

    def test_returns_not_found_when_missing(self):
        mock_crud = MagicMock()
        mock_crud.get_by_template_id.return_value = None

        service = _service(template_crud=mock_crud)
        result = service.get_template_by_id("nonexistent")

        assert result.success is False

    def test_returns_error_on_exception(self):
        mock_crud = MagicMock()
        mock_crud.get_by_template_id.side_effect = Exception("db error")

        service = _service(template_crud=mock_crud)
        result = service.get_template_by_id("tpl-001")

        assert result.success is False
        assert "db error" in result.error


class TestCreateRecord:
    """See #22: wraps NotificationRecordCRUD.add"""

    def test_returns_success_with_uuid(self):
        record = MagicMock(name="record")
        mock_crud = MagicMock()
        mock_crud.add.return_value = "rec-uuid-001"

        service = _service(record_crud=mock_crud)
        result = service.create_record(record)

        assert result.success is True
        assert result.data["uuid"] == "rec-uuid-001"

    def test_returns_error_when_add_fails(self):
        mock_crud = MagicMock()
        mock_crud.add.return_value = None

        service = _service(record_crud=mock_crud)
        result = service.create_record(MagicMock())

        assert result.success is False

    def test_returns_error_on_exception(self):
        mock_crud = MagicMock()
        mock_crud.add.side_effect = Exception("write error")

        service = _service(record_crud=mock_crud)
        result = service.create_record(MagicMock())

        assert result.success is False


class TestUpdateRecordStatus:
    """See #22: wraps NotificationRecordCRUD.update_status"""

    def test_returns_success(self):
        mock_crud = MagicMock()
        mock_crud.update_status.return_value = 1

        service = _service(record_crud=mock_crud)
        result = service.update_record_status("msg-001", 2, "delivered")

        assert result.success is True

    def test_returns_error_on_exception(self):
        mock_crud = MagicMock()
        mock_crud.update_status.side_effect = Exception("db error")

        service = _service(record_crud=mock_crud)
        result = service.update_record_status("msg-001", 2)

        assert result.success is False


class TestGetRecordsByUser:
    """See #22: wraps NotificationRecordCRUD.get_by_user"""

    def test_returns_records(self):
        mock_records = [MagicMock(name="rec1"), MagicMock(name="rec2")]
        mock_crud = MagicMock()
        mock_crud.get_by_user.return_value = mock_records

        service = _service(record_crud=mock_crud)
        result = service.get_records_by_user("user-001", limit=50, status=1)

        assert result.success is True
        assert result.data == mock_records

    def test_returns_error_on_exception(self):
        mock_crud = MagicMock()
        mock_crud.get_by_user.side_effect = Exception("db error")

        service = _service(record_crud=mock_crud)
        result = service.get_records_by_user("user-001")

        assert result.success is False


class TestGetRecentFailedRecords:
    """See #22: wraps NotificationRecordCRUD.get_recent_failed"""

    def test_returns_records(self):
        mock_records = [MagicMock(name="failed_rec")]
        mock_crud = MagicMock()
        mock_crud.get_recent_failed.return_value = mock_records

        service = _service(record_crud=mock_crud)
        result = service.get_recent_failed_records(limit=30)

        assert result.success is True
        assert result.data == mock_records


class TestGetRecordsByTemplate:
    """See #22: wraps NotificationRecordCRUD.get_by_template_id"""

    def test_returns_records(self):
        mock_records = [MagicMock(name="rec")]
        mock_crud = MagicMock()
        mock_crud.get_by_template_id.return_value = mock_records

        service = _service(record_crud=mock_crud)
        result = service.get_records_by_template("tpl-001", limit=20)

        assert result.success is True
        assert result.data == mock_records
