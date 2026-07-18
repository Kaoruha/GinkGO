# TDD for NotificationManagementService dependency injection (#5568).
# Upstream: tests/unit/data/services/test_notification_service_di.py
# Downstream: src/ginkgo/data/services/notification_service.py
# Role: 验证 NotificationManagementService 接入 BaseService DI 生命周期（构造器注入 + lazy 兜底）

from unittest.mock import MagicMock

from ginkgo.data.services.base_service import BaseService
from ginkgo.data.services.notification_service import NotificationManagementService


def test_injected_crud_used_and_extends_base():
    """Slice 1 (tracer bullet): 注入的 template_crud 被方法使用 + 继承 BaseService。

    当前 __init__ 用 `or NotificationTemplateCRUD()` eager 自建 + 不继承 BaseService，
    绕过容器 override 与 DI 生命周期。
    """
    mock_crud = MagicMock()
    mock_crud.get_by_template_id.return_value = None
    svc = NotificationManagementService(template_crud=mock_crud)
    assert isinstance(svc, BaseService)
    svc.get_template_by_id("tpl_1")
    mock_crud.get_by_template_id.assert_called_once_with("tpl_1")


def test_no_arg_does_not_eagerly_create_crud(monkeypatch):
    """Slice 2: 无参实例化不 eager 建 CRUD；首次访问 property 才延迟创建。

    防止每次 new 都重复建 Mongo client（原 `or XxxCRUD()` 在 __init__ 立即建）。
    """
    created = []

    class FakeCRUD:
        def __init__(self):
            created.append(self)

    monkeypatch.setattr(
        "ginkgo.data.services.notification_service.NotificationTemplateCRUD",
        FakeCRUD,
    )
    svc = NotificationManagementService()
    assert created == []  # __init__ 不 eager 建
    _ = svc.template_crud  # 首次访问 property 才建
    assert len(created) == 1


def test_no_arg_method_lazily_creates_crud(monkeypatch):
    """Slice 3: 无参实例化的方法调用经 lazy property 建 CRUD，不崩。

    方法体须走 property 访问器（self.template_crud）而非 self._template_crud（None）。
    """
    class FakeCRUD:
        def get_by_template_id(self, template_id):
            return {"id": template_id}

    monkeypatch.setattr(
        "ginkgo.data.services.notification_service.NotificationTemplateCRUD",
        FakeCRUD,
    )
    svc = NotificationManagementService()
    result = svc.get_template_by_id("tpl_1")
    assert result.success
    assert result.data == {"id": "tpl_1"}
