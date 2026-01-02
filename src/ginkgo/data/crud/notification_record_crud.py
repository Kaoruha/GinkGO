# Upstream: NotificationService (通知业务逻辑)、NotificationChannel (通知渠道)
# Downstream: BaseMongoCRUD (继承提供MongoDB CRUD基础能力)、MNotificationRecord (通知记录模型)
# Role: NotificationRecordCRUD通知记录CRUD操作封装通知发送记录的增删改查和按message_id/user_uuid查询支持通知记录管理功能


"""
Notification Record CRUD

通知发送记录 CRUD 操作层，提供通知记录的增删改查功能。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ginkgo.data.crud.base_mongo_crud import BaseMongoCRUD
from ginkgo.data.models.model_notification_record import MNotificationRecord
from ginkgo.libs import GLOG


class NotificationRecordCRUD(BaseMongoCRUD[MNotificationRecord]):
    """
    通知记录 CRUD 操作

    提供通知记录的基本 CRUD 操作和业务辅助方法。
    """

    # 必须重写的类属性
    _model_class = MNotificationRecord

    def __init__(self, model_class=None, driver=None):
        """
        初始化 NotificationRecordCRUD

        Args:
            model_class: MNotificationRecord 类 (可选，默认使用 _model_class)
            driver: GinkgoMongo 驱动实例 (可选，从全局获取)
        """
        from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
        from ginkgo.libs import GCONF

        # 使用默认值
        if model_class is None:
            model_class = self._model_class
        if driver is None:
            driver = GinkgoMongo(
                user=GCONF.MONGOUSER,
                pwd=GCONF.MONGOPWD,
                host=GCONF.MONGOHOST,
                port=int(GCONF.MONGOPORT),
                db=GCONF.MONGODB,
            )

        super().__init__(model_class=model_class, driver=driver)

    def add(self, record: MNotificationRecord) -> Optional[str]:
        """
        添加通知记录

        Args:
            record: MNotificationRecord 实例

        Returns:
            str: 记录的 UUID，失败返回 None
        """
        try:
            return super().add(record)
        except Exception as e:
            GLOG.ERROR(f"Error adding notification record: {e}")
            return None

    def get_by_message_id(self, message_id: str) -> Optional[MNotificationRecord]:
        """
        根据 message_id 查询记录

        Args:
            message_id: 消息唯一标识符

        Returns:
            MNotificationRecord: 记录实例，不存在返回 None
        """
        try:
            collection = self._get_collection()

            doc = collection.find_one({
                "message_id": message_id,
                "is_del": False
            })

            if doc:
                return self._doc_to_model(doc)

            return None

        except Exception as e:
            GLOG.ERROR(f"Error getting record by message_id '{message_id}': {e}")
            return None

    def get_by_user(
        self,
        user_uuid: str,
        limit: int = 100,
        status: Optional[int] = None
    ) -> List[MNotificationRecord]:
        """
        根据用户 UUID 查询记录

        Args:
            user_uuid: 用户 UUID
            limit: 最大返回数量
            status: 可选的状态过滤

        Returns:
            List[MNotificationRecord]: 记录列表
        """
        try:
            collection = self._get_collection()

            query = {
                "user_uuid": user_uuid,
                "is_del": False
            }

            if status is not None:
                query["status"] = status

            docs = collection.find(query).sort("create_at", -1).limit(limit).to_list(None)

            return [self._doc_to_model(doc) for doc in docs]

        except Exception as e:
            GLOG.ERROR(f"Error getting records by user '{user_uuid}': {e}")
            return []

    def get_by_template_id(self, template_id: str, limit: int = 100) -> List[MNotificationRecord]:
        """
        根据模板 ID 查询记录

        Args:
            template_id: 模板 ID
            limit: 最大返回数量

        Returns:
            List[MNotificationRecord]: 记录列表
        """
        try:
            collection = self._get_collection()

            docs = collection.find({
                "template_id": template_id,
                "is_del": False
            }).sort("create_at", -1).limit(limit).to_list(None)

            return [self._doc_to_model(doc) for doc in docs]

        except Exception as e:
            GLOG.ERROR(f"Error getting records by template_id '{template_id}': {e}")
            return []

    def get_by_status(
        self,
        status: int,
        limit: int = 100
    ) -> List[MNotificationRecord]:
        """
        根据状态查询记录

        Args:
            status: 发送状态
            limit: 最大返回数量

        Returns:
            List[MNotificationRecord]: 记录列表
        """
        try:
            collection = self._get_collection()

            docs = collection.find({
                "status": status,
                "is_del": False
            }).sort("create_at", -1).limit(limit).to_list(None)

            return [self._doc_to_model(doc) for doc in docs]

        except Exception as e:
            GLOG.ERROR(f"Error getting records by status: {e}")
            return []

    def get_recent_failed(self, limit: int = 50) -> List[MNotificationRecord]:
        """
        获取最近的失败记录

        Args:
            limit: 最大返回数量

        Returns:
            List[MNotificationRecord]: 失败记录列表
        """
        try:
            from ginkgo.enums import NOTIFICATION_STATUS_TYPES

            return self.get_by_status(
                status=NOTIFICATION_STATUS_TYPES.FAILED.value,
                limit=limit
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting recent failed records: {e}")
            return []

    def update_status(
        self,
        message_id: str,
        status: int,
        error_message: Optional[str] = None
    ) -> int:
        """
        更新记录状态

        Args:
            message_id: 消息 ID
            status: 新状态
            error_message: 错误信息（可选）

        Returns:
            int: 更新的文档数量
        """
        try:
            collection = self._get_collection()

            update_data = {
                "status": status,
                "update_at": datetime.now()
            }

            if error_message is not None:
                update_data["error_message"] = error_message

            if status == 1:  # SENT
                update_data["sent_at"] = datetime.now()

            result = collection.update_many(
                {"message_id": message_id, "is_del": False},
                {"$set": update_data}
            )

            return result.modified_count

        except Exception as e:
            GLOG.ERROR(f"Error updating status for message_id '{message_id}': {e}")
            return 0

    def get_old_records(
        self,
        days_old: int = 7,
        limit: int = 1000
    ) -> List[MNotificationRecord]:
        """
        获取旧记录（用于清理）

        Args:
            days_old: 天数阈值
            limit: 最大返回数量

        Returns:
            List[MNotificationRecord]: 旧记录列表
        """
        try:
            collection = self._get_collection()

            cutoff_date = datetime.now() - timedelta(days=days_old)

            docs = collection.find({
                "create_at": {"$lt": cutoff_date},
                "is_del": False
            }).limit(limit).to_list(None)

            return [self._doc_to_model(doc) for doc in docs]

        except Exception as e:
            GLOG.ERROR(f"Error getting old records: {e}")
            return []

    def _doc_to_model(self, doc: Dict[str, Any]) -> MNotificationRecord:
        """
        将 MongoDB 文档转换为模型实例

        Args:
            doc: MongoDB 文档

        Returns:
            MNotificationRecord: 模型实例
        """
        return MNotificationRecord.from_mongo(doc)
