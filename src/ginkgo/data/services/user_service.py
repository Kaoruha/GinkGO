# Upstream: Auth API (登录/注册)、Settings API (用户管理)
# Downstream: UserCRUD, UserCredentialCRUD, UserContactCRUD
# Role: UserService用户管理业务服务，封装用户/凭据/联系方式的业务逻辑

from typing import Optional, List, Dict, Any

from ginkgo.data.crud.user_crud import UserCRUD
from ginkgo.data.crud.user_credential_crud import UserCredentialCRUD
from ginkgo.data.crud.user_contact_crud import UserContactCRUD
from ginkgo.data.models import MUser, MUserCredential, MUserContact
from ginkgo.enums import USER_TYPES, CONTACT_TYPES, SOURCE_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult


class UserService:
    """用户管理服务 — 整合 user + credential + contact"""

    def __init__(self):
        self.user_crud = UserCRUD()
        self.credential_crud = UserCredentialCRUD()
        self.contact_crud = UserContactCRUD()

    # ==================== 用户 ====================

    def list_users(self, **filters) -> ServiceResult:
        """查询用户列表"""
        try:
            filters.setdefault("is_del", False)
            users = self.user_crud.find(filters=filters)

            result = []
            for user in users:
                credential = self.credential_crud.get_by_user_id(user.uuid)
                result.append({
                    "uuid": user.uuid,
                    "username": user.username,
                    "display_name": user.display_name or user.username,
                    "is_active": user.is_active,
                    "is_admin": credential.is_admin if credential else False,
                    "created_at": str(user.create_at) if hasattr(user, "create_at") else None,
                })

            return ServiceResult.success(result)
        except Exception as e:
            GLOG.ERROR(f"Failed to list users: {e}")
            return ServiceResult.error(str(e))

    def get_user(self, uuid: str) -> ServiceResult:
        """获取单个用户"""
        try:
            users = self.user_crud.find(filters={"uuid": uuid, "is_del": False})
            if not users:
                return ServiceResult.error("User not found")
            return ServiceResult.success(users[0])
        except Exception as e:
            GLOG.ERROR(f"Failed to get user: {e}")
            return ServiceResult.error(str(e))

    def create_user(self, username: str, display_name: str = None,
                    email: str = "", description: str = "",
                    password_hash: str = None) -> ServiceResult:
        """创建用户，同时创建凭据"""
        try:
            # 检查用户名是否已存在
            existing = self.user_crud.find(filters={"username": username, "is_del": False})
            if existing:
                return ServiceResult.error("Username already exists")

            # 创建 MUser
            user = MUser(
                username=username,
                display_name=display_name or username,
                email=email,
                description=description,
                user_type=USER_TYPES.PERSON,
                is_active=True,
                source=SOURCE_TYPES.OTHER,
            )
            created_user = self.user_crud.add(user)
            if not created_user:
                return ServiceResult.error("Failed to create user")

            # 创建凭据
            if password_hash:
                credential = MUserCredential(
                    user_id=created_user.uuid,
                    password_hash=password_hash,
                    is_active=True,
                    is_admin=False,
                )
                self.credential_crud.add(credential)

            return ServiceResult.success({
                "uuid": created_user.uuid,
                "username": username,
                "display_name": display_name or username,
            })
        except Exception as e:
            GLOG.ERROR(f"Failed to create user: {e}")
            return ServiceResult.error(str(e))

    def update_user(self, uuid: str, **updates) -> ServiceResult:
        """更新用户信息"""
        try:
            users = self.user_crud.find(filters={"uuid": uuid, "is_del": False})
            if not users:
                return ServiceResult.error("User not found")
            user = users[0]

            # 用户字段更新
            user_updates = {}
            credential_updates = {}
            for key in ("display_name", "email", "description", "is_active"):
                if key in updates:
                    user_updates[key] = updates[key]

            # 凭据字段更新
            if "is_admin" in updates:
                credential_updates["is_admin"] = updates["is_admin"]
            if "is_active" in updates:
                credential_updates["is_active"] = updates["is_active"]

            if user_updates:
                self.user_crud.modify(filters={"uuid": uuid}, updates=user_updates)

            if credential_updates:
                credential = self.credential_crud.get_by_user_id(uuid)
                if credential:
                    self.credential_crud.modify(
                        filters={"uuid": credential.uuid}, updates=credential_updates
                    )

            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update user: {e}")
            return ServiceResult.error(str(e))

    def delete_user(self, uuid: str) -> ServiceResult:
        """删除用户"""
        try:
            self.user_crud.delete(filters={"uuid": uuid})
            return ServiceResult.success({"deleted": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to delete user: {e}")
            return ServiceResult.error(str(e))

    # ==================== 凭据 ====================

    def get_credential(self, user_id: str):
        """根据用户ID获取凭据"""
        return self.credential_crud.get_by_user_id(user_id)

    def update_last_login(self, credential_uuid: str, ip: str = "") -> bool:
        """更新最后登录时间和IP"""
        from datetime import datetime
        try:
            self.credential_crud.modify(
                {"uuid": credential_uuid},
                {"last_login_at": datetime.now(), "last_login_ip": ip},
            )
            return True
        except Exception as e:
            GLOG.ERROR(f"Failed to update last login: {e}")
            return False

    def update_password(self, credential_uuid: str, new_password_hash: str) -> bool:
        """更新密码哈希"""
        try:
            self.credential_crud.modify(
                {"uuid": credential_uuid},
                {"password_hash": new_password_hash},
            )
            return True
        except Exception as e:
            GLOG.ERROR(f"Failed to update password: {e}")
            return False

    def reset_password(self, user_uuid: str, new_password_hash: str) -> ServiceResult:
        """重置用户密码"""
        try:
            credential = self.credential_crud.get_by_user_id(user_uuid)
            if not credential:
                return ServiceResult.error("Credential not found")
            self.credential_crud.modify(
                {"uuid": credential.uuid},
                {"password_hash": new_password_hash},
            )
            return ServiceResult.success({"reset": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to reset password: {e}")
            return ServiceResult.error(str(e))

    # ==================== 联系方式 ====================

    def get_contacts(self, user_id: str) -> ServiceResult:
        """获取用户联系方式"""
        try:
            contacts = self.contact_crud.find_by_user_id(user_id)
            return ServiceResult.success(contacts)
        except Exception as e:
            GLOG.ERROR(f"Failed to get contacts: {e}")
            return ServiceResult.error(str(e))

    def create_contact(self, user_id: str, contact_type, contact_value: str,
                       is_primary: bool = False) -> ServiceResult:
        """创建联系方式"""
        try:
            # 如果设为主联系方式，先取消其他主联系方式
            if is_primary:
                existing = self.contact_crud.find_by_user_id(user_id)
                for c in existing:
                    if c.is_primary:
                        self.contact_crud.modify(
                            filters={"uuid": c.uuid}, updates={"is_primary": False}
                        )

            contact = MUserContact(
                user_id=user_id,
                contact_type=contact_type,
                contact_value=contact_value,
                is_primary=is_primary,
                is_active=True,
            )
            self.contact_crud.add(contact)
            return ServiceResult.success({"created": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to create contact: {e}")
            return ServiceResult.error(str(e))

    def update_contact(self, contact_uuid: str, **updates) -> ServiceResult:
        """更新联系方式"""
        try:
            contacts = self.contact_crud.find(filters={"uuid": contact_uuid})
            if not contacts:
                return ServiceResult.error("Contact not found")
            contact = contacts[0]

            # 如果设为主联系方式
            if updates.get("is_primary"):
                existing = self.contact_crud.find_by_user_id(contact.user_id)
                for c in existing:
                    if c.is_primary and c.uuid != contact_uuid:
                        self.contact_crud.modify(
                            filters={"uuid": c.uuid}, updates={"is_primary": False}
                        )

            self.contact_crud.modify(filters={"uuid": contact_uuid}, updates=updates)
            return ServiceResult.success({"updated": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to update contact: {e}")
            return ServiceResult.error(str(e))

    def delete_contact(self, contact_uuid: str) -> ServiceResult:
        """删除联系方式"""
        try:
            self.contact_crud.delete(filters={"uuid": contact_uuid})
            return ServiceResult.success({"deleted": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to delete contact: {e}")
            return ServiceResult.error(str(e))

    def get_contact(self, contact_uuid: str) -> ServiceResult:
        """获取单个联系方式"""
        try:
            contacts = self.contact_crud.find(filters={"uuid": contact_uuid})
            if not contacts:
                return ServiceResult.error("Contact not found")
            return ServiceResult.success(contacts[0])
        except Exception as e:
            GLOG.ERROR(f"Failed to get contact: {e}")
            return ServiceResult.error(str(e))
