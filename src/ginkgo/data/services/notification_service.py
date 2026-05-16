# Upstream: Settings API (通知管理)
# Downstream: NotificationTemplateCRUD, NotificationRecordCRUD
# Role: NotificationService通知管理业务服务，整合模板和历史记录

from typing import Optional, List

from ginkgo.data.crud.notification_template_crud import NotificationTemplateCRUD
from ginkgo.data.crud.notification_record_crud import NotificationRecordCRUD
from ginkgo.data.models import MNotificationTemplate, MNotificationRecord
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult


class NotificationService:
    """通知管理服务 — 整合 template + record"""

    def __init__(self, template_crud=None, record_crud=None):
        self._template_crud = template_crud or NotificationTemplateCRUD()
        self._record_crud = record_crud or NotificationRecordCRUD()

    # ==================== 模板查询（notifier facade） ====================

    def get_template_by_id(self, template_id: str) -> ServiceResult:
        """按 template_id 查询模板"""
        try:
            template = self._template_crud.get_by_template_id(template_id)
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
            templates = self._template_crud.find(filters=filters)
            return ServiceResult.success(templates)
        except Exception as e:
            GLOG.ERROR(f"Failed to list templates: {e}")
            return ServiceResult.error(str(e))

    def get_template(self, uuid: str) -> ServiceResult:
        """获取单个模板"""
        try:
            templates = self._template_crud.find(filters={"uuid": uuid})
            if not templates:
                return ServiceResult.error("Template not found")
            return ServiceResult.success(templates[0])
        except Exception as e:
            GLOG.ERROR(f"Failed to get template: {e}")
            return ServiceResult.error(str(e))

    def template_exists(self, uuid: str) -> bool:
        """检查模板是否存在"""
        templates = self._template_crud.find(filters={"uuid": uuid})
        return len(templates) > 0

    def create_template(self, template: MNotificationTemplate) -> ServiceResult:
        """创建通知模板"""
        try:
            result = self._template_crud.add(template)
            if not result:
                return ServiceResult.error("Failed to create template")
            return ServiceResult.success({"uuid": result})
        except Exception as e:
            GLOG.ERROR(f"Failed to create template: {e}")
            return ServiceResult.error(str(e))

    def update_template(self, uuid: str, **updates) -> ServiceResult:
        """更新通知模板"""
        try:
            self._template_crud.update_by_template_id(uuid, **updates)
            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update template: {e}")
            return ServiceResult.error(str(e))

    def delete_template(self, uuid: str) -> ServiceResult:
        """删除通知模板"""
        try:
            self._template_crud.delete(uuid)
            return ServiceResult.success({"deleted": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to delete template: {e}")
            return ServiceResult.error(str(e))

    # ==================== 历史记录（notifier facade） ====================

    def create_record(self, record) -> ServiceResult:
        """创建通知记录"""
        try:
            uuid = self._record_crud.add(record)
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
            self._record_crud.update_status(message_id, status, error_message)
            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update record status: {e}")
            return ServiceResult.error(str(e))

    def get_records_by_user(self, user_uuid: str, limit: int = 100,
                            status: int = None) -> ServiceResult:
        """按用户查询通知记录"""
        try:
            records = self._record_crud.get_by_user(user_uuid, limit=limit, status=status)
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to get records by user: {e}")
            return ServiceResult.error(str(e))

    def get_recent_failed_records(self, limit: int = 50) -> ServiceResult:
        """查询最近失败的通知记录"""
        try:
            records = self._record_crud.get_recent_failed(limit=limit)
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to get recent failed records: {e}")
            return ServiceResult.error(str(e))

    def get_records_by_template(self, template_id: str, limit: int = 100) -> ServiceResult:
        """按模板查询通知记录"""
        try:
            records = self._record_crud.get_by_template_id(template_id, limit=limit)
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to get records by template: {e}")
            return ServiceResult.error(str(e))

    # ==================== 历史记录 ====================

    def list_records(self, filters=None, limit: int = 100, offset: int = 0,
                     sort=None) -> ServiceResult:
        """查询通知历史记录"""
        try:
            records = self._record_crud.find(
                filters=filters, limit=limit, offset=offset, sort=sort
            )
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to list records: {e}")
            return ServiceResult.error(str(e))
