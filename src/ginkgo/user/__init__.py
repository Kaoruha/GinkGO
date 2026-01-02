# Upstream: CLI Commands (ginkgo users, ginkgo groups 命令)
# Downstream: None (终端模块)
# Role: User模块提供用户和用户组管理服务，支持用户创建、联系方式管理、用户组管理等通知系统用户管理功能


"""
User Management Module

Provides user and user group management services for the notification system.
"""

from ginkgo.user.services.user_service import UserService
from ginkgo.user.services.user_group_service import UserGroupService

__all__ = [
    "UserService",
    "UserGroupService",
]
