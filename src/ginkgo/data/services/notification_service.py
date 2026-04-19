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

    def __init__(self):
        self.template_crud = NotificationTemplateCRUD()
        self.record_crud = NotificationRecordCRUD()

    # ==================== 模板 ====================

    def list_templates(self, **filters) -> ServiceResult:
        """查询通知模板列表"""
        try:
            templates = self.template_crud.find(filters=filters)
            return ServiceResult.success(templates)
        except Exception as e:
            GLOG.ERROR(f"Failed to list templates: {e}")
            return ServiceResult.error(str(e))

    def get_template(self, uuid: str) -> ServiceResult:
        """获取单个模板"""
        try:
            templates = self.template_crud.find(filters={"uuid": uuid})
            if not templates:
                return ServiceResult.error("Template not found")
            return ServiceResult.success(templates[0])
        except Exception as e:
            GLOG.ERROR(f"Failed to get template: {e}")
            return ServiceResult.error(str(e))

    def template_exists(self, uuid: str) -> bool:
        """检查模板是否存在"""
        templates = self.template_crud.find(filters={"uuid": uuid})
        return len(templates) > 0

    def create_template(self, template: MNotificationTemplate) -> ServiceResult:
        """创建通知模板"""
        try:
            result = self.template_crud.add(template)
            if not result:
                return ServiceResult.error("Failed to create template")
            return ServiceResult.success({"uuid": result})
        except Exception as e:
            GLOG.ERROR(f"Failed to create template: {e}")
            return ServiceResult.error(str(e))

    def update_template(self, uuid: str, **updates) -> ServiceResult:
        """更新通知模板"""
        try:
            self.template_crud.update_by_template_id(uuid, **updates)
            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update template: {e}")
            return ServiceResult.error(str(e))

    def delete_template(self, uuid: str) -> ServiceResult:
        """删除通知模板"""
        try:
            self.template_crud.delete(uuid)
            return ServiceResult.success({"deleted": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to delete template: {e}")
            return ServiceResult.error(str(e))

    # ==================== 历史记录 ====================

    def list_records(self, filters=None, limit: int = 100, offset: int = 0,
                     sort=None) -> ServiceResult:
        """查询通知历史记录"""
        try:
            records = self.record_crud.find(
                filters=filters, limit=limit, offset=offset, sort=sort
            )
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"Failed to list records: {e}")
            return ServiceResult.error(str(e))
