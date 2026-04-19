"""
系统设置相关API路由
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import bcrypt

from ginkgo.data.containers import container
from ginkgo.data.models import MUserCredential, MUser
from ginkgo.enums import CONTACT_TYPES, CONTACT_METHOD_STATUS_TYPES
from ginkgo.data.services.user_service import UserService
from ginkgo.data.services.user_group_service import UserGroupService
from ginkgo.data.services.notification_service import NotificationService
from core.logging import logger
from core.response import ok

router = APIRouter()


# ==================== 通用函数 ====================

def get_user_service() -> UserService:
    """获取UserService实例"""
    return UserService()


def get_user_group_service() -> UserGroupService:
    """获取UserGroupService实例"""
    return UserGroupService()


def get_notification_service() -> NotificationService:
    """获取NotificationService实例"""
    return NotificationService()


def hash_password(password: str) -> str:
    """对密码进行哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# ==================== 用户管理 ====================

class UserSummary(BaseModel):
    """用户摘要"""
    uuid: str
    username: str
    display_name: str
    email: str
    roles: List[str]
    status: str  # active, disabled
    created_at: str


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str
    password: str
    display_name: str
    email: str
    roles: List[str]
    status: str = "active"


class UserUpdate(BaseModel):
    """更新用户请求"""
    display_name: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    status: Optional[str] = None


@router.get("/users")
async def list_users(
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """获取用户列表"""
    try:
        user_service = get_user_service()

        # 构建查询条件
        filters = {"is_del": False}
        if status == "active":
            filters["is_active"] = True
        elif status == "disabled":
            filters["is_active"] = False

        # 通过 Service 查询用户
        result = user_service.list_users(**filters)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list users"
            )

        users = result.data

        # 搜索过滤
        if search:
            search_lower = search.lower()
            users = [u for u in users if search_lower in u.username.lower() or (u.display_name and search_lower in u.display_name.lower())]

        result_list = []
        for user in users:
            # 跳过没有用户名的记录
            if not user.username:
                continue

            # 获取关联的凭证（get_credential 返回单个对象或 None）
            credential = user_service.get_credential(user.uuid)

            # 确定角色
            roles = ["admin"] if credential and credential.is_admin else []

            # 确定状态
            user_status = "active" if user.is_active and (credential and credential.is_active) else "disabled"

            result_list.append({
                "uuid": user.uuid,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "email": user.email or "",
                "roles": roles,
                "status": user_status,
                "created_at": user.create_at.isoformat() if user.create_at else datetime.utcnow().isoformat() + "Z"
            })

        return ok(data=result_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.post("/users", status_code=201)
async def create_user(data: UserCreate):
    """创建用户"""
    try:
        user_service = get_user_service()

        # 检查用户名是否已存在
        existing_result = user_service.list_users(username=data.username, is_del=False)
        existing_users = existing_result.data if existing_result.success else []
        if existing_users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )

        # 哈希密码
        password_hash = hash_password(data.password)
        is_admin = "admin" in data.roles
        is_active = data.status == "active"

        # 通过 Service 创建用户（含凭据）
        result = user_service.create_user(
            username=data.username,
            display_name=data.display_name,
            email=data.email,
            description=f"User created via API: {data.username}",
            password_hash=password_hash,
        )
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        created_user_data = result.data

        # 如果需要设置管理员或非默认 active 状态，单独更新凭据
        if is_admin or not is_active:
            credential = user_service.get_credential(created_user_data["uuid"])
            if credential:
                cred_updates = {}
                if is_admin:
                    cred_updates["is_admin"] = True
                if not is_active:
                    cred_updates["is_active"] = False
                if cred_updates:
                    user_service.update_user(created_user_data["uuid"], **cred_updates)
        # 如果非 active，还需更新用户本身
        if not is_active:
            user_service.update_user(created_user_data["uuid"], is_active=False)

        logger.info(f"User created: {data.username} (uuid={created_user_data['uuid']})")

        return ok(data={
            "uuid": created_user_data["uuid"],
            "username": data.username,
            "display_name": data.display_name,
            "email": data.email,
            "roles": data.roles,
            "status": data.status,
            "created_at": created_user_data.get("created_at") or datetime.utcnow().isoformat() + "Z"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.put("/users/{uuid}")
async def update_user(uuid: str, data: UserUpdate):
    """更新用户"""
    try:
        user_service = get_user_service()

        # 构建更新参数
        updates = {}
        if data.display_name is not None:
            updates["display_name"] = data.display_name

        if data.email is not None:
            updates["email"] = data.email

        if data.status is not None:
            updates["is_active"] = (data.status == "active")

        # 凭据相关更新
        if data.roles is not None:
            updates["is_admin"] = "admin" in data.roles

        if updates:
            result = user_service.update_user(uuid, **updates)
            if not result.success:
                if "not found" in result.error.lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user"
                )

        logger.info(f"User updated: {uuid}")

        return ok(message=f"User {uuid} updated")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.post("/users/{uuid}/reset-password")
async def reset_user_password(uuid: str, data: dict):
    """重置用户密码"""
    try:
        user_service = get_user_service()

        new_password = data.get("new_password", "123456")
        new_password_hash = hash_password(new_password)

        result = user_service.reset_password(uuid, new_password_hash)
        if not result.success:
            if "not found" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User credential not found"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )

        logger.info(f"Password reset for user: {uuid}")

        return ok(data={"new_password": new_password}, message=f"Password for user {uuid} has been reset")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.delete("/users/{uuid}")
async def delete_user(uuid: str):
    """删除用户"""
    try:
        user_service = get_user_service()

        result = user_service.delete_user(uuid)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User deleted: {uuid}")

        return ok(message=f"User {uuid} deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


# ==================== 用户联系方式管理 ====================

class UserContactSummary(BaseModel):
    """用户联系方式摘要"""
    uuid: str
    user_id: str
    contact_type: str  # email, webhook
    address: str
    is_primary: bool
    is_active: bool
    created_at: str


class UserContactCreate(BaseModel):
    """创建联系方式请求"""
    contact_type: str  # email, webhook
    address: str
    is_primary: bool = False


class UserContactUpdate(BaseModel):
    """更新联系方式请求"""
    contact_type: Optional[str] = None
    address: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class UserContactTest(BaseModel):
    """测试联系方式请求"""
    address: str
    subject: str = "Ginkgo Test Notification"
    content: str = "This is a test notification from Ginkgo."


@router.get("/users/{user_uuid}/contacts")
async def list_user_contacts(user_uuid: str):
    """获取用户联系方式列表"""
    try:
        user_service = get_user_service()

        # 验证用户存在
        user_result = user_service.get_user(user_uuid)
        if not user_result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 获取联系方式
        contacts_result = user_service.get_contacts(user_uuid)
        if not contacts_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list contacts"
            )

        contacts = contacts_result.data

        result = []
        for contact in contacts:
            contact_type_enum = contact.get_contact_type_enum()
            result.append({
                "uuid": contact.uuid,
                "user_id": contact.user_id,
                "contact_type": contact_type_enum.name.lower() if contact_type_enum else "email",
                "address": contact.address,
                "is_primary": contact.is_primary,
                "is_active": contact.is_active,
                "created_at": contact.create_at.isoformat() if contact.create_at else datetime.utcnow().isoformat() + "Z"
            })

        return ok(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list contacts"
        )


@router.post("/users/{user_uuid}/contacts", status_code=201)
async def create_user_contact(user_uuid: str, data: UserContactCreate):
    """创建用户联系方式"""
    try:
        user_service = get_user_service()

        # 验证用户存在
        user_result = user_service.get_user(user_uuid)
        if not user_result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 验证联系方式类型
        type_map = {
            "email": CONTACT_TYPES.EMAIL,
            "webhook": CONTACT_TYPES.WEBHOOK
        }
        contact_type_enum = type_map.get(data.contact_type.lower(), CONTACT_TYPES.EMAIL)

        # 通过 Service 创建联系方式
        result = user_service.create_contact(
            user_id=user_uuid,
            contact_type=contact_type_enum,
            contact_value=data.address,
            is_primary=data.is_primary,
        )
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create contact"
            )

        logger.info(f"Contact created for user: {user_uuid}")

        return ok(data={
            "uuid": result.data.get("uuid", "") if isinstance(result.data, dict) else "",
            "user_id": user_uuid,
            "contact_type": data.contact_type,
            "address": data.address,
            "is_primary": data.is_primary,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create contact"
        )


@router.put("/users/contacts/{contact_uuid}")
async def update_user_contact(contact_uuid: str, data: UserContactUpdate):
    """更新用户联系方式"""
    try:
        user_service = get_user_service()

        # 构建更新数据
        updates = {}

        if data.contact_type is not None:
            type_map = {
                "email": CONTACT_TYPES.EMAIL,
                "webhook": CONTACT_TYPES.WEBHOOK
            }
            updates["contact_type"] = type_map.get(data.contact_type.lower(), CONTACT_TYPES.EMAIL).value

        if data.address is not None:
            updates["address"] = data.address

        if data.is_primary is not None:
            updates["is_primary"] = data.is_primary

        if data.is_active is not None:
            updates["is_active"] = data.is_active

        if updates:
            result = user_service.update_contact(contact_uuid, **updates)
            if not result.success:
                if "not found" in result.error.lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Contact not found"
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update contact"
                )

        logger.info(f"Contact updated: {contact_uuid}")

        return ok(message=f"Contact {contact_uuid} updated")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update contact"
        )


@router.delete("/users/contacts/{contact_uuid}")
async def delete_user_contact(contact_uuid: str):
    """删除用户联系方式"""
    try:
        user_service = get_user_service()

        result = user_service.delete_contact(contact_uuid)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        logger.info(f"Contact deleted: {contact_uuid}")

        return ok(message=f"Contact {contact_uuid} deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete contact"
        )


@router.post("/users/contacts/{contact_uuid}/test")
async def test_user_contact(contact_uuid: str, data: UserContactTest):
    """测试用户联系方式（发送测试通知）"""
    try:
        user_service = get_user_service()

        # 获取联系方式
        contact_result = user_service.get_contact(contact_uuid)
        if not contact_result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        contact = contact_result.data
        contact_type = contact.get_contact_type_enum()

        # 根据联系方式类型发送测试通知
        if contact_type == CONTACT_TYPES.EMAIL:
            # TODO: 实现邮件发送
            logger.info(f"Email test sent to: {data.address}")
            return ok(data={
                "detail": "Email sending not implemented yet"
            }, message=f"Test email sent to {data.address}")
        elif contact_type == CONTACT_TYPES.WEBHOOK:
            # TODO: 实现Webhook调用
            import requests
            try:
                response = requests.post(
                    data.address,
                    json={
                        "subject": data.subject,
                        "content": data.content,
                        "test": True
                    },
                    timeout=10
                )
                return ok(data={
                    "detail": f"Status code: {response.status_code}"
                }, message=f"Test webhook sent to {data.address}")
            except Exception as e:
                logger.error(f"Webhook test failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Webhook test failed: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported contact type: {contact_type}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test contact"
        )


@router.post("/users/contacts/{contact_uuid}/set-primary")
async def set_primary_contact(contact_uuid: str):
    """设置为主联系方式"""
    try:
        user_service = get_user_service()

        # 获取联系方式
        contact_result = user_service.get_contact(contact_uuid)
        if not contact_result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        contact = contact_result.data

        # 取消该用户的其他主联系方式
        contacts_result = user_service.get_contacts(contact.user_id)
        if contacts_result.success:
            for c in contacts_result.data:
                if c.uuid != contact_uuid and c.is_primary:
                    user_service.update_contact(c.uuid, is_primary=False)

        # 设置为主联系方式
        user_service.update_contact(contact_uuid, is_primary=True)

        logger.info(f"Primary contact set: {contact_uuid}")

        return ok(message=f"Contact {contact_uuid} set as primary")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting primary contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set primary contact"
        )


# ==================== 用户组管理 ====================

class UserGroupSummary(BaseModel):
    """用户组摘要"""
    uuid: str
    name: str
    description: Optional[str]
    user_count: int
    permissions: List[str]


class UserGroupCreate(BaseModel):
    """创建用户组请求"""
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


class UserGroupUpdate(BaseModel):
    """更新用户组请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


@router.get("/user-groups")
async def list_user_groups():
    """获取用户组列表"""
    try:
        group_service = get_user_group_service()

        result = group_service.list_groups(is_del=False)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list user groups"
            )

        raw_groups = result.data
        group_list = []
        for group_data in raw_groups:
            group_uuid = group_data["uuid"]
            member_count = group_service.count_members(group_uuid)

            group_list.append({
                "uuid": group_uuid,
                "name": group_data["name"],
                "description": group_data.get("description", ""),
                "user_count": member_count,
                "permissions": []
            })

        return ok(data=group_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing user groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list user groups"
        )


@router.post("/user-groups", status_code=201)
async def create_user_group(data: UserGroupCreate):
    """创建用户组"""
    try:
        group_service = get_user_group_service()

        # 检查组名是否已存在
        existing_result = group_service.list_groups(is_del=False)
        if existing_result.success:
            existing_groups = existing_result.data
            for g in existing_groups:
                if g["name"] == data.name:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Group name already exists"
                    )

        result = group_service.create_group(
            name=data.name,
            description=data.description or "",
        )
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user group"
            )

        group_data = result.data
        logger.info(f"User group created: {data.name} (uuid={group_data['uuid']})")

        return ok(data={
            "uuid": group_data["uuid"],
            "name": data.name,
            "description": data.description or "",
            "user_count": 0,
            "permissions": data.permissions
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user group"
        )


@router.put("/user-groups/{uuid}")
async def update_user_group(uuid: str, data: UserGroupUpdate):
    """更新用户组"""
    try:
        group_service = get_user_group_service()

        # 构建更新参数
        updates = {}
        if data.name is not None:
            # 检查新名称是否与其他组冲突
            existing_result = group_service.list_groups(is_del=False)
            if existing_result.success:
                for g in existing_result.data:
                    if g["name"] == data.name and g["uuid"] != uuid:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Group name already exists"
                        )
            updates["name"] = data.name

        if data.description is not None:
            updates["description"] = data.description

        if updates:
            result = group_service.update_group(uuid, **updates)
            if not result.success:
                if "not found" in result.error.lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User group not found"
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user group"
                )

        logger.info(f"User group updated: {uuid}")

        return ok(message=f"User group {uuid} updated")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user group"
        )


@router.delete("/user-groups/{uuid}")
async def delete_user_group(uuid: str):
    """删除用户组"""
    try:
        group_service = get_user_group_service()

        result = group_service.delete_group(uuid)
        if not result.success:
            if "not found" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User group not found"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user group"
            )

        logger.info(f"User group deleted: {uuid}")

        return ok(message=f"User group {uuid} deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user group"
        )


# ==================== 用户组成员管理 ====================

class GroupMemberSummary(BaseModel):
    """组成员摘要"""
    uuid: str
    user_uuid: str
    username: str
    display_name: str
    email: str


@router.get("/user-groups/{group_uuid}/members")
async def list_group_members(group_uuid: str):
    """获取用户组成员列表"""
    try:
        group_service = get_user_group_service()
        user_service = get_user_service()

        # 检查用户组是否存在
        group_result = group_service.get_group(group_uuid)
        if not group_result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found"
            )

        # 获取组成员映射
        members_result = group_service.list_members(group_uuid)
        if not members_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list group members"
            )

        members = members_result.data
        result = []
        for member_data in members:
            user_uuid = member_data["uuid"]
            # 获取用户信息
            user_result = user_service.get_user(user_uuid)
            if user_result.success:
                user = user_result.data
                result.append({
                    "uuid": member_data.get("group_uuid", ""),
                    "user_uuid": user.uuid,
                    "username": user.username,
                    "display_name": user.display_name or user.username,
                    "email": user.email or ""
                })

        return ok(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing group members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list group members"
        )


@router.post("/user-groups/{group_uuid}/members", status_code=201)
async def add_group_member(group_uuid: str, data: dict):
    """添加用户到用户组"""
    try:
        group_service = get_user_group_service()
        user_service = get_user_service()

        user_uuid = data.get("user_uuid")
        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_uuid is required"
            )

        # 检查用户是否存在
        user_result = user_service.get_user(user_uuid)
        if not user_result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 添加成员到用户组
        result = group_service.add_member(user_uuid, group_uuid)
        if not result.success:
            if "already" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already in this group"
                )
            if "not found" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User group not found"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add user to group"
            )

        mapping_data = result.data
        logger.info(f"User {user_uuid} added to group {group_uuid}")

        return ok(data={"mapping_uuid": mapping_data.get("mapping_uuid", "")}, message="User added to group")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding group member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add user to group"
        )


@router.delete("/user-groups/{group_uuid}/members/{user_uuid}")
async def remove_group_member(group_uuid: str, user_uuid: str):
    """从用户组移除用户"""
    try:
        group_service = get_user_group_service()

        result = group_service.remove_member(user_uuid, group_uuid)
        if not result.success:
            if "not found" in result.error.lower() or "not a member" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User is not in this group"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove user from group"
            )

        logger.info(f"User {user_uuid} removed from group {group_uuid}")

        return ok(message="User removed from group")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing group member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove user from group"
        )


# ==================== 通知管理 ====================

class NotificationTemplateSummary(BaseModel):
    """通知模板摘要"""
    uuid: str
    name: str
    type: str  # email, discord, system
    subject: str
    enabled: bool
    updated_at: str


class NotificationHistoryItem(BaseModel):
    """通知历史记录"""
    uuid: str
    type: str
    subject: str
    recipient: str
    status: str  # success, failed
    created_at: str
    error: Optional[str] = None


class NotificationTemplateCreate(BaseModel):
    """创建通知模板请求"""
    name: str
    type: str  # email, discord, system
    subject: str
    content: str
    enabled: bool = True


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板请求"""
    name: Optional[str] = None
    type: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[bool] = None


def get_notification_recipient_service():
    """获取NotificationRecipientService实例"""
    return container.notification_recipient_service()


@router.get("/notifications/templates")
async def list_notification_templates():
    """获取通知模板列表"""
    try:
        notification_service = get_notification_service()

        result = notification_service.list_templates(is_del=False)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list notification templates"
            )

        templates = result.data

        result_list = []
        for tpl in templates:
            # 获取模板类型
            template_type = tpl.get_template_type_enum()
            type_str = template_type.name.lower() if template_type else "text"

            result_list.append({
                "uuid": tpl.uuid,
                "name": tpl.template_name,
                "type": type_str,
                "subject": tpl.subject or "",
                "enabled": tpl.is_active,
                "updated_at": tpl.update_at.isoformat() if tpl.update_at else datetime.utcnow().isoformat() + "Z"
            })

        return ok(data=result_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing notification templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list notification templates"
        )


@router.post("/notifications/templates", status_code=201)
async def create_notification_template(data: NotificationTemplateCreate):
    """创建通知模板"""
    try:
        from ginkgo.data.models.model_notification_template import MNotificationTemplate
        from ginkgo.enums import TEMPLATE_TYPES

        notification_service = get_notification_service()

        # 映射类型字符串到枚举
        type_map = {
            "email": TEMPLATE_TYPES.TEXT,
            "discord": TEMPLATE_TYPES.MARKDOWN,
            "system": TEMPLATE_TYPES.TEXT
        }
        template_type = type_map.get(data.type.lower(), TEMPLATE_TYPES.TEXT)

        # 生成 template_id
        import uuid
        template_id = f"tpl_{uuid.uuid4().hex[:8]}"

        template = MNotificationTemplate(
            template_id=template_id,
            template_name=data.name,
            template_type=template_type.value,
            subject=data.subject,
            content=data.content,
            is_active=data.enabled
        )

        result = notification_service.create_template(template)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notification template"
            )

        created_uuid = result.data.get("uuid") if isinstance(result.data, dict) else result.data
        logger.info(f"Notification template created: {data.name}")

        return ok(data={
            "uuid": created_uuid,
            "name": data.name,
            "type": data.type,
            "subject": data.subject,
            "enabled": data.enabled,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification template"
        )


@router.put("/notifications/templates/{uuid}")
async def update_notification_template(uuid: str, data: NotificationTemplateUpdate):
    """更新通知模板"""
    try:
        from ginkgo.enums import TEMPLATE_TYPES

        notification_service = get_notification_service()

        # 检查模板是否存在
        if not notification_service.template_exists(uuid):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification template not found"
            )

        # 构建更新数据
        update_dict = {}
        if data.name is not None:
            update_dict["template_name"] = data.name

        if data.type is not None:
            type_map = {
                "email": TEMPLATE_TYPES.TEXT,
                "discord": TEMPLATE_TYPES.MARKDOWN,
                "system": TEMPLATE_TYPES.TEXT
            }
            template_type = type_map.get(data.type.lower(), TEMPLATE_TYPES.TEXT)
            update_dict["template_type"] = template_type.value

        if data.subject is not None:
            update_dict["subject"] = data.subject

        if data.content is not None:
            update_dict["content"] = data.content

        if data.enabled is not None:
            update_dict["is_active"] = data.enabled

        if update_dict:
            notification_service.update_template(uuid, **update_dict)

        logger.info(f"Notification template updated: {uuid}")

        return ok(message=f"Notification template {uuid} updated")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification template"
        )


@router.delete("/notifications/templates/{uuid}")
async def delete_notification_template(uuid: str):
    """删除通知模板"""
    try:
        notification_service = get_notification_service()

        result = notification_service.delete_template(uuid)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification template not found"
            )

        logger.info(f"Notification template deleted: {uuid}")

        return ok(message=f"Notification template {uuid} deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification template"
        )


@router.post("/notifications/templates/{uuid}/test")
async def test_notification_template(uuid: str):
    """测试通知模板"""
    try:
        notification_service = get_notification_service()

        if not notification_service.template_exists(uuid):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification template not found"
            )

        # TODO: 实现真实的测试发送
        logger.info(f"Test notification template: {uuid}")

        return ok(message="Test notification sent")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing notification template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test notification template"
        )


@router.patch("/notifications/templates/{uuid}")
async def toggle_notification_template(uuid: str, enabled: bool):
    """切换通知模板启用状态"""
    try:
        notification_service = get_notification_service()

        if not notification_service.template_exists(uuid):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification template not found"
            )

        notification_service.update_template(uuid, is_active=enabled)

        logger.info(f"Notification template {uuid} toggled to {enabled}")

        return ok(message=f"Notification template {'enabled' if enabled else 'disabled'}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling notification template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle notification template"
        )


@router.get("/notifications/history")
async def list_notification_history(
    type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取通知历史"""
    try:
        notification_service = get_notification_service()

        # 计算跳过的数量
        offset = (page - 1) * page_size

        # 构建查询条件
        filters = {"is_del": False}
        # TODO: 添加类型筛选支持

        result = notification_service.list_records(
            filters=filters,
            limit=page_size,
            offset=offset,
            sort=[("create_at", -1)]
        )
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list notification history"
            )

        records = result.data
        result_list = []
        for record in records:
            # 获取状态
            from ginkgo.enums import NOTIFICATION_STATUS_TYPES
            status_enum = NOTIFICATION_STATUS_TYPES.from_int(record.status)
            status_str = "success" if status_enum == NOTIFICATION_STATUS_TYPES.SENT else "failed"

            # 从 channels 中获取类型
            channel = record.channels[0] if record.channels else "system"

            result_list.append({
                "uuid": record.uuid,
                "type": channel,
                "subject": record.message_id,
                "recipient": ", ".join(record.channels),
                "status": status_str,
                "created_at": record.create_at.isoformat() if record.create_at else datetime.utcnow().isoformat() + "Z",
                "error": getattr(record, 'error_message', None)
            })

        return ok(data=result_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing notification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list notification history"
        )


# ==================== 通知接收人管理 ====================

class UserInfo(BaseModel):
    """用户信息"""
    uuid: str
    username: str
    display_name: Optional[str] = None


class UserGroupInfo(BaseModel):
    """用户组信息"""
    uuid: str
    name: str


class NotificationRecipientSummary(BaseModel):
    """通知接收人摘要"""
    uuid: str
    name: str
    recipient_type: str  # USER, USER_GROUP
    user_id: Optional[str] = None
    user_group_id: Optional[str] = None
    user_info: Optional[UserInfo] = None
    user_group_info: Optional[UserGroupInfo] = None
    description: Optional[str] = None
    is_default: bool
    created_at: str


class NotificationRecipientCreate(BaseModel):
    """创建通知接收人请求"""
    name: str
    recipient_type: str  # USER, USER_GROUP
    user_id: Optional[str] = None
    user_group_id: Optional[str] = None
    is_default: bool = False
    description: Optional[str] = None


class NotificationRecipientUpdate(BaseModel):
    """更新通知接收人请求"""
    name: Optional[str] = None
    recipient_type: Optional[str] = None
    user_id: Optional[str] = None
    user_group_id: Optional[str] = None
    is_default: Optional[bool] = None
    description: Optional[str] = None


@router.get("/notifications/recipients")
async def list_notification_recipients():
    """获取全局通知接收人列表"""
    try:
        service = get_notification_recipient_service()
        result = service.list_all()

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )

        return ok(data=result.data["recipients"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing notification recipients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list notification recipients"
        )


@router.post("/notifications/recipients", status_code=201)
async def create_notification_recipient(data: NotificationRecipientCreate):
    """创建通知接收人"""
    try:
        service = get_notification_recipient_service()

        result = service.add_recipient(
            name=data.name,
            recipient_type=data.recipient_type,
            user_id=data.user_id,
            user_group_id=data.user_group_id,
            is_default=data.is_default,
            description=data.description
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )

        recipient_data = result.data
        return ok(data={
            "uuid": recipient_data["uuid"],
            "name": recipient_data["name"],
            "recipient_type": recipient_data["recipient_type"].lower(),
            "user_id": recipient_data["user_id"],
            "user_group_id": recipient_data["user_group_id"],
            "description": recipient_data["description"],
            "is_default": recipient_data["is_default"],
            "created_at": datetime.utcnow().isoformat() + "Z"
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error creating notification recipient: {e}\nTraceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification recipient: {str(e)}"
        )


@router.put("/notifications/recipients/{uuid}")
async def update_notification_recipient(uuid: str, data: NotificationRecipientUpdate):
    """更新通知接收人"""
    try:
        service = get_notification_recipient_service()

        result = service.update_recipient(
            uuid=uuid,
            name=data.name,
            recipient_type=data.recipient_type,
            user_id=data.user_id,
            user_group_id=data.user_group_id,
            is_default=data.is_default,
            description=data.description
        )

        if not result.is_success():
            # Check if it's a "not found" error
            if "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )

        return ok(message="Notification recipient updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification recipient {uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification recipient"
        )


@router.delete("/notifications/recipients/{uuid}")
async def delete_notification_recipient(uuid: str):
    """删除通知接收人"""
    try:
        service = get_notification_recipient_service()

        result = service.delete_recipient(uuid=uuid)

        if not result.is_success():
            # Check if it's a "not found" error
            if "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )

        return ok(message="Notification recipient deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification recipient {uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification recipient"
        )


@router.patch("/notifications/recipients/{uuid}/toggle")
async def toggle_notification_recipient(uuid: str):
    """切换通知接收人默认状态"""
    try:
        service = get_notification_recipient_service()

        result = service.toggle_default(uuid=uuid)

        if not result.is_success():
            # Check if it's a "not found" error
            if "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )

        return ok(data={"is_default": result.data["is_default"]}, message="Notification recipient toggled successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification recipient {uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification recipient"
        )


@router.post("/notifications/recipients/{uuid}/test")
async def test_notification_recipient(uuid: str):
    """测试通知接收人 - 发送测试通知到所有联系方式"""
    try:
        service = get_notification_recipient_service()

        # 获取接收人的联系方式
        contacts_result = service.get_recipient_contacts(uuid=uuid)

        if not contacts_result.is_success():
            # Check if it's a "not found" error
            if "not found" in contacts_result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=contacts_result.message
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=contacts_result.message
            )

        contacts_data = contacts_result.data
        contacts = contacts_data.get("contacts", [])
        contact_count = len(contacts)

        if contact_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient has no valid contact addresses"
            )

        recipient_name = contacts_data.get("recipient_name", "Unknown")
        recipient_type = contacts_data.get("recipient_type", "UNKNOWN")

        # 准备测试消息内容
        from datetime import datetime
        test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        test_content = f"🧪 测试通知 - 接收人: {recipient_name} ({recipient_type}) | 发送时间: {test_time}"

        # 发送测试通知到每个联系方式
        success_count = 0
        failed_count = 0
        results = []

        for contact in contacts:
            contact_type = contact.get("type")
            address = contact.get("address")

            try:
                if contact_type in ["DISCORD", "WEBHOOK"]:
                    # 使用 requests 直接发送 Discord Webhook
                    import requests
                    payload = {
                        "content": test_content.replace("\n", " ").replace("\r", ""),
                        "embeds": [{
                            "title": "🧪 测试通知",
                            "description": f"接收人: **{recipient_name}**\n类型: **{recipient_type}**",
                            "color": 3447003,  # 蓝色
                            "timestamp": datetime.now().isoformat()
                        }]
                    }

                    response = requests.post(
                        address,
                        json=payload,
                        timeout=10
                    )

                    if response.status_code in [200, 204]:
                        success_count += 1
                        results.append(f"{contact_type}: 成功 (HTTP {response.status_code})")
                        logger.info(f"Test notification sent successfully to {address}")
                    else:
                        failed_count += 1
                        results.append(f"{contact_type}: 失败 (HTTP {response.status_code})")
                        logger.warning(f"Test notification failed: HTTP {response.status_code} for {address}")

                elif contact_type == "EMAIL":
                    # Email 暂不支持
                    failed_count += 1
                    results.append(f"{contact_type}: 暂不支持")

                else:
                    failed_count += 1
                    results.append(f"{contact_type}: 未知类型")

            except Exception as e:
                err_name = type(e).__name__
                if "Timeout" in err_name:
                    failed_count += 1
                    results.append(f"{contact_type}: 超时")
                    logger.warning(f"Test notification timeout for {address}")
                elif "Request" in err_name:
                    failed_count += 1
                    results.append(f"{contact_type}: 请求失败 - {str(e)}")
                    logger.error(f"Test notification request failed: {e}")
                else:
                    failed_count += 1
                    results.append(f"{contact_type}: 异常 - {str(e)}")
                    logger.error(f"Test notification error: {e}")

        logger.info(f"Test notification completed for recipient {uuid}: {success_count} success, {failed_count} failed")

        return ok(data={
            "details": results,
            "recipient_name": recipient_name,
            "contact_count": contact_count,
            "success_count": success_count,
            "failed_count": failed_count
        }, message=f"测试通知已发送: {success_count} 成功, {failed_count} 失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing notification recipient {uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test notification recipient: {str(e)}"
        )


# ==================== API接口设置 ====================

class APIKeySummary(BaseModel):
    """API密钥摘要"""
    key_id: str
    name: str
    masked_key: str
    status: str
    expires_at: Optional[str]
    last_used: Optional[str]


class APIStats(BaseModel):
    """API统计"""
    today_calls: int
    month_calls: int
    success_rate: float
    avg_response_time: float


@router.get("/api-keys")
async def list_api_keys():
    """获取API密钥列表"""
    # TODO: 从数据库获取API密钥
    return ok(data=[
        {
            "key_id": "key-1",
            "name": "生产环境密钥",
            "masked_key": "ginkgo_sk_****",
            "status": "active",
            "expires_at": "2025-01-31T00:00:00Z",
            "last_used": "2024-01-30T15:30:00Z"
        }
    ])


@router.post("/api-keys", status_code=201)
async def create_api_key(data: dict):
    """创建API密钥"""
    # TODO: 创建API密钥
    return ok(data={
        "key_id": "new-key",
        "name": data.get("name"),
        "masked_key": "ginkgo_sk_****",
        "status": "active",
        "expires_at": None,
        "last_used": None
    })


@router.get("/api-stats")
async def get_api_stats():
    """获取API统计"""
    # TODO: 获取实际统计数据
    return ok(data={
        "today_calls": 15234,
        "month_calls": 456789,
        "success_rate": 99.8,
        "avg_response_time": 85.0
    })
