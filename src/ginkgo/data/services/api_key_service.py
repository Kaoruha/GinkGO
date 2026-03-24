# Upstream: FastAPI Router
# Downstream: ApiKeyCRUD, Database (api_keys表)
# Role: API Key 业务逻辑层 - 提供 API Key 的创建、查询、验证、权限检查等业务功能


import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from ginkgo.data.crud.api_key_crud import ApiKeyCRUD
from ginkgo.data.models.model_api_key import MApiKey, PermissionType
from ginkgo.data.models.model_live_account import ExchangeType, EnvironmentType
from ginkgo.libs import GLOG
from ginkgo.data.services.encryption_service import get_encryption_service


class ApiKeyService:
    """API Key 服务"""

    def __init__(self):
        self.crud = ApiKeyCRUD()

    def create_api_key(
        self,
        name: str,
        permissions: List[str] = None,
        user_id: str = None,
        description: str = None,
        expires_days: int = None,
        auto_generate: bool = False
    ) -> Dict:
        """
        创建 API Key

        Args:
            name: Key 名称
            permissions: 权限列表 ["read", "trade", "admin"]
            user_id: 用户 ID（可选，用于限制访问范围）
            description: 备注说明
            expires_days: 有效期（天），None 表示永久
            auto_generate: 是否自动生成 Key 值

        Returns:
            dict: {
                "success": bool,
                "data": {
                    "uuid": str,
                    "name": str,
                    "key_value": str,  # 仅在创建时返回一次
                    "prefix": str,
                    "permissions": str,
                    "expires_at": str
                },
                "message": str
            }
        """
        try:
            # 处理权限
            if permissions is None:
                permissions = [PermissionType.READ]
            permissions_str = ",".join(permissions)

            # 处理过期时间
            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)

            # 生成或使用提供的 Key
            key_value = None
            if auto_generate:
                # 生成格式: ginkgo-{hash}
                # hash 部分使用 SHA256 的前 32 位
                import hashlib
                import secrets
                random_part = secrets.token_hex(16)  # 32 位随机字符串
                hash_input = f"{name}-{random_part}-{uuid.uuid4().hex[:8]}"
                hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:32]
                key_value = f"ginkgo-{hash_value}"

            # 创建 API Key
            api_key = self.crud.create_api_key(
                name=name,
                key_value=key_value,
                permissions=permissions_str,
                user_id=user_id,
                description=description,
                expires_at=expires_at
            )

            if not api_key:
                return {
                    "success": False,
                    "message": "Failed to create API Key"
                }

            return {
                "success": True,
                "data": {
                    "uuid": api_key.uuid,
                    "name": api_key.name,
                    "key_value": key_value,  # 仅此一次返回
                    "key_prefix": api_key.key_prefix,
                    "permissions": api_key.permissions,
                    "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                    "is_active": api_key.is_active,
                    "user_id": api_key.user_id
                },
                "message": "API Key created successfully"
            }

        except Exception as e:
            GLOG.ERROR(f"Error creating API Key: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def get_api_key(self, uuid: str) -> Dict:
        """
        获取 API Key 详情

        Args:
            uuid: API Key UUID

        Returns:
            dict: API Key 信息（不包含原始 key_value）
        """
        try:
            api_key = self.crud.get_api_key_by_uuid(uuid)

            if not api_key:
                return {
                    "success": False,
                    "message": "API Key not found"
                }

            # 获取账号信息
            account = self.crud._verify_account(api_key.account_uuid)

            return {
                "success": True,
                "data": {
                    "uuid": api_key.uuid,
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "permissions": api_key.permissions,
                    "permissions_list": api_key.get_permissions_list(),
                    "is_active": api_key.is_active,
                    "is_expired": api_key.is_expired(),
                    "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                    "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                    "description": api_key.description,
                    "created_at": api_key.create_at.isoformat(),
                    "user_id": api_key.user_id
                }
            }

        except Exception as e:
            GLOG.ERROR(f"Error getting API Key: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def list_api_keys(self, user_id: str = None) -> Dict:
        """
        获取 API Key 列表

        Args:
            user_id: 用户 ID（可选，为空则返回所有）

        Returns:
            dict: {
                "success": bool,
                "data": {
                    "api_keys": [...]
                }
            }
        """
        try:
            if user_id:
                api_keys = self.crud.get_api_keys_by_user(user_id)
            else:
                result = self.crud.get_all_api_keys(page=1, page_size=100)
                api_keys = result["items"]

            # 转换为返回格式（不包含原始 key_value）
            items = []
            for api_key in api_keys:
                items.append({
                    "uuid": api_key.uuid,
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "permissions": api_key.permissions,
                    "permissions_list": api_key.get_permissions_list(),
                    "is_active": api_key.is_active,
                    "is_expired": api_key.is_expired(),
                    "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                    "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                    "created_at": api_key.create_at.isoformat(),
                    "description": api_key.description,
                    "user_id": api_key.user_id
                })

            return {
                "success": True,
                "data": {
                    "api_keys": items
                }
            }

        except Exception as e:
            GLOG.ERROR(f"Error listing API Keys: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def update_api_key(
        self,
        uuid: str,
        name: str = None,
        permissions: List[str] = None,
        is_active: bool = None,
        description: str = None,
        expires_days: int = None
    ) -> Dict:
        """
        更新 API Key

        Args:
            uuid: API Key UUID
            name: 新名称
            permissions: 新权限列表
            is_active: 是否激活
            description: 新描述
            expires_days: 有效期（天）

        Returns:
            dict: 更新结果
        """
        try:
            # 处理权限
            permissions_str = None
            if permissions is not None:
                # 验证权限
                for perm in permissions:
                    if not PermissionType.validate(perm):
                        return {
                            "success": False,
                            "message": f"Invalid permission: {perm}"
                        }
                permissions_str = ",".join(permissions)

            # 处理过期时间
            expires_at = None
            if expires_days is not None:
                expires_at = datetime.now() + timedelta(days=expires_days)

            # 执行更新
            success = self.crud.update_api_key(
                uuid=uuid,
                name=name,
                permissions=permissions_str,
                is_active=is_active,
                description=description,
                expires_at=expires_at
            )

            if success:
                return {
                    "success": True,
                    "message": "API Key updated successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "API Key not found or update failed"
                }

        except Exception as e:
            GLOG.ERROR(f"Error updating API Key: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def delete_api_key(self, uuid: str) -> Dict:
        """
        删除 API Key

        Args:
            uuid: API Key UUID

        Returns:
            dict: 删除结果
        """
        try:
            success = self.crud.delete_api_key(uuid)

            if success:
                return {
                    "success": True,
                    "message": "API Key deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "API Key not found"
                }

        except Exception as e:
            GLOG.ERROR(f"Error deleting API Key: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def verify_api_key(self, key_value: str, required_permission: str = None) -> Optional[MApiKey]:
        """
        验证 API Key

        Args:
            key_value: 原始 API Key
            required_permission: 需要的权限

        Returns:
            MApiKey: API Key 对象，验证失败返回 None
        """
        try:
            return self.crud.verify_api_key(key_value, required_permission)
        except Exception as e:
            GLOG.ERROR(f"Error verifying API Key: {e}")
            return None

    def check_permission(self, key_value: str, permission: str) -> bool:
        """
        检查 API Key 是否有指定权限

        Args:
            key_value: 原始 API Key
            permission: 需要的权限

        Returns:
            bool: 是否有权限
        """
        try:
            api_key = self.verify_api_key(key_value, permission)
            return api_key is not None
        except Exception as e:
            GLOG.ERROR(f"Error checking permission: {e}")
            return False

    def reveal_api_key(self, uuid: str) -> Dict:
        """
        解密并返回完整的 API Key

        Args:
            uuid: API Key UUID

        Returns:
            dict: {
                "success": bool,
                "data": {
                    "uuid": str,
                    "name": str,
                    "key_value": str  # 完整的 API Key
                },
                "message": str
            }
        """
        try:
            # 先获取基本信息
            api_key = self.crud.get_api_key_by_uuid(uuid)
            if not api_key:
                return {
                    "success": False,
                    "message": "API Key 不存在"
                }

            # 解密获取完整 key
            key_value = self.crud.reveal_api_key(uuid)
            if not key_value:
                return {
                    "success": False,
                    "message": "无法解密 API Key，可能是旧版本创建的 Key"
                }

            return {
                "success": True,
                "data": {
                    "uuid": api_key.uuid,
                    "name": api_key.name,
                    "key_value": key_value,
                    "key_prefix": api_key.key_prefix,
                    "permissions": api_key.permissions,
                    "permissions_list": api_key.get_permissions_list()
                },
                "message": "success"
            }

        except Exception as e:
            GLOG.ERROR(f"Error revealing API Key: {e}")
            return {
                "success": False,
                "message": str(e)
            }
