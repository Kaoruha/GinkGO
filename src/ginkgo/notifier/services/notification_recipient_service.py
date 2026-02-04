# Upstream: API Server (settings.py 路由调用)
# Downstream: NotificationRecipientCRUD (CRUD操作)、MNotificationRecipient (模型)
# Role: NotificationRecipientService通知接收人业务服务提供全局接收人的增删改查管理业务逻辑支持系统级通知接收人管理功能


"""
Notification Recipient Service

通知接收人业务服务层，提供全局通知接收人的完整业务逻辑。
通过引用用户/用户组实现。
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from ginkgo.libs import GLOG, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud import NotificationRecipientCRUD, UserContactCRUD, UserGroupMappingCRUD
from ginkgo.data.models.model_notification_recipient import MNotificationRecipient
from ginkgo.data.models.model_user_contact import MUserContact
from ginkgo.enums import RECIPIENT_TYPES, CONTACT_TYPES, SOURCE_TYPES


class NotificationRecipientService(BaseService):
    """
    通知接收人业务服务

    提供全局通知接收人的管理功能，通过引用用户/用户组实现。
    """

    def __init__(
        self,
        recipient_crud: NotificationRecipientCRUD,
        user_contact_crud: UserContactCRUD,
        user_group_mapping_crud: UserGroupMappingCRUD
    ):
        """
        初始化 NotificationRecipientService

        Args:
            recipient_crud: NotificationRecipientCRUD 实例
            user_contact_crud: UserContactCRUD 实例
            user_group_mapping_crud: UserGroupMappingCRUD 实例
        """
        super().__init__(crud_repo=recipient_crud)
        self.recipient_crud = recipient_crud
        self.user_contact_crud = user_contact_crud
        self.user_group_mapping_crud = user_group_mapping_crud

    @retry(max_try=3)
    def add_recipient(
        self,
        name: str,
        recipient_type: Union[RECIPIENT_TYPES, int, str],
        user_id: Optional[str] = None,
        user_group_id: Optional[str] = None,
        is_default: bool = False,
        description: Optional[str] = None,
        source: Union[SOURCE_TYPES, int] = SOURCE_TYPES.OTHER
    ) -> ServiceResult:
        """
        添加全局通知接收人

        Args:
            name: 接收人名称
            recipient_type: 接收人类型 (USER/USER_GROUP)
            user_id: 关联的用户UUID
            user_group_id: 关联的用户组UUID
            is_default: 是否为默认接收人
            description: 描述信息
            source: 数据来源

        Returns:
            ServiceResult: 包含创建的接收人信息
        """
        try:
            GLOG.INFO(f"Creating recipient - name: {name}, type: {recipient_type}, user_id: {user_id}, user_group_id: {user_group_id}")

            # 验证接收人类型
            if isinstance(recipient_type, str):
                GLOG.INFO(f"Converting string recipient_type: {recipient_type}")
                recipient_type = RECIPIENT_TYPES.enum_convert(recipient_type)
                GLOG.INFO(f"Converted to: {recipient_type}")
            elif isinstance(recipient_type, int):
                recipient_type = RECIPIENT_TYPES.from_int(recipient_type)
                GLOG.INFO(f"Converted from int to: {recipient_type}")

            if recipient_type is None:
                GLOG.ERROR(f"Invalid recipient_type: {recipient_type}")
                return ServiceResult.error(
                    f"Invalid recipient_type: {recipient_type}",
                    message="Recipient type must be 'USER' or 'USER_GROUP'"
                )

            # 验证关联字段
            if recipient_type == RECIPIENT_TYPES.USER:
                if user_id is None:
                    return ServiceResult.error(
                        "user_id is required for USER type",
                        message="Missing user_id"
                    )
                # 验证用户是否有主联系方式
                contacts = self.user_contact_crud.find(
                    filters={"user_id": user_id, "is_primary": True, "is_del": False},
                    page_size=1,
                page=0,
                    as_dataframe=False
                )
                if not contacts:
                    return ServiceResult.error(
                        f"User {user_id} has no primary contact",
                        message="User must have a primary contact"
                    )
                user_group_id = None

            elif recipient_type == RECIPIENT_TYPES.USER_GROUP:
                if user_group_id is None:
                    return ServiceResult.error(
                        "user_group_id is required for USER_GROUP type",
                        message="Missing user_group_id"
                    )
                user_id = None
            else:
                return ServiceResult.error(
                    f"Invalid recipient_type: {recipient_type}",
                    message="Invalid recipient type"
                )

            # 检查名称是否已存在
            existing = self.recipient_crud.get_by_name(name)
            if existing is not None:
                return ServiceResult.error(
                    f"Recipient with name '{name}' already exists",
                    message="Duplicate recipient name"
                )

            # 如果设为默认接收人，先清除其他默认接收人（同类型）
            if is_default:
                self.recipient_crud.clear_default_by_type(recipient_type)

            # 创建模型实例
            recipient = MNotificationRecipient(
                name=name,
                recipient_type=recipient_type.value,
                user_id=user_id,
                user_group_id=user_group_id,
                is_default=is_default,
                description=description or "",
                is_del=False,
                source=source.value if isinstance(source, SOURCE_TYPES) else source
            )

            # 添加到数据库
            created_recipient = self.recipient_crud.add(recipient)

            if created_recipient is None:
                return ServiceResult.error(
                    "Failed to create notification recipient",
                    message="Database operation failed"
                )

            GLOG.INFO(f"Created notification recipient: {name} ({recipient_type.name})")

            return ServiceResult.success(
                data={
                    "uuid": str(created_recipient.uuid),
                    "name": created_recipient.name,
                    "recipient_type": recipient_type.name,
                    "user_id": created_recipient.user_id,
                    "user_group_id": created_recipient.user_group_id,
                    "is_default": created_recipient.is_default,
                    "description": created_recipient.description
                },
                message=f"Recipient '{name}' created successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error adding notification recipient: {e}")
            return ServiceResult.error(
                f"Failed to add recipient: {str(e)}"
            )

    @retry(max_try=3)
    def update_recipient(
        self,
        uuid: str,
        name: Optional[str] = None,
        recipient_type: Optional[Union[RECIPIENT_TYPES, int, str]] = None,
        user_id: Optional[str] = None,
        user_group_id: Optional[str] = None,
        is_default: Optional[bool] = None,
        description: Optional[str] = None
    ) -> ServiceResult:
        """
        更新通知接收人

        Args:
            uuid: 接收人 UUID
            name: 新的名称
            recipient_type: 新的接收人类型
            user_id: 新的用户UUID
            user_group_id: 新的用户组UUID
            is_default: 是否为默认接收人
            description: 新的描述

        Returns:
            ServiceResult: 更新结果
        """
        try:
            # 检查接收人是否存在
            recipients = self.recipient_crud.find(
                filters={"uuid": uuid, "is_del": False},
                page_size=1,
                page=0,
                as_dataframe=False
            )
            if not recipients:
                return ServiceResult.error(
                    f"Recipient not found: {uuid}",
                    message="Recipient does not exist"
                )
            recipient = recipients[0]

            # 如果更新名称，检查是否重复
            if name and name != recipient.name:
                existing = self.recipient_crud.get_by_name(name)
                if existing is not None and existing.uuid != uuid:
                    return ServiceResult.error(
                        f"Recipient with name '{name}' already exists",
                        message="Duplicate recipient name"
                    )

            # 构建更新数据
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if is_default is not None:
                update_data["is_default"] = is_default

            # 处理类型和关联字段变更
            new_type = None
            if recipient_type is not None:
                if isinstance(recipient_type, str):
                    new_type = RECIPIENT_TYPES.enum_convert(recipient_type)
                elif isinstance(recipient_type, int):
                    new_type = RECIPIENT_TYPES.from_int(recipient_type)

                if new_type is None:
                    return ServiceResult.error(
                        f"Invalid recipient_type: {recipient_type}",
                        message="Recipient type validation failed"
                    )

                update_data["recipient_type"] = new_type.value

                # 根据类型设置关联字段
                if new_type == RECIPIENT_TYPES.USER:
                    if user_id is None:
                        return ServiceResult.error(
                            "user_id is required for USER type",
                            message="Missing user_id"
                        )
                    update_data["user_id"] = user_id
                    update_data["user_group_id"] = None
                elif new_type == RECIPIENT_TYPES.USER_GROUP:
                    if user_group_id is None:
                        return ServiceResult.error(
                            "user_group_id is required for USER_GROUP type",
                            message="Missing user_group_id"
                        )
                    update_data["user_group_id"] = user_group_id
                    update_data["user_id"] = None

            # 如果设为默认接收人，先清除其他默认接收人
            if is_default is True:
                target_type = new_type or recipient.get_recipient_type_enum()
                if target_type:
                    self.recipient_crud.clear_default_by_type(target_type)

            # 执行更新
            modified_count = self.recipient_crud.update_by_uuid(uuid, **update_data)

            if modified_count == 0:
                return ServiceResult.error(
                    "Failed to update recipient",
                    message="No records were modified"
                )

            GLOG.INFO(f"Updated notification recipient: {uuid}")

            return ServiceResult.success(
                data={"uuid": uuid, "modified_count": modified_count},
                message="Recipient updated successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error updating notification recipient {uuid}: {e}")
            return ServiceResult.error(
                f"Failed to update recipient: {str(e)}"
            )

    @retry(max_try=3)
    def delete_recipient(self, uuid: str) -> ServiceResult:
        """
        删除通知接收人（软删除）

        Args:
            uuid: 接收人 UUID

        Returns:
            ServiceResult: 删除结果
        """
        try:
            recipients = self.recipient_crud.find(
                filters={"uuid": uuid, "is_del": False},
                page_size=1,
                page=0,
                as_dataframe=False
            )
            if not recipients:
                return ServiceResult.error(
                    f"Recipient not found: {uuid}",
                    message="Recipient does not exist"
                )
            recipient = recipients[0]

            # MySQL CRUD 使用 remove() 方法进行软删除
            self.recipient_crud.remove(filters={"uuid": uuid})

            GLOG.INFO(f"Deleted notification recipient: {recipient.name}")

            return ServiceResult.success(
                data={"uuid": uuid},
                message=f"Recipient '{recipient.name}' deleted successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error deleting notification recipient {uuid}: {e}")
            return ServiceResult.error(
                f"Failed to delete recipient: {str(e)}"
            )

    @retry(max_try=3)
    def toggle_default(self, uuid: str) -> ServiceResult:
        """
        切换接收人默认状态

        Args:
            uuid: 接收人 UUID

        Returns:
            ServiceResult: 包含新状态
        """
        try:
            recipients = self.recipient_crud.find(
                filters={"uuid": uuid, "is_del": False},
                page_size=1,
                page=0,
                as_dataframe=False
            )
            if not recipients:
                return ServiceResult.error(
                    f"Recipient not found: {uuid}",
                    message="Recipient does not exist"
                )
            recipient = recipients[0]

            new_status = not recipient.is_default

            # 如果设为默认，清除同类型的其他默认接收人
            if new_status:
                recipient_type = recipient.get_recipient_type_enum()
                if recipient_type:
                    self.recipient_crud.clear_default_by_type(recipient_type)

            self.recipient_crud.modify(
                filters={"uuid": uuid},
                updates={"is_default": new_status}
            )

            GLOG.INFO(f"Toggled recipient {uuid}: {recipient.is_default} -> {new_status}")

            return ServiceResult.success(
                data={
                    "uuid": uuid,
                    "is_default": new_status,
                    "name": recipient.name
                },
                message=f"Recipient {'is now default' if new_status else 'is no longer default'}"
            )

        except Exception as e:
            GLOG.ERROR(f"Error toggling recipient {uuid}: {e}")
            return ServiceResult.error(
                f"Failed to toggle recipient: {str(e)}"
            )

    def list_all(
        self,
        recipient_type: Optional[Union[RECIPIENT_TYPES, int, str]] = None,
        is_default: Optional[bool] = None
    ) -> ServiceResult:
        """
        查询通知接收人列表

        Args:
            recipient_type: 接收人类型过滤
            is_default: 是否默认接收人过滤

        Returns:
            ServiceResult: 包含接收人列表
        """
        try:
            # 构建查询条件
            filters = {"is_del": False}

            if is_default is not None:
                filters["is_default"] = is_default

            if recipient_type is not None:
                if isinstance(recipient_type, str):
                    recipient_type = RECIPIENT_TYPES.enum_convert(recipient_type)
                elif isinstance(recipient_type, int):
                    recipient_type = RECIPIENT_TYPES.from_int(recipient_type)

                if recipient_type is not None:
                    filters["recipient_type"] = recipient_type.value

            # 查询
            recipients = self.recipient_crud.find(filters=filters, as_dataframe=False)

            # 获取所有用户和用户组信息用于显示
            user_ids = list(set([r.user_id for r in recipients if r.user_id]))
            group_ids = list(set([r.user_group_id for r in recipients if r.user_group_id]))

            users_map = {}
            if user_ids:
                from ginkgo.data.containers import container
                user_crud = container.user_crud()
                for user_id in user_ids:
                    user_list = user_crud.find(filters={"uuid": user_id, "is_del": False}, as_dataframe=False)
                    if user_list:
                        u = user_list[0]
                        users_map[user_id] = {"uuid": u.uuid, "username": u.username, "display_name": u.display_name}

            groups_map = {}
            if group_ids:
                from ginkgo.data.containers import container
                group_crud = container.user_group_crud()
                for group_id in group_ids:
                    group_list = group_crud.find(filters={"uuid": group_id, "is_del": False}, as_dataframe=False)
                    if group_list:
                        g = group_list[0]
                        groups_map[group_id] = {"uuid": g.uuid, "name": g.name}

            result = []
            for r in recipients:
                item = {
                    "uuid": r.uuid,
                    "name": r.name,
                    "recipient_type": r.get_recipient_type_enum().name if r.get_recipient_type_enum() else "UNKNOWN",
                    "user_id": r.user_id,
                    "user_group_id": r.user_group_id,
                    "is_default": r.is_default,
                    "description": r.description,
                    "created_at": r.create_at.isoformat() if r.create_at else None
                }

                # 添加关联的用户/用户组信息
                if r.user_id and r.user_id in users_map:
                    item["user_info"] = users_map[r.user_id]
                if r.user_group_id and r.user_group_id in groups_map:
                    item["user_group_info"] = groups_map[r.user_group_id]

                result.append(item)

            return ServiceResult.success(
                data={"recipients": result, "count": len(result)},
                message=f"Found {len(result)} recipients"
            )

        except Exception as e:
            GLOG.ERROR(f"Error listing recipients: {e}")
            return ServiceResult.error(
                f"Failed to list recipients: {str(e)}"
            )

    def get_recipient_contacts(self, uuid: str) -> ServiceResult:
        """
        获取接收人的实际联系方式列表

        Args:
            uuid: 接收人 UUID

        Returns:
            ServiceResult: 包含联系方式列表
        """
        try:
            recipients = self.recipient_crud.find(
                filters={"uuid": uuid, "is_del": False},
                page_size=1,
                page=0,
                as_dataframe=False
            )
            if not recipients:
                return ServiceResult.error(
                    f"Recipient not found: {uuid}",
                    message="Recipient does not exist"
                )
            recipient = recipients[0]

            recipient_type = recipient.get_recipient_type_enum()
            contacts = []

            if recipient_type == RECIPIENT_TYPES.USER:
                # 获取用户的主联系方式
                user_contacts = self.user_contact_crud.find(
                    filters={
                        "user_id": recipient.user_id,
                        "is_primary": True,
                        "is_del": False
                    },
                    as_dataframe=False
                )
                for uc in user_contacts:
                    contacts.append({
                        "type": uc.get_contact_type_enum().name if uc.get_contact_type_enum() else "UNKNOWN",
                        "address": uc.address
                    })

            elif recipient_type == RECIPIENT_TYPES.USER_GROUP:
                # 获取用户组所有用户的主联系方式
                mappings = self.user_group_mapping_crud.find(
                    filters={"group_uuid": recipient.user_group_id, "is_del": False},
                    as_dataframe=False
                )
                for mapping in mappings:
                    user_contacts = self.user_contact_crud.find(
                        filters={
                            "user_id": mapping.user_uuid,  # MUserGroupMapping uses user_uuid, MUserContact uses user_id
                            "is_primary": True,
                            "is_del": False
                        },
                        as_dataframe=False
                    )
                    for uc in user_contacts:
                        contacts.append({
                            "type": uc.get_contact_type_enum().name if uc.get_contact_type_enum() else "UNKNOWN",
                            "address": uc.address
                        })

            return ServiceResult.success(
                data={
                    "recipient_uuid": uuid,
                    "recipient_name": recipient.name,
                    "recipient_type": recipient_type.name if recipient_type else "UNKNOWN",
                    "contacts": contacts,
                    "contact_count": len(contacts)
                },
                message=f"Found {len(contacts)} contacts for recipient"
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting recipient contacts {uuid}: {e}")
            return ServiceResult.error(
                f"Failed to get recipient contacts: {str(e)}"
            )
