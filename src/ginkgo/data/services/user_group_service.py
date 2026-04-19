# Upstream: Settings API (用户组管理)
# Downstream: UserGroupCRUD, UserGroupMappingCRUD
# Role: UserGroupService用户组管理业务服务

from typing import Optional

from ginkgo.data.crud.user_group_crud import UserGroupCRUD
from ginkgo.data.crud.user_group_mapping_crud import UserGroupMappingCRUD
from ginkgo.data.models import MUserGroup, MUserGroupMapping
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult


class UserGroupService:
    """用户组管理服务 — 整合 group + group mapping"""

    def __init__(self):
        self.group_crud = UserGroupCRUD()
        self.mapping_crud = UserGroupMappingCRUD()

    def list_groups(self, **filters) -> ServiceResult:
        """查询用户组列表"""
        try:
            filters.setdefault("is_del", False)
            groups = self.group_crud.find(filters=filters)

            result = []
            for group in groups:
                member_count = len(self.mapping_crud.find_by_group(group.uuid))
                result.append({
                    "uuid": group.uuid,
                    "name": group.name,
                    "description": group.description or "",
                    "member_count": member_count,
                    "created_at": str(group.create_at) if hasattr(group, "create_at") else None,
                })

            return ServiceResult.success(result)
        except Exception as e:
            GLOG.ERROR(f"Failed to list groups: {e}")
            return ServiceResult.error(str(e))

    def get_group(self, uuid: str) -> ServiceResult:
        """获取单个用户组"""
        try:
            groups = self.group_crud.find(filters={"uuid": uuid, "is_del": False})
            if not groups:
                return ServiceResult.error("Group not found")
            return ServiceResult.success(groups[0])
        except Exception as e:
            GLOG.ERROR(f"Failed to get group: {e}")
            return ServiceResult.error(str(e))

    def create_group(self, name: str, description: str = "") -> ServiceResult:
        """创建用户组"""
        try:
            group = MUserGroup(name=name, description=description)
            created = self.group_crud.add(group)
            if not created:
                return ServiceResult.error("Failed to create group")
            return ServiceResult.success({"uuid": created.uuid, "name": name})
        except Exception as e:
            GLOG.ERROR(f"Failed to create group: {e}")
            return ServiceResult.error(str(e))

    def update_group(self, uuid: str, **updates) -> ServiceResult:
        """更新用户组"""
        try:
            groups = self.group_crud.find(filters={"uuid": uuid, "is_del": False})
            if not groups:
                return ServiceResult.error("Group not found")
            self.group_crud.modify(filters={"uuid": uuid}, updates=updates)
            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update group: {e}")
            return ServiceResult.error(str(e))

    def delete_group(self, uuid: str) -> ServiceResult:
        """删除用户组及其成员映射"""
        try:
            # 删除所有成员映射
            mappings = self.mapping_crud.find_by_group(uuid)
            for m in mappings:
                self.mapping_crud.remove(filters={"uuid": m.uuid})

            # 删除用户组
            self.group_crud.delete(filters={"uuid": uuid})
            return ServiceResult.success({"deleted": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to delete group: {e}")
            return ServiceResult.error(str(e))

    # ==================== 成员管理 ====================

    def list_members(self, group_uuid: str) -> ServiceResult:
        """获取用户组成员列表"""
        try:
            mappings = self.mapping_crud.find_by_group(group_uuid)
            members = [{"uuid": m.user_uuid, "group_uuid": m.group_uuid} for m in mappings]
            return ServiceResult.success(members)
        except Exception as e:
            GLOG.ERROR(f"Failed to list members: {e}")
            return ServiceResult.error(str(e))

    def add_member(self, user_uuid: str, group_uuid: str) -> ServiceResult:
        """添加成员到用户组"""
        try:
            if self.mapping_crud.check_mapping_exists(user_uuid, group_uuid):
                return ServiceResult.error("User already in group")

            mapping = MUserGroupMapping(user_uuid=user_uuid, group_uuid=group_uuid)
            self.mapping_crud.add(mapping)
            return ServiceResult.success({"added": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to add member: {e}")
            return ServiceResult.error(str(e))

    def remove_member(self, user_uuid: str, group_uuid: str) -> ServiceResult:
        """从用户组移除成员"""
        try:
            self.mapping_crud.remove_user_from_group(user_uuid, group_uuid)
            return ServiceResult.success({"removed": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to remove member: {e}")
            return ServiceResult.error(str(e))

    def count_members(self, group_uuid: str) -> int:
        """统计用户组成员数"""
        return len(self.mapping_crud.find_by_group(group_uuid))
