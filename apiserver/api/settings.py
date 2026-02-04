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
from core.logging import logger

router = APIRouter()


# ==================== 通用函数 ====================

def get_user_crud():
    """获取UserCRUD实例"""
    return container.user_crud()


def get_user_credential_crud():
    """获取UserCredentialCRUD实例"""
    return container.user_credential_crud()


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


@router.get("/users", response_model=List[UserSummary])
async def list_users(
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """获取用户列表"""
    try:
        user_crud = get_user_crud()
        credential_crud = get_user_credential_crud()

        # 构建查询条件
        filters = {"is_del": False}
        if status == "active":
            filters["is_active"] = True
        elif status == "disabled":
            filters["is_active"] = False

        # 查询用户
        users = user_crud.find(filters=filters, as_dataframe=False)

        # 搜索过滤
        if search:
            search_lower = search.lower()
            users = [u for u in users if search_lower in u.username.lower() or (u.display_name and search_lower in u.display_name.lower())]

        result = []
        for user in users:
            # 获取关联的凭证
            credentials = credential_crud.get_by_user_id(user.uuid, as_dataframe=False)
            credential = credentials[0] if credentials else None

            # 确定角色
            roles = ["admin"] if credential and credential.is_admin else []

            # 确定状态
            user_status = "active" if user.is_active and (credential and credential.is_active) else "disabled"

            result.append({
                "uuid": user.uuid,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "email": user.email or "",
                "roles": roles,
                "status": user_status,
                "created_at": user.create_at.isoformat() if user.create_at else datetime.utcnow().isoformat() + "Z"
            })

        return result

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.post("/users", response_model=UserSummary, status_code=201)
async def create_user(data: UserCreate):
    """创建用户"""
    try:
        user_crud = get_user_crud()
        credential_crud = get_user_credential_crud()

        # 检查用户名是否已存在
        existing_users = user_crud.find(filters={"username": data.username, "is_del": False}, as_dataframe=False)
        if existing_users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )

        # 创建MUser
        user = MUser(
            username=data.username,
            display_name=data.display_name,
            email=data.email,
            description=f"User created via API: {data.username}",
            user_type=1,  # PERSON
            is_active=data.status == "active"
        )
        created_user = user_crud.add(user)

        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # 创建MUserCredential
        password_hash = hash_password(data.password)
        is_admin = "admin" in data.roles
        credential = MUserCredential(
            user_id=created_user.uuid,
            password_hash=password_hash,
            is_active=data.status == "active",
            is_admin=is_admin
        )
        created_credential = credential_crud.add(credential)

        if not created_credential:
            # 删除已创建的user
            user_crud.delete(filters={"uuid": created_user.uuid})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user credential"
            )

        logger.info(f"User created: {data.username} (uuid={created_user.uuid})")

        return {
            "uuid": created_user.uuid,
            "username": created_user.username,
            "display_name": created_user.display_name or created_user.username,
            "email": data.email,
            "roles": data.roles,
            "status": data.status,
            "created_at": created_user.create_at.isoformat() if created_user.create_at else datetime.utcnow().isoformat() + "Z"
        }

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
        user_crud = get_user_crud()
        credential_crud = get_user_credential_crud()

        # 查询用户
        users = user_crud.find(filters={"uuid": uuid, "is_del": False}, as_dataframe=False)
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user = users[0]

        # 更新用户信息
        updates = {}
        if data.display_name is not None:
            updates["display_name"] = data.display_name

        if data.email is not None:
            updates["email"] = data.email

        if data.status is not None:
            updates["is_active"] = (data.status == "active")

        if updates:
            user_crud.modify(filters={"uuid": uuid}, updates=updates)

        # 更新凭证信息
        credentials = credential_crud.get_by_user_id(uuid, as_dataframe=False)
        if credentials:
            credential = credentials[0]
            credential_updates = {}

            if data.status is not None:
                credential_updates["is_active"] = (data.status == "active")

            if data.roles is not None:
                credential_updates["is_admin"] = "admin" in data.roles

            if credential_updates:
                credential_crud.modify(filters={"uuid": credential.uuid}, updates=credential_updates)

        logger.info(f"User updated: {uuid}")

        return {"message": f"User {uuid} updated"}

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
        credential_crud = get_user_credential_crud()

        new_password = data.get("new_password", "123456")

        # 获取用户凭证
        credentials = credential_crud.get_by_user_id(uuid, as_dataframe=False)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User credential not found"
            )

        credential = credentials[0]

        # 更新密码
        new_password_hash = hash_password(new_password)
        success = credential_crud.update_password(credential.uuid, new_password_hash)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )

        logger.info(f"Password reset for user: {uuid}")

        return {"message": f"Password for user {uuid} has been reset", "new_password": new_password}

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
        user_crud = get_user_crud()

        # 软删除用户（会级联删除credential）
        success = user_crud.delete(filters={"uuid": uuid})

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User deleted: {uuid}")

        return {"message": f"User {uuid} deleted"}

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


@router.get("/users/{user_uuid}/contacts", response_model=List[UserContactSummary])
async def list_user_contacts(user_uuid: str):
    """获取用户联系方式列表"""
    try:
        user_crud = get_user_crud()
        contact_crud = container.user_contact_crud()

        # 验证用户存在
        users = user_crud.find(filters={"uuid": user_uuid, "is_del": False}, as_dataframe=False)
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 获取联系方式
        contacts = contact_crud.find_by_user_id(user_uuid, as_dataframe=False)

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

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list contacts"
        )


@router.post("/users/{user_uuid}/contacts", response_model=UserContactSummary, status_code=201)
async def create_user_contact(user_uuid: str, data: UserContactCreate):
    """创建用户联系方式"""
    try:
        from ginkgo.data.models.model_user_contact import MUserContact

        user_crud = get_user_crud()
        contact_crud = container.user_contact_crud()

        # 验证用户存在
        users = user_crud.find(filters={"uuid": user_uuid, "is_del": False}, as_dataframe=False)
        if not users:
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

        # 如果设置为主联系方式，先取消其他的主联系方式
        if data.is_primary:
            existing_contacts = contact_crud.find_by_user_id(user_uuid, as_dataframe=False)
            for contact in existing_contacts:
                if contact.is_primary:
                    contact_crud.modify(filters={"uuid": contact.uuid}, updates={"is_primary": False})

        # 创建联系方式
        contact = MUserContact(
            user_id=user_uuid,
            contact_type=contact_type_enum,
            address=data.address,
            is_primary=data.is_primary,
            is_active=True
        )

        created_contact = contact_crud.add(contact)
        if not created_contact:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create contact"
            )

        logger.info(f"Contact created for user: {user_uuid}")

        return {
            "uuid": created_contact.uuid,
            "user_id": created_contact.user_id,
            "contact_type": data.contact_type,
            "address": data.address,
            "is_primary": data.is_primary,
            "is_active": True,
            "created_at": created_contact.create_at.isoformat() if created_contact.create_at else datetime.utcnow().isoformat() + "Z"
        }

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
        contact_crud = container.user_contact_crud()

        # 获取联系方式
        contacts = contact_crud.find(filters={"uuid": contact_uuid}, as_dataframe=False)
        if not contacts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        contact = contacts[0]

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
            # 如果设置为主联系方式，先取消该用户其他的主联系方式
            if data.is_primary:
                existing_contacts = contact_crud.find_by_user_id(contact.user_id, as_dataframe=False)
                for c in existing_contacts:
                    if c.uuid != contact_uuid and c.is_primary:
                        contact_crud.modify(filters={"uuid": c.uuid}, updates={"is_primary": False})
            updates["is_primary"] = data.is_primary

        if data.is_active is not None:
            updates["is_active"] = data.is_active

        if updates:
            contact_crud.modify(filters={"uuid": contact_uuid}, updates=updates)

        logger.info(f"Contact updated: {contact_uuid}")

        return {"message": f"Contact {contact_uuid} updated"}

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
        contact_crud = container.user_contact_crud()

        success = contact_crud.delete(filters={"uuid": contact_uuid})
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        logger.info(f"Contact deleted: {contact_uuid}")

        return {"message": f"Contact {contact_uuid} deleted"}

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
        contact_crud = container.user_contact_crud()

        # 获取联系方式
        contacts = contact_crud.find(filters={"uuid": contact_uuid}, as_dataframe=False)
        if not contacts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        contact = contacts[0]
        contact_type = contact.get_contact_type_enum()

        # 根据联系方式类型发送测试通知
        if contact_type == CONTACT_TYPES.EMAIL:
            # TODO: 实现邮件发送
            logger.info(f"Email test sent to: {data.address}")
            return {
                "message": f"Test email sent to {data.address}",
                "detail": "Email sending not implemented yet"
            }
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
                return {
                    "message": f"Test webhook sent to {data.address}",
                    "detail": f"Status code: {response.status_code}"
                }
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
        contact_crud = container.user_contact_crud()

        # 获取联系方式
        contacts = contact_crud.find(filters={"uuid": contact_uuid}, as_dataframe=False)
        if not contacts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        contact = contacts[0]

        # 取消该用户的其他主联系方式
        existing_contacts = contact_crud.find_by_user_id(contact.user_id, as_dataframe=False)
        for c in existing_contacts:
            if c.uuid != contact_uuid and c.is_primary:
                contact_crud.modify(filters={"uuid": c.uuid}, updates={"is_primary": False})

        # 设置为主联系方式
        contact_crud.modify(filters={"uuid": contact_uuid}, updates={"is_primary": True})

        logger.info(f"Primary contact set: {contact_uuid}")

        return {"message": f"Contact {contact_uuid} set as primary"}

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


def get_user_group_crud():
    """获取UserGroupCRUD实例"""
    return container.user_group_crud()


def get_user_group_mapping_crud():
    """获取UserGroupMappingCRUD实例"""
    return container.user_group_mapping_crud()


def count_users_in_group(group_uuid: str) -> int:
    """统计组中的用户数量"""
    mapping_crud = get_user_group_mapping_crud()
    mappings = mapping_crud.find_by_group(group_uuid, as_dataframe=False)
    return len(mappings)


@router.get("/user-groups", response_model=List[UserGroupSummary])
async def list_user_groups():
    """获取用户组列表"""
    try:
        group_crud = get_user_group_crud()

        # 查询所有用户组
        groups = group_crud.find(filters={"is_del": False}, as_dataframe=False)

        result = []
        for group in groups:
            # 统计用户数量
            user_count = count_users_in_group(group.uuid)

            # 权限暂不实现，返回空数组
            permissions = []

            result.append({
                "uuid": group.uuid,
                "name": group.name,
                "description": group.description or "",
                "user_count": user_count,
                "permissions": permissions
            })

        return result

    except Exception as e:
        logger.error(f"Error listing user groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list user groups"
        )


@router.post("/user-groups", response_model=UserGroupSummary, status_code=201)
async def create_user_group(data: UserGroupCreate):
    """创建用户组"""
    try:
        group_crud = get_user_group_crud()

        # 检查组名是否已存在
        existing_groups = group_crud.find(filters={"name": data.name, "is_del": False}, as_dataframe=False)
        if existing_groups:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Group name already exists"
            )

        # 创建用户组
        from ginkgo.data.models.model_user_group import MUserGroup
        group = MUserGroup(
            name=data.name,
            description=data.description or "",
            is_active=True
        )
        created_group = group_crud.add(group)

        if not created_group:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user group"
            )

        logger.info(f"User group created: {data.name} (uuid={created_group.uuid})")

        return {
            "uuid": created_group.uuid,
            "name": created_group.name,
            "description": created_group.description or "",
            "user_count": 0,
            "permissions": data.permissions
        }

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
        group_crud = get_user_group_crud()

        # 查询用户组
        groups = group_crud.find(filters={"uuid": uuid, "is_del": False}, as_dataframe=False)
        if not groups:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found"
            )

        # 更新用户组信息（权限暂不实现）
        updates = {}
        if data.name is not None:
            # 检查新名称是否与其他组冲突
            existing_groups = group_crud.find(filters={"name": data.name, "is_del": False}, as_dataframe=False)
            if existing_groups and existing_groups[0].uuid != uuid:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Group name already exists"
                )
            updates["name"] = data.name

        if data.description is not None:
            updates["description"] = data.description

        if updates:
            group_crud.modify(filters={"uuid": uuid}, updates=updates)

        logger.info(f"User group updated: {uuid}")

        return {"message": f"User group {uuid} updated"}

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
        group_crud = get_user_group_crud()
        mapping_crud = get_user_group_mapping_crud()

        # 检查用户组是否存在
        groups = group_crud.find(filters={"uuid": uuid, "is_del": False}, as_dataframe=False)
        if not groups:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found"
            )

        # 删除用户组（软删除）
        success = group_crud.delete(filters={"uuid": uuid})

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user group"
            )

        # 删除相关的映射记录
        mapping_crud.remove(filters={"group_uuid": uuid})

        logger.info(f"User group deleted: {uuid}")

        return {"message": f"User group {uuid} deleted"}

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


@router.get("/user-groups/{group_uuid}/members", response_model=List[GroupMemberSummary])
async def list_group_members(group_uuid: str):
    """获取用户组成员列表"""
    try:
        group_crud = get_user_group_crud()
        mapping_crud = get_user_group_mapping_crud()
        user_crud = get_user_crud()

        # 检查用户组是否存在
        groups = group_crud.find(filters={"uuid": group_uuid, "is_del": False}, as_dataframe=False)
        if not groups:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found"
            )

        # 获取组成员映射
        mappings = mapping_crud.find_by_group(group_uuid, as_dataframe=False)

        result = []
        for mapping in mappings:
            # 获取用户信息
            users = user_crud.find(filters={"uuid": mapping.user_uuid, "is_del": False}, as_dataframe=False)
            if users:
                user = users[0]
                result.append({
                    "uuid": mapping.uuid,
                    "user_uuid": user.uuid,
                    "username": user.username,
                    "display_name": user.display_name or user.username,
                    "email": user.email or ""
                })

        return result

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
        group_crud = get_user_group_crud()
        mapping_crud = get_user_group_mapping_crud()
        user_crud = get_user_crud()

        # 检查用户组是否存在
        groups = group_crud.find(filters={"uuid": group_uuid, "is_del": False}, as_dataframe=False)
        if not groups:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found"
            )

        user_uuid = data.get("user_uuid")
        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_uuid is required"
            )

        # 检查用户是否存在
        users = user_crud.find(filters={"uuid": user_uuid, "is_del": False}, as_dataframe=False)
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 检查用户是否已在组中
        if mapping_crud.check_mapping_exists(user_uuid, group_uuid):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already in this group"
            )

        # 创建映射
        from ginkgo.data.models.model_user_group_mapping import MUserGroupMapping
        mapping = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )
        created_mapping = mapping_crud.add(mapping)

        if not created_mapping:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add user to group"
            )

        logger.info(f"User {user_uuid} added to group {group_uuid}")

        return {"message": f"User added to group", "mapping_uuid": created_mapping.uuid}

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
        group_crud = get_user_group_crud()
        mapping_crud = get_user_group_mapping_crud()

        # 检查用户组是否存在
        groups = group_crud.find(filters={"uuid": group_uuid, "is_del": False}, as_dataframe=False)
        if not groups:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User group not found"
            )

        # 移除用户
        removed_count = mapping_crud.remove_user_from_group(user_uuid, group_uuid)

        if removed_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not in this group"
            )

        logger.info(f"User {user_uuid} removed from group {group_uuid}")

        return {"message": f"User removed from group"}

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


def get_notification_template_crud():
    """获取NotificationTemplateCRUD实例"""
    return container.notification_template_crud()


def get_notification_record_crud():
    """获取NotificationRecordCRUD实例"""
    return container.notification_record_crud()


def get_notification_recipient_service():
    """获取NotificationRecipientService实例"""
    return container.notification_recipient_service()


@router.get("/notifications/templates", response_model=List[NotificationTemplateSummary])
async def list_notification_templates():
    """获取通知模板列表"""
    try:
        template_crud = get_notification_template_crud()

        # 查询所有模板（使用统一接口）
        templates = template_crud.find(filters={"is_del": False}, as_dataframe=False)

        result = []
        for tpl in templates:
            # 获取模板类型
            template_type = tpl.get_template_type_enum()
            type_str = template_type.name.lower() if template_type else "text"

            result.append({
                "uuid": tpl.uuid,
                "name": tpl.template_name,
                "type": type_str,
                "subject": tpl.subject or "",
                "enabled": tpl.is_active,
                "updated_at": tpl.update_at.isoformat() if tpl.update_at else datetime.utcnow().isoformat() + "Z"
            })

        return result

    except Exception as e:
        logger.error(f"Error listing notification templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list notification templates"
        )


@router.post("/notifications/templates", response_model=NotificationTemplateSummary, status_code=201)
async def create_notification_template(data: NotificationTemplateCreate):
    """创建通知模板"""
    try:
        from ginkgo.data.models.model_notification_template import MNotificationTemplate
        from ginkgo.enums import TEMPLATE_TYPES

        template_crud = get_notification_template_crud()

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

        created_template = template_crud.add(template)

        if not created_template:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notification template"
            )

        logger.info(f"Notification template created: {data.name}")

        return {
            "uuid": created_template.uuid,
            "name": created_template.template_name,
            "type": data.type,
            "subject": created_template.subject or "",
            "enabled": created_template.is_active,
            "updated_at": created_template.update_at.isoformat() if created_template.update_at else datetime.utcnow().isoformat() + "Z"
        }

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
        template_crud = get_notification_template_crud()
        from ginkgo.enums import TEMPLATE_TYPES

        # 检查模板是否存在
        if not template_crud.exists(uuid):
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
            template_crud.update(uuid, update_dict)

        logger.info(f"Notification template updated: {uuid}")

        return {"message": f"Notification template {uuid} updated"}

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
        template_crud = get_notification_template_crud()

        success = template_crud.delete(uuid)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification template not found"
            )

        logger.info(f"Notification template deleted: {uuid}")

        return {"message": f"Notification template {uuid} deleted"}

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
        template_crud = get_notification_template_crud()

        if not template_crud.exists(uuid):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification template not found"
            )

        # TODO: 实现真实的测试发送
        logger.info(f"Test notification template: {uuid}")

        return {"message": "Test notification sent"}

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
        template_crud = get_notification_template_crud()

        if not template_crud.exists(uuid):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification template not found"
            )

        template_crud.update(uuid, {"is_active": enabled})

        logger.info(f"Notification template {uuid} toggled to {enabled}")

        return {"message": f"Notification template {'enabled' if enabled else 'disabled'}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling notification template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle notification template"
        )


@router.get("/notifications/history", response_model=List[NotificationHistoryItem])
async def list_notification_history(
    type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取通知历史"""
    try:
        record_crud = get_notification_record_crud()

        # 计算跳过的数量
        offset = (page - 1) * page_size

        # 构建查询条件
        filters = {"is_del": False}
        # TODO: 添加类型筛选支持

        # 查询记录（使用统一接口）
        records = record_crud.find(
            filters=filters,
            limit=page_size,
            offset=offset,
            sort=[("create_at", -1)]
        )

        result = []
        for record in records:
            # 获取状态
            from ginkgo.enums import NOTIFICATION_STATUS_TYPES
            status_enum = NOTIFICATION_STATUS_TYPES.from_int(record.status)
            status_str = "success" if status_enum == NOTIFICATION_STATUS_TYPES.SENT else "failed"

            # 从 channels 中获取类型
            channel = record.channels[0] if record.channels else "system"

            result.append({
                "uuid": record.uuid,
                "type": channel,
                "subject": record.message_id,
                "recipient": ", ".join(record.channels),
                "status": status_str,
                "created_at": record.create_at.isoformat() if record.create_at else datetime.utcnow().isoformat() + "Z",
                "error": getattr(record, 'error_message', None)
            })

        return result

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


@router.get("/notifications/recipients", response_model=List[NotificationRecipientSummary])
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

        return result.data["recipients"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing notification recipients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list notification recipients"
        )


@router.post("/notifications/recipients", response_model=NotificationRecipientSummary, status_code=201)
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
        return {
            "uuid": recipient_data["uuid"],
            "name": recipient_data["name"],
            "recipient_type": recipient_data["recipient_type"].lower(),
            "user_id": recipient_data["user_id"],
            "user_group_id": recipient_data["user_group_id"],
            "description": recipient_data["description"],
            "is_default": recipient_data["is_default"],
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

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

        return {"message": "Notification recipient updated successfully"}

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

        return {"message": "Notification recipient deleted successfully"}

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

        return {"message": "Notification recipient toggled successfully", "is_default": result.data["is_default"]}

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

            except requests.exceptions.Timeout:
                failed_count += 1
                results.append(f"{contact_type}: 超时")
                logger.warning(f"Test notification timeout for {address}")
            except requests.exceptions.RequestException as e:
                failed_count += 1
                results.append(f"{contact_type}: 请求失败 - {str(e)}")
                logger.error(f"Test notification request failed: {e}")
            except Exception as e:
                failed_count += 1
                results.append(f"{contact_type}: 异常 - {str(e)}")
                logger.error(f"Test notification error: {e}")

        logger.info(f"Test notification completed for recipient {uuid}: {success_count} success, {failed_count} failed")

        return {
            "message": f"测试通知已发送: {success_count} 成功, {failed_count} 失败",
            "details": results,
            "recipient_name": recipient_name,
            "contact_count": contact_count,
            "success_count": success_count,
            "failed_count": failed_count
        }

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


@router.get("/api-keys", response_model=List[APIKeySummary])
async def list_api_keys():
    """获取API密钥列表"""
    # TODO: 从数据库获取API密钥
    return [
        {
            "key_id": "key-1",
            "name": "生产环境密钥",
            "masked_key": "ginkgo_sk_****",
            "status": "active",
            "expires_at": "2025-01-31T00:00:00Z",
            "last_used": "2024-01-30T15:30:00Z"
        }
    ]


@router.post("/api-keys", response_model=APIKeySummary, status_code=201)
async def create_api_key(data: dict):
    """创建API密钥"""
    # TODO: 创建API密钥
    return {
        "key_id": "new-key",
        "name": data.get("name"),
        "masked_key": "ginkgo_sk_****",
        "status": "active",
        "expires_at": None,
        "last_used": None
    }


@router.get("/api-stats", response_model=APIStats)
async def get_api_stats():
    """获取API统计"""
    # TODO: 获取实际统计数据
    return APIStats(
        today_calls=15234,
        month_calls=456789,
        success_rate=99.8,
        avg_response_time=85.0
    )
