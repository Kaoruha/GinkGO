# Upstream: ApiKeyService
# Downstream: MySQL Database (api_keys表)
# Role: API Key CRUD 操作 - 提供 API Key 的增删改查基础功能


from typing import List, Optional, Dict
from datetime import datetime, timedelta

from ginkgo.data.models.model_api_key import MApiKey, PermissionType
from ginkgo.data.models.model_live_account import MLiveAccount
from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.libs import GLOG
from ginkgo.data.services.encryption_service import get_encryption_service
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class ApiKeyCRUD(BaseCRUD[MApiKey]):
    """API Key CRUD 操作"""

    _model_class = MApiKey

    def __init__(self):
        super().__init__(MApiKey)
    """API Key CRUD 操作"""

    def create_api_key(
        self,
        name: str,
        key_value: str,
        permissions: str = "read",
        user_id: str = None,
        description: str = None,
        expires_at: datetime = None
    ) -> Optional[MApiKey]:
        """
        创建 API Key

        Args:
            name: Key 名称
            key_value: 原始 API Key
            permissions: 权限列表，逗号分隔 (read/trade/admin)
            user_id: 用户 ID（可选，用于限制访问范围）
            description: 备注说明
            expires_at: 过期时间

        Returns:
            MApiKey: 创建的 API Key 对象
        """
        try:
            # 验证权限
            for perm in permissions.split(','):
                if not PermissionType.validate(perm.strip()):
                    GLOG.ERROR(f"Invalid permission: {perm}")
                    return None

            # 生成哈希和前缀
            key_hash = MApiKey.hash_key(key_value)
            key_prefix = MApiKey.generate_prefix(key_value)

            # 加密原始 key
            encryption_service = get_encryption_service()
            encrypt_result = encryption_service.encrypt_credential(key_value)
            key_encrypted = encrypt_result.data.get("encrypted_credential") if encrypt_result.success else None

            # 创建对象
            api_key = MApiKey(
                user_id=user_id,
                name=name,
                key_hash=key_hash,
                key_prefix=key_prefix,
                key_encrypted=key_encrypted,
                permissions=permissions,
                description=description,
                expires_at=expires_at,
                is_active=True,
                last_used_at=None
            )

            # 保存到数据库
            self.add(api_key)

            GLOG.INFO(f"API Key created: {api_key.uuid} (name: {name})")
            return api_key

        except Exception as e:
            GLOG.ERROR(f"Failed to create API Key: {e}")
            return None

    def get_api_key_by_uuid(self, uuid: str) -> Optional[MApiKey]:
        """
        根据 UUID 获取 API Key

        Args:
            uuid: API Key UUID

        Returns:
            MApiKey: API Key 对象
        """
        try:
            result = self.find(filters={"uuid": uuid, "is_del": False})
            if result and len(result) > 0:
                return result[0]
            return None
        except Exception as e:
            GLOG.ERROR(f"Failed to get API Key: {e}")
            return None

    def get_api_keys_by_user(self, user_id: str) -> List[MApiKey]:
        """
        获取用户的所有 API Key

        Args:
            user_id: 用户 ID

        Returns:
            list: API Key 列表
        """
        try:
            result = self.find(
                filters={"user_id": user_id, "is_del": False},
                order_by="create_at",
                desc_order=True
            )
            return result or []
        except Exception as e:
            GLOG.ERROR(f"Failed to get API Keys: {e}")
            return []

    def get_all_api_keys(self, page: int = 1, page_size: int = 50) -> Dict:
        """
        获取所有 API Key（分页）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            dict: {items: list, total: int, page: int, page_size: int}
        """
        try:
            result = self.find(
                filters={"is_del": False},
                order_by="create_at",
                desc_order=True,
                page=page - 1,  # Convert to 0-based page numbering
                page_size=page_size
            )

            # 获取总数
            total = self.count(filters={"is_del": False})

            return {
                "items": result or [],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        except Exception as e:
            GLOG.ERROR(f"Failed to get all API Keys: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    def update_api_key(
        self,
        uuid: str,
        name: str = None,
        permissions: str = None,
        is_active: bool = None,
        description: str = None,
        expires_at: datetime = None
    ) -> bool:
        """
        更新 API Key

        Args:
            uuid: API Key UUID
            name: 新名称
            permissions: 新权限
            is_active: 是否激活
            description: 新描述
            expires_at: 新过期时间

        Returns:
            bool: 是否更新成功
        """
        try:
            # 验证 API Key 存在
            api_key = self.get_api_key_by_uuid(uuid)
            if not api_key:
                GLOG.ERROR(f"API Key not found: {uuid}")
                return False

            # 验证权限
            if permissions is not None:
                for perm in permissions.split(','):
                    if not PermissionType.validate(perm.strip()):
                        GLOG.ERROR(f"Invalid permission: {perm}")
                        return False

            # 构建更新字典
            updates = {}
            if name is not None:
                updates["name"] = name
            if permissions is not None:
                updates["permissions"] = permissions
            if is_active is not None:
                updates["is_active"] = is_active
            if description is not None:
                updates["description"] = description
            if expires_at is not None:
                updates["expires_at"] = expires_at

            if updates:
                updates["update_at"] = datetime.datetime.now()
                self.modify(filters={"uuid": uuid}, updates=updates)

            GLOG.INFO(f"API Key updated: {uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to update API Key: {e}")
            return False

    def delete_api_key(self, uuid: str) -> bool:
        """
        删除 API Key（软删除）

        Args:
            uuid: API Key UUID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 验证 API Key 存在
            api_key = self.get_api_key_by_uuid(uuid)
            if not api_key:
                GLOG.ERROR(f"API Key not found: {uuid}")
                return False

            # 使用 modify 方法进行软删除（设置 is_del=True）
            self.modify(filters={"uuid": uuid}, updates={"is_del": True})

            GLOG.INFO(f"API Key deleted: {uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to delete API Key: {e}")
            return False

    def verify_api_key(self, key_value: str, required_permission: str = None) -> Optional[MApiKey]:
        """
        验证 API Key

        Args:
            key_value: 原始 API Key
            required_permission: 需要的权限 (read/trade/admin)

        Returns:
            MApiKey: API Key 对象，验证失败返回 None
        """
        try:
            key_hash = MApiKey.hash_key(key_value)
            result = self.find(
                filters={"key_hash": key_hash, "is_del": False},
                page=0,
                page_size=1
            )

            if not result or len(result) == 0:
                return None

            api_key = result[0]

            # 检查状态
            if not api_key.is_active:
                return None

            # 检查过期
            if api_key.is_expired():
                return None

            # 检查权限
            if required_permission and not api_key.check_permission(required_permission):
                return None

            # 更新最后使用时间
            self.modify(filters={"uuid": api_key.uuid}, updates={"last_used_at": datetime.datetime.now()})

            return api_key

        except Exception as e:
            GLOG.ERROR(f"Failed to verify API Key: {e}")
            return None

    def update_last_used(self, uuid: str) -> bool:
        """
        更新最后使用时间

        Args:
            uuid: API Key UUID

        Returns:
            bool: 是否更新成功
        """
        try:
            self.modify(filters={"uuid": uuid}, updates={"last_used_at": datetime.datetime.now()})
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to update last used: {e}")
            return False

    def reveal_api_key(self, uuid: str) -> Optional[str]:
        """
        解密并返回完整的 API Key

        Args:
            uuid: API Key UUID

        Returns:
            str: 原始 API Key，失败返回 None
        """
        try:
            api_key = self.get_api_key_by_uuid(uuid)
            if not api_key:
                GLOG.ERROR(f"API Key not found: {uuid}")
                return None

            if not api_key.key_encrypted:
                GLOG.ERROR(f"API Key {uuid} was created before encryption was enabled")
                return None

            # 解密 key
            encryption_service = get_encryption_service()
            decrypt_result = encryption_service.decrypt_credential(api_key.key_encrypted)

            if decrypt_result.success:
                return decrypt_result.data.get("credential")
            else:
                GLOG.ERROR(f"Failed to decrypt API Key: {decrypt_result.message}")
                return None

        except Exception as e:
            GLOG.ERROR(f"Failed to reveal API Key: {e}")
            return None
