# Upstream: CLI Commands (ginkgo groups 命令)
# Downstream: BaseService (继承提供服务基础能力)、UserGroupCRUD (用户组CRUD操作)、UserGroupMappingCRUD (用户组映射CRUD操作)
# Role: UserGroupService用户组管理业务服务提供用户组创建、用户加入/移除组、组查询等业务逻辑支持通知系统用户组管理功能


"""
User Group Management Service

This service handles business logic for managing user groups including:
- Creating user groups
- Adding users to groups
- Removing users from groups
- Deleting groups
"""

from typing import List, Optional, Union, Any
import pandas as pd

from ginkgo.libs import GLOG, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud import UserGroupCRUD, UserGroupMappingCRUD
from ginkgo.data.models import MUserGroup, MUserGroupMapping
from ginkgo.enums import SOURCE_TYPES


class UserGroupService(BaseService):
    """
    User Group Management Service

    Provides business logic for user group management operations including
    group creation, user management, and cascade deletion.
    """

    def __init__(self, user_group_crud: UserGroupCRUD, user_group_mapping_crud: UserGroupMappingCRUD):
        """
        Initialize UserGroupService with CRUD dependencies

        Args:
            user_group_crud: UserGroup CRUD repository instance
            user_group_mapping_crud: UserGroupMapping CRUD repository instance
        """
        super().__init__(crud_repo=user_group_crud)
        self.user_group_crud = user_group_crud
        self.user_group_mapping_crud = user_group_mapping_crud

    @retry(max_try=3)
    def create_group(
        self,
        name: str,
        description: Optional[str] = None,
        is_active: bool = True
    ) -> ServiceResult:
        """
        Create a new user group

        Args:
            name: Group name (unique business identifier)
            description: Group description
            is_active: Whether the group is active

        Returns:
            ServiceResult with created group info
        """
        try:
            # Check if name already exists
            existing = self.user_group_crud.find(filters={"name": name}, page_size=1, as_dataframe=False)
            if existing:
                return ServiceResult.error(
                    f"Group already exists: {name}",
                    message="A group with this name already exists"
                )

            # Create group
            group = MUserGroup(
                name=name,
                description=description,
                is_active=is_active,
                source=SOURCE_TYPES.OTHER
            )

            # Insert via CRUD
            created_group = self.user_group_crud.add(group)

            if created_group is None:
                return ServiceResult.error(
                    "Failed to create group",
                    message="Database insert operation returned None"
                )

            # Extract UUID from created group object
            group_uuid = created_group.uuid

            GLOG.INFO(f"Created group: {group_uuid}, name={name}")

            return ServiceResult.success(
                data={
                    "uuid": group_uuid,
                    "name": name,
                    "description": description,
                    "is_active": is_active
                },
                message=f"Group '{name}' created successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error creating group: {e}")
            return ServiceResult.error(
                f"Failed to create group: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def add_user_to_group(
        self,
        user_uuid: str,
        group_uuid: str
    ) -> ServiceResult:
        """
        Add a user to a group

        Args:
            user_uuid: User UUID
            group_uuid: Group UUID

        Returns:
            ServiceResult indicating success or failure
        """
        try:
            # Check if user exists (using user_crud if available, or skip)
            # For now, assume user exists

            # Check if group exists
            groups = self.user_group_crud.find(filters={"uuid": group_uuid}, page_size=1, as_dataframe=False)
            if not groups:
                return ServiceResult.error(
                    f"Group not found: {group_uuid}",
                    message="Group does not exist"
                )

            # Check if mapping already exists
            if self.user_group_mapping_crud.check_mapping_exists(user_uuid, group_uuid):
                return ServiceResult.error(
                    f"User already in group: {user_uuid} in {group_uuid}",
                    message="User is already a member of this group"
                )

            # Create mapping
            mapping = MUserGroupMapping(
                user_uuid=user_uuid,
                group_uuid=group_uuid,
                source=SOURCE_TYPES.OTHER
            )

            created_mapping = self.user_group_mapping_crud.add(mapping)

            if created_mapping is None:
                return ServiceResult.error(
                    "Failed to add user to group",
                    message="Database insert operation returned None"
                )

            # Extract UUID from created mapping object
            mapping_uuid = created_mapping.uuid

            GLOG.INFO(f"Added user {user_uuid} to group {group_uuid}, mapping={mapping_uuid}")

            return ServiceResult.success(
                data={
                    "mapping_uuid": mapping_uuid,
                    "user_uuid": user_uuid,
                    "group_uuid": group_uuid
                },
                message="User added to group successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error adding user to group: {e}")
            return ServiceResult.error(
                f"Failed to add user to group: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def remove_user_from_group(
        self,
        user_uuid: str,
        group_uuid: str
    ) -> ServiceResult:
        """
        Remove a user from a group

        Args:
            user_uuid: User UUID
            group_uuid: Group UUID

        Returns:
            ServiceResult indicating success or failure
        """
        try:
            count = self.user_group_mapping_crud.remove_user_from_group(user_uuid, group_uuid)

            if count == 0:
                return ServiceResult.error(
                    f"Mapping not found: {user_uuid} in {group_uuid}",
                    message="User is not a member of this group"
                )

            GLOG.INFO(f"Removed user {user_uuid} from group {group_uuid}")

            return ServiceResult.success(
                data={
                    "user_uuid": user_uuid,
                    "group_uuid": group_uuid,
                    "deleted_count": count
                },
                message="User removed from group successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error removing user from group: {e}")
            return ServiceResult.error(
                f"Failed to remove user from group: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def delete_group(self, group_uuid: str) -> ServiceResult:
        """
        Delete a group with cascade (all user mappings)

        Args:
            group_uuid: Group UUID to delete

        Returns:
            ServiceResult indicating success or failure
        """
        try:
            # Remove all users from group first
            mappings = self.user_group_mapping_crud.find_by_group(group_uuid)
            removed_count = 0
            for mapping in mappings:
                count = self.user_group_mapping_crud.remove_user_from_group(mapping.user_uuid, group_uuid)
                removed_count += count

            # Delete group using remove instead of delete
            self.user_group_crud.remove(filters={"uuid": group_uuid})

            GLOG.INFO(f"Deleted group {group_uuid} with {removed_count} user mappings removed")

            return ServiceResult.success(
                data={
                    "group_uuid": group_uuid,
                    "mappings_removed": removed_count
                },
                message=f"Group and {removed_count} user mappings deleted successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error deleting group: {e}")
            return ServiceResult.error(
                f"Failed to delete group: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def get_group(self, group_uuid: str) -> ServiceResult:
        """
        Get group by UUID

        Args:
            group_uuid: Group UUID

        Returns:
            ServiceResult with group data
        """
        try:
            groups = self.user_group_crud.find(filters={"uuid": group_uuid}, page_size=1, as_dataframe=False)

            if not groups:
                return ServiceResult.error(
                    f"Group not found: {group_uuid}",
                    message="Group does not exist"
                )

            group = groups[0]

            return ServiceResult.success(
                data={
                    "uuid": group.uuid,
                    "name": group.name,
                    "description": group.description,
                    "is_active": group.is_active,
                    "source": SOURCE_TYPES.from_int(group.source).name,
                    "create_at": group.create_at.isoformat() if group.create_at else None,
                    "update_at": group.update_at.isoformat() if group.update_at else None
                },
                message="Group retrieved successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting group: {e}")
            return ServiceResult.error(
                f"Failed to get group: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def list_groups(
        self,
        is_active: Optional[bool] = None,
        limit: int = 100
    ) -> ServiceResult:
        """
        List groups with optional filters

        Args:
            is_active: Filter by active status
            limit: Maximum number of results

        Returns:
            ServiceResult with list of groups
        """
        try:
            filters = {"is_del": False}  # 默认过滤已删除的组
            if is_active is not None:
                filters["is_active"] = is_active

            groups = self.user_group_crud.find(filters=filters, page_size=limit, as_dataframe=False)

            group_list = []
            for group in groups:
                group_list.append({
                    "uuid": group.uuid,
                    "name": group.name,
                    "description": group.description,
                    "is_active": group.is_active,
                    "update_at": group.update_at.isoformat() if group.update_at else None
                })

            return ServiceResult.success(
                data={"groups": group_list, "count": len(group_list)},
                message=f"Retrieved {len(group_list)} groups"
            )

        except Exception as e:
            GLOG.ERROR(f"Error listing groups: {e}")
            return ServiceResult.error(
                f"Failed to list groups: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def get_group_members(self, group_uuid: str) -> ServiceResult:
        """
        Get all members of a group with user names

        Args:
            group_uuid: Group UUID

        Returns:
            ServiceResult with list of members including user names
        """
        try:
            from ginkgo.data.crud import UserCRUD
            from ginkgo.data.containers import container

            mappings = self.user_group_mapping_crud.find_by_group(group_uuid)
            user_crud = container.user_crud()

            member_list = []
            for mapping in mappings:
                # Get user info to fetch user name
                users = user_crud.find(filters={"uuid": mapping.user_uuid}, page_size=1, as_dataframe=False)
                user_name = users[0].name if users else "Unknown"

                member_list.append({
                    "mapping_uuid": mapping.uuid,
                    "user_uuid": mapping.user_uuid,
                    "user_name": user_name,
                    "group_uuid": mapping.group_uuid
                })

            return ServiceResult.success(
                data={"members": member_list, "count": len(member_list)},
                message=f"Retrieved {len(member_list)} group members"
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting group members: {e}")
            return ServiceResult.error(
                f"Failed to get group members: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def get_user_groups(self, user_uuid: str) -> ServiceResult:
        """
        Get all groups for a user

        Args:
            user_uuid: User UUID

        Returns:
            ServiceResult with list of group info
        """
        try:
            mappings = self.user_group_mapping_crud.find_by_user(user_uuid)

            # Get full group info for each mapping
            group_list = []
            for mapping in mappings:
                groups = self.user_group_crud.find(
                    filters={"uuid": mapping.group_uuid},
                    page_size=1,
                    as_dataframe=False
                )
                if groups:
                    group = groups[0]
                    group_list.append({
                        "group_uuid": group.uuid,
                        "name": group.name,
                        "description": group.description
                    })

            return ServiceResult.success(
                data={"groups": group_list, "count": len(group_list)},
                message=f"Retrieved {len(group_list)} groups for user"
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting user groups: {e}")
            return ServiceResult.error(
                f"Failed to get user groups: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def fuzzy_search(self, query: str, limit: int = 100) -> ServiceResult:
        """
        Fuzzy search groups by UUID or name

        Searches in uuid and name fields with partial matching.
        Full UUID (32 hex chars) will match exactly, otherwise uses LIKE query.

        Args:
            query: Search keyword (UUID or group name)
            limit: Maximum results to return

        Returns:
            ServiceResult with list of matching groups

        Examples:
            result = service.fuzzy_search("traders")
            result = service.fuzzy_search("fbe6e147")
        """
        try:
            groups = self.user_group_crud.fuzzy_search(query)

            # Apply limit
            if limit and len(groups) > limit:
                groups = groups.head(limit)

            group_list = []
            for group in groups:
                group_list.append({
                    "uuid": group.uuid,
                    "name": group.name,
                    "description": group.description,
                    "is_active": group.is_active,
                    "create_at": group.create_at.isoformat() if group.create_at else None
                })

            return ServiceResult.success(
                data={"groups": group_list, "count": len(group_list)},
                message=f"Found {len(group_list)} groups matching '{query}'"
            )

        except Exception as e:
            GLOG.ERROR(f"Error fuzzy searching groups: {e}")
            return ServiceResult.error(
                f"Failed to search groups: {str(e)}",
                message=f"Error: {str(e)}"
            )
