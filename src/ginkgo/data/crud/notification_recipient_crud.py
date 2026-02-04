# Upstream: NotificationRecipientService (通知接收人业务逻辑)
# Downstream: BaseCRUD (继承提供MySQL CRUD基础能力)、MNotificationRecipient (通知接收人模型)
# Role: NotificationRecipientCRUD通知接收人CRUD操作封装全局接收人的增删改查和按类型查询支持系统级通知接收人管理功能


"""
Notification Recipient CRUD

通知接收人 CRUD 操作层，提供全局通知接收人的基本 CRUD 操作。
MySQL 实现，通过引用用户/用户组实现。
"""

from typing import List, Optional
from sqlalchemy import and_, or_

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_notification_recipient import MNotificationRecipient
from ginkgo.libs import GLOG
from ginkgo.enums import RECIPIENT_TYPES


class NotificationRecipientCRUD(BaseCRUD[MNotificationRecipient]):
    """
    通知接收人 CRUD 操作

    提供全局通知接收人的基本 CRUD 操作和业务辅助方法。
    """

    # 必须重写的类属性
    _model_class = MNotificationRecipient

    def __init__(self):
        """
        初始化 NotificationRecipientCRUD
        """
        super().__init__(MNotificationRecipient)

    def get_by_name(self, name: str) -> Optional[MNotificationRecipient]:
        """
        根据名称查询接收人

        Args:
            name: 接收人名称

        Returns:
            MNotificationRecipient: 接收人实例，不存在返回 None
        """
        try:
            results = self.find(
                filters={"name": name, "is_del": False},
                page_size=1,
                page=0,
                as_dataframe=False
            )
            return results[0] if results else None

        except Exception as e:
            GLOG.ERROR(f"Error getting recipient by name '{name}': {e}")
            return None

    def get_by_type(
        self,
        recipient_type: RECIPIENT_TYPES
    ) -> List[MNotificationRecipient]:
        """
        根据接收人类型查询

        Args:
            recipient_type: 接收人类型枚举

        Returns:
            List[MNotificationRecipient]: 接收人列表
        """
        try:
            results = self.find(
                filters={
                    "recipient_type": recipient_type.value,
                    "is_del": False
                },
                as_dataframe=False
            )
            return results

        except Exception as e:
            GLOG.ERROR(f"Error getting recipients by type '{recipient_type}': {e}")
            return []

    def get_active_recipients(self, recipient_type: Optional[RECIPIENT_TYPES] = None) -> List[MNotificationRecipient]:
        """
        获取所有启用的接收人

        Args:
            recipient_type: 可选的接收人类型过滤

        Returns:
            List[MNotificationRecipient]: 启用的接收人列表
        """
        try:
            filters = {"is_del": False}
            if recipient_type is not None:
                filters["recipient_type"] = recipient_type.value

            results = self.find(filters=filters, as_dataframe=False)
            return results

        except Exception as e:
            GLOG.ERROR(f"Error getting active recipients: {e}")
            return []

    def get_default_recipients(self) -> List[MNotificationRecipient]:
        """
        获取所有默认接收人

        Returns:
            List[MNotificationRecipient]: 默认接收人列表
        """
        try:
            results = self.find(
                filters={
                    "is_default": True,
                    "is_del": False
                },
                as_dataframe=False
            )
            return results

        except Exception as e:
            GLOG.ERROR(f"Error getting default recipients: {e}")
            return []

    def get_by_user_id(self, user_id: str) -> List[MNotificationRecipient]:
        """
        根据用户ID查询接收人

        Args:
            user_id: 用户UUID

        Returns:
            List[MNotificationRecipient]: 接收人列表
        """
        try:
            results = self.find(
                filters={
                    "user_id": user_id,
                    "is_del": False
                },
                as_dataframe=False
            )
            return results

        except Exception as e:
            GLOG.ERROR(f"Error getting recipients by user_id '{user_id}': {e}")
            return []

    def get_by_user_group_id(self, user_group_id: str) -> List[MNotificationRecipient]:
        """
        根据用户组ID查询接收人

        Args:
            user_group_id: 用户组UUID

        Returns:
            List[MNotificationRecipient]: 接收人列表
        """
        try:
            results = self.find(
                filters={
                    "user_group_id": user_group_id,
                    "is_del": False
                },
                as_dataframe=False
            )
            return results

        except Exception as e:
            GLOG.ERROR(f"Error getting recipients by user_group_id '{user_group_id}': {e}")
            return []

    def update_by_uuid(
        self,
        uuid: str,
        **kwargs
    ) -> int:
        """
        根据 UUID 更新接收人

        Args:
            uuid: 接收人 UUID
            **kwargs: 要更新的字段

        Returns:
            int: 更新的记录数量
        """
        try:
            modified_count = self.modify(
                filters={"uuid": uuid, "is_del": False},
                updates=kwargs
            )
            return modified_count

        except Exception as e:
            GLOG.ERROR(f"Error updating recipient by uuid '{uuid}': {e}")
            return 0

    def clear_default_by_type(self, recipient_type: RECIPIENT_TYPES) -> int:
        """
        清除指定类型的其他默认接收人

        Args:
            recipient_type: 接收人类型

        Returns:
            int: 更新的记录数量
        """
        try:
            modified_count = self.modify(
                filters={
                    "recipient_type": recipient_type.value,
                    "is_default": True,
                    "is_del": False
                },
                updates={"is_default": False}
            )
            return modified_count

        except Exception as e:
            GLOG.ERROR(f"Error clearing default recipients: {e}")
            return 0
