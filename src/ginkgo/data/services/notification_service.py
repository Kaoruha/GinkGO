# Upstream: Settings API (通知管理)
# Downstream: NotificationTemplateCRUD, NotificationRecordCRUD
# Role: NotificationService通知管理业务服务，整合模板和历史记录

from typing import Optional, List

from ginkgo.data.crud.notification_template_crud import NotificationTemplateCRUD
from ginkgo.data.crud.notification_record_crud import NotificationRecordCRUD
from ginkgo.data.models import MNotificationTemplate, MNotificationRecord
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import BaseService, ServiceResult


class NotificationService(BaseService):
    """通知管理服务 — 整合 template + record"""

    def __init__(self, template_crud=None, record_crud=None, **kwargs):
        # 透传给 BaseService._initialize_dependencies：注入非 None 时存为 self._template_crud/_record_crud；
        # None 时保持 None，由私有访问器 _get_template_crud/_get_record_crud 延迟创建
        # （兼容无参实例化，避免 eager 建 Mongo 连接）。用私有方法而非 property，保持封装契约——
        # 不向 API 层暴露 CRUD 实例（TestCrudInjectedViaConstructor / CLAUDE.md「Service 禁止暴露 CRUD 实例」）。
        super().__init__(template_crud=template_crud, record_crud=record_crud, **kwargs)

    def _get_template_crud(self):
        """注入优先；无注入时延迟创建，避免 eager 自建绕过容器 override。"""
        if self._template_crud is None:
            self._template_crud = NotificationTemplateCRUD()
        return self._template_crud

    def _get_record_crud(self):
        """注入优先；无注入时延迟创建。"""
        if self._record_crud is None:
            self._record_crud = NotificationRecordCRUD()
        return self._record_crud

    # ==================== 模板查询（notifier facade） ====================

    def get_template_by_id(self, template_id: str) -> ServiceResult:
        """按 template_id 查询模板"""
        try:
            template = self._get_template_crud().get_by_template_id(template_id)
            if template is None:
                return ServiceResult.error("Template not found")
            return ServiceResult.success(template)
        except Exception as e:
            GLOG.ERROR(f"Failed to get template by id: {e}")
            return ServiceResult.error(str(e))

    # ==================== 模板 ====================

    def list_templates(self, **filters) -> ServiceResult:
        """查询通知模板列表"""
        try:
            templates = self._get_template_crud().find(filters=filters)
            return ServiceResult.success(templates)
        except Exception as e:
            GLOG.ERROR(f"Failed to list templates: {e}")
            return ServiceResult.error(str(e))

    def get_template(self, uuid: str) -> ServiceResult:
        """获取单个模板"""
        try:
            templates = self._get_template_crud().find(filters={"uuid": uuid})
            if not templates:
                return ServiceResult.error("Template not found")
            return ServiceResult.success(templates[0])
        except Exception as e:
            GLOG.ERROR(f"Failed to get template: {e}")
            return ServiceResult.error(str(e))

    def template_exists(self, uuid: str) -> bool:
        """检查模板是否存在"""
        templates = self._get_template_crud().find(filters={"uuid": uuid})
        return len(templates) > 0

    def create_template(self, template: MNotificationTemplate) -> ServiceResult:
        """创建通知模板"""
        try:
            result = self._get_template_crud().add(template)
            if not result:
                return ServiceResult.error("Failed to create template")
            return ServiceResult.success({"uuid": result})
        except Exception as e:
            GLOG.ERROR(f"Failed to create template: {e}")
            return ServiceResult.error(str(e))

    def update_template(self, uuid: str, **updates) -> ServiceResult:
        """更新通知模板"""
        try:
            self._get_template_crud().update_by_template_id(uuid, **updates)
            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update template: {e}")
            return ServiceResult.error(str(e))

    def delete_template(self, uuid: str) -> ServiceResult:
        """删除通知模板"""
        try:
            self._get_template_crud().delete(uuid)
            return ServiceResult.success({"deleted": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to delete template: {e}")
            return ServiceResult.error(str(e))

    # ==================== 历史记录（notifier facade） ====================

    def create_record(self, record) -> ServiceResult:
        """创建通知记录"""
        try:
            uuid = self._get_record_crud().add(record)
            if not uuid:
                return ServiceResult.error("Failed to create record")
            return ServiceResult.success({"uuid": uuid})
        except Exception as e:
            GLOG.ERROR(f"Failed to create record: {e}")
            return ServiceResult.error(str(e))

    def update_record_status(self, message_id: str, status: int,
                             error_message: str = None) -> ServiceResult:
        """更新通知记录状态"""
        try:
            self._get_record_crud().update_status(message_id, status, error_message)
            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update record status: {e}")
            return ServiceResult.error(str(e))

    def get_records_by_user(self, user_uuid: str, limit: int = 100,
                            status: int = None) -> ServiceResult:
        """按用户查询通知记录"""
        try:
            records = self._get_record_crud().get_by_user(user_uuid, limit=limit, status=status)
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to get records by user: {e}")
            return ServiceResult.error(str(e))

    def get_recent_failed_records(self, limit: int = 50) -> ServiceResult:
        """查询最近失败的通知记录"""
        try:
            records = self._get_record_crud().get_recent_failed(limit=limit)
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to get recent failed records: {e}")
            return ServiceResult.error(str(e))

    def get_records_by_template(self, template_id: str, limit: int = 100) -> ServiceResult:
        """按模板查询通知记录"""
        try:
            records = self._get_record_crud().get_by_template_id(template_id, limit=limit)
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to get records by template: {e}")
            return ServiceResult.error(str(e))

    # ==================== 历史记录 ====================

    def list_records(self, filters=None, limit: int = 100, offset: int = 0,
                     sort=None) -> ServiceResult:
        """查询通知历史记录"""
        try:
            records = self._get_record_crud().find(
                filters=filters, limit=limit, offset=offset, sort=sort
            )
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to list records: {e}")
            return ServiceResult.error(str(e))
