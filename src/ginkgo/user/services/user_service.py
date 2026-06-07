# Upstream: CLI Commands (ginkgo users 命令)
# Downstream: BaseService (继承提供服务基础能力)、UserCRUD (用户CRUD操作)、UserContactCRUD (联系方式CRUD操作)
# Role: UserService用户管理业务服务提供用户创建、删除、联系方式管理等业务逻辑支持通知系统用户管理功能


"""
User Management Service

This service handles business logic for managing users including:
- Creating users (person, channel, organization)
- Adding contact information (email, discord)
- Deleting users with cascade
"""

from typing import List, Optional, Union, Any
import pandas as pd

from ginkgo.libs import GLOG, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud import UserCRUD, UserContactCRUD, UserCredentialCRUD
from ginkgo.data.models import MUser, MUserContact
from ginkgo.enums import USER_TYPES, SOURCE_TYPES, CONTACT_TYPES


class UserService(BaseService):
    """
    User Management Service

    Provides business logic for user management operations including
    user creation, contact management, and cascade deletion.
    """

    def __init__(self, user_crud: UserCRUD, user_contact_crud: UserContactCRUD, user_credential_crud: UserCredentialCRUD):
        """
        Initialize UserService with CRUD dependencies

        Args:
            user_crud: User CRUD repository instance
            user_contact_crud: UserContact CRUD repository instance
            user_credential_crud: UserCredential CRUD repository instance
        """
        super().__init__(crud_repo=user_crud)
        self.user_crud = user_crud
        self.user_contact_crud = user_contact_crud
        # #3956
        self.user_credential_crud = user_credential_crud

    @retry(max_try=3)
    def add_user(
        self,
        name: str,
        user_type: Union[USER_TYPES, int, str] = USER_TYPES.PERSON,
        description: Optional[str] = None,
        is_active: bool = True,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
    ) -> ServiceResult:
        """
        Add a new user (automatically creates credential with password=username)

        Args:
            name: User name (will be used as both username and display_name)
            user_type: User type (PERSON/CHANNEL/ORGANIZATION)
            description: User description
            is_active: Whether the user is active

        Returns:
            ServiceResult with created user info
        """
        try:
            # Validate user_type
            if isinstance(user_type, str):
                type_map = {
                    "PERSON": USER_TYPES.PERSON,
                    "CHANNEL": USER_TYPES.CHANNEL,
                    "ORGANIZATION": USER_TYPES.ORGANIZATION
                }
                user_type = type_map.get(user_type.upper(), USER_TYPES.PERSON)

            validated_type = USER_TYPES.validate_input(user_type)
            if validated_type is None:
                return ServiceResult.error(
                    f"Invalid user_type: {user_type}",
                    message="User type must be PERSON, CHANNEL, or ORGANIZATION"
                )

            # Create user - name is used as both username and display_name
            user = MUser(
                username=name,
                display_name=display_name or name,
                description=description,
                user_type=validated_type,
                is_active=is_active,
                source=SOURCE_TYPES.OTHER
            )

            # Insert via CRUD
            created_user = self.user_crud.add(user)

            if created_user is None:
                return ServiceResult.error(
                    "Failed to create user",
                    message="Database insert operation returned None"
                )

            # Extract UUID from created user object
            user_uuid = created_user.uuid

            # Auto-create credential with password=username
            import bcrypt
            from ginkgo.data.models import MUserCredential

            password_hash = password_hash or bcrypt.hashpw(name.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            credential = MUserCredential(
                user_id=user_uuid,
                password_hash=password_hash,
                is_active=is_active,
                is_admin=False
            )

            created_credential = self.user_credential_crud.add(credential)
            if not created_credential:
                # Rollback: delete user if credential creation fails
                self.user_crud.delete(filters={"uuid": user_uuid})
                return ServiceResult.error(
                    "Failed to create user credential",
                    message="Credential creation failed, user rolled back"
                )

            GLOG.INFO(f"Created user: {user_uuid}, username={name}, type={USER_TYPES.from_int(validated_type).name}")

            # Auto-create email contact if provided
            if email:
                email_type = CONTACT_TYPES.validate_input(CONTACT_TYPES.EMAIL)
                self.user_contact_crud.add(MUserContact(
                    user_id=user_uuid,
                    contact_type=email_type,
                    address=email,
                    is_primary=True,
                    is_active=is_active,
                    source=SOURCE_TYPES.OTHER
                ))

            return ServiceResult.success(
                data={
                    "uuid": user_uuid,
                    "username": name,
                    "display_name": display_name or name,
                    "description": description or "",
                    "user_type": USER_TYPES.from_int(validated_type).name,
                    "is_active": is_active,
                    "is_admin": False,
                    "email": email or "",
                },
                message=f"User '{name}' created successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error adding user: {e}")
            return ServiceResult.error(
                f"Failed to add user: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def add_contact(
        self,
        user_uuid: str,
        contact_type: Union[CONTACT_TYPES, int, str],
        address: str,
        is_primary: bool = False,
        is_active: bool = True
    ) -> ServiceResult:
        """
        Add contact information for a user

        Args:
            user_uuid: User UUID
            contact_type: Contact type (EMAIL/DISCORD)
            address: Contact address (email or webhook URL)
            is_primary: Whether this is the primary contact (default: False)
            is_active: Whether the contact is active

        Returns:
            ServiceResult with created contact info
        """
        try:
            # If setting as primary, first set all other contacts to is_primary=False
            if is_primary:
                # #3956
                existing_contacts = self.user_contact_crud.find_by_user_id(user_id=user_uuid)
                for contact in existing_contacts:
                    if contact.is_primary:
                        self.user_contact_crud.modify(
                            filters={"uuid": contact.uuid},
                            updates={"is_primary": False}
                        )
                        GLOG.DEBUG(f"Set contact {contact.uuid} to non-primary")

            # Validate contact_type
            if isinstance(contact_type, str):
                type_map = {
                    "EMAIL": CONTACT_TYPES.EMAIL,
                    "WEBHOOK": CONTACT_TYPES.WEBHOOK,
                    "DISCORD": CONTACT_TYPES.DISCORD
                }
                contact_type = type_map.get(contact_type.upper(), CONTACT_TYPES.EMAIL)

            validated_type = CONTACT_TYPES.validate_input(contact_type)
            if validated_type is None:
                return ServiceResult.error(
                    f"Invalid contact_type: {contact_type}",
                    message="Contact type must be EMAIL or DISCORD"
                )

            # Create contact
            contact = MUserContact(
                user_id=user_uuid,  # MUserContact uses user_id field
                contact_type=validated_type,
                address=address,
                is_primary=is_primary,
                is_active=is_active,
                source=SOURCE_TYPES.OTHER
            )

            # Insert via CRUD
            created_contact = self.user_contact_crud.add(contact)

            if created_contact is None:
                return ServiceResult.error(
                    "Failed to create contact",
                    message="Database insert operation returned None"
                )

            # Extract UUID from created contact object
            contact_uuid = created_contact.uuid

            GLOG.INFO(f"Added contact: {contact_uuid} for user: {user_uuid}, type={CONTACT_TYPES.from_int(validated_type).name}")

            return ServiceResult.success(
                data={
                    "uuid": contact_uuid,
                    "user_uuid": user_uuid,
                    "contact_type": CONTACT_TYPES.from_int(validated_type).name,
                    "address": address,
                    "is_primary": is_primary,
                    "is_active": is_active
                },
                message=f"Contact added successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error adding contact: {e}")
            return ServiceResult.error(
                f"Failed to add contact: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def delete_user(self, user_uuid: str) -> ServiceResult:
        """
        Delete a user with cascade (contacts and group mappings)

        Args:
            user_uuid: User UUID to delete

        Returns:
            ServiceResult indicating success or failure
        """
        try:
            # Use UserCRUD.delete() which handles cascade deletion
            count = self.user_crud.delete(filters={"uuid": user_uuid})

            if count == 0:
                return ServiceResult.error(
                    f"User not found: {user_uuid}",
                    message="No user deleted"
                )

            GLOG.INFO(f"Deleted user with cascade: {user_uuid}")

            return ServiceResult.success(
                data={"user_uuid": user_uuid, "deleted_count": count},
                message=f"User and related records deleted successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error deleting user: {e}")
            return ServiceResult.error(
                f"Failed to delete user: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def get_user(self, user_uuid: str) -> ServiceResult:
        """
        Get user by UUID

        Args:
            user_uuid: User UUID

        Returns:
            ServiceResult with user data
        """
        try:
            # #3956
            users = self.user_crud.find(filters={"uuid": user_uuid}, page_size=1)

            if not users:
                return ServiceResult.error(
                    f"User not found: {user_uuid}",
                    message="User does not exist"
                )

            user = users[0]

            return ServiceResult.success(
                data={
                    "uuid": user.uuid,
                    "username": user.username,
                    "display_name": user.display_name,
                    "description": user.description,
                    "user_type": USER_TYPES.from_int(user.user_type).name,
                    "is_active": user.is_active,
                    "source": SOURCE_TYPES.from_int(user.source).name,
                    "create_at": user.create_at.isoformat() if user.create_at else None,
                    "update_at": user.update_at.isoformat() if user.update_at else None
                },
                message="User retrieved successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting user: {e}")
            return ServiceResult.error(
                f"Failed to get user: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def get_user_full_info(self, user_uuid: str) -> ServiceResult:
        """
        Get complete user information including contacts and groups

        Args:
            user_uuid: User UUID

        Returns:
            ServiceResult with complete user data
        """
        try:
            # Get basic user info
            basic_result = self.get_user(user_uuid)
            if not basic_result.success:
                return basic_result

            user_data = basic_result.data

            # Get contacts
            contacts_result = self.get_user_contacts(user_uuid)
            contacts = contacts_result.data["contacts"] if contacts_result.success else []

            # Get groups through UserGroupService
            from ginkgo.data.containers import container

            group_service = container.user_group_service()
            groups_result = group_service.get_user_groups(user_uuid)
            groups = groups_result.data["groups"] if groups_result.success else []

            return ServiceResult.success(
                data={
                    **user_data,
                    "contacts": contacts,
                    "groups": groups
                },
                message="User full info retrieved successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting user full info: {e}")
            return ServiceResult.error(
                f"Failed to get user full info: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def update_user(
        self,
        user_uuid: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        is_admin: Optional[bool] = None,
    ) -> ServiceResult:
        """
        Update user information

        Args:
            user_uuid: User UUID
            name: New name (optional)
            description: New description (optional)
            is_active: New active status (optional)

        Returns:
            ServiceResult with updated user info
        """
        try:
            # Check if user exists
            # #3956
            users = self.user_crud.find(filters={"uuid": user_uuid}, page_size=1)
            if not users:
                return ServiceResult.error(
                    f"User not found: {user_uuid}",
                    message="User does not exist"
                )

            user = users[0]

            # Build updates dict
            updates = {}
            if name is not None:
                # Update both username and display_name when name is provided
                updates["username"] = name
                updates["display_name"] = name
            if display_name is not None:
                # Update only display_name without touching username
                updates["display_name"] = display_name
            if description is not None:
                updates["description"] = description
            if is_active is not None:
                updates["is_active"] = is_active

            if not updates and email is None and is_admin is None:
                return ServiceResult.error(
                    "No updates provided",
                    message="At least one field must be specified for update"
                )

            # Apply user table updates
            if updates:
                self.user_crud.modify(filters={"uuid": user_uuid}, updates=updates)

            # Update credential is_admin if requested
            if is_admin is not None:
                credential = self.user_credential_crud.get_by_user_id(user_uuid)
                if credential:
                    self.user_credential_crud.modify(
                        filters={"uuid": credential.uuid},
                        updates={"is_admin": is_admin},
                    )

            # Update/create email contact if requested
            if email is not None:
                existing_contacts = self.user_contact_crud.find_by_user_id(user_id=user_uuid)
                email_contacts = [c for c in existing_contacts
                                  if hasattr(c, 'contact_type') and
                                  CONTACT_TYPES.from_int(c.contact_type) == CONTACT_TYPES.EMAIL]
                if email_contacts:
                    self.user_contact_crud.modify(
                        filters={"uuid": email_contacts[0].uuid},
                        updates={"address": email},
                    )
                else:
                    email_type = CONTACT_TYPES.validate_input(CONTACT_TYPES.EMAIL)
                    self.user_contact_crud.add(MUserContact(
                        user_id=user_uuid,
                        contact_type=email_type,
                        address=email,
                        is_primary=True,
                        is_active=True,
                        source=SOURCE_TYPES.OTHER,
                    ))

            GLOG.INFO(f"Updated user: {user_uuid}")

            # Re-fetch user to get updated data
            # #3956
            users = self.user_crud.find(filters={"uuid": user_uuid}, page_size=1)
            if not users:
                return ServiceResult.error(
                    "Failed to fetch updated user",
                    message="User disappeared after update"
                )

            updated_user = users[0]

            # Fetch credential for is_admin
            credential = self.user_credential_crud.get_by_user_id(user_uuid)
            is_admin_val = credential.is_admin if credential and hasattr(credential, 'is_admin') else False

            return ServiceResult.success(
                data={
                    "uuid": user_uuid,
                    "username": updated_user.username,
                    "display_name": updated_user.display_name,
                    "description": updated_user.description,
                    "user_type": USER_TYPES.from_int(updated_user.user_type).name,
                    "is_active": updated_user.is_active,
                    "is_admin": is_admin_val,
                },
                message="User updated successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error updating user: {e}")
            return ServiceResult.error(
                f"Failed to update user: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def list_users(
        self,
        user_type: Optional[Union[USER_TYPES, int]] = None,
        is_active: Optional[bool] = None,
        name: Optional[str] = None,
        username: Optional[str] = None,
        is_del: Optional[bool] = None,
        limit: int = 100
    ) -> ServiceResult:
        """
        List users with optional filters

        Args:
            user_type: Filter by user type
            is_active: Filter by active status
            name: Filter by name (partial match, case-insensitive)
            limit: Maximum number of results

        Returns:
            ServiceResult with list of users
        """
        try:
            filters = {"is_del": is_del if is_del is not None else False}
            if user_type is not None:
                validated = USER_TYPES.validate_input(user_type)
                if validated is not None:
                    filters["user_type"] = validated
            if is_active is not None:
                filters["is_active"] = is_active

            # #3956
            users = self.user_crud.find(filters=filters)

            # 按 username 精确匹配（优先级高于模糊 name 搜索）
            if username:
                users = [u for u in users if u.username == username]

            # 按 name 过滤（在 Python 端实现模糊匹配，搜索 username 和 display_name）
            if name:
                name_lower = name.lower()
                users = [u for u in users if name_lower in u.username.lower() or (u.display_name and name_lower in u.display_name.lower())]

            # Batch-fetch credentials for is_admin enrichment
            credentials_map = self.get_all_credentials()

            user_list = []
            for user in users:
                cred = credentials_map.get(user.uuid)
                is_admin_val = cred.is_admin if cred and hasattr(cred, 'is_admin') else False
                user_list.append({
                    "uuid": user.uuid,
                    "username": user.username,
                    "display_name": user.display_name,
                    "description": user.description,
                    "user_type": USER_TYPES.from_int(user.user_type).name,
                    "is_active": user.is_active,
                    "is_admin": is_admin_val,
                    "create_at": user.create_at.isoformat() if user.create_at else None,
                    "created_at": user.create_at.isoformat() if user.create_at else None,
                })

            return ServiceResult.success(
                data={"users": user_list, "count": len(user_list)},
                message=f"Retrieved {len(user_list)} users"
            )

        except Exception as e:
            GLOG.ERROR(f"Error listing users: {e}")
            return ServiceResult.error(
                f"Failed to list users: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def update_contact(
        self,
        contact_uuid: str,
        contact_type: Optional[Union[CONTACT_TYPES, int, str]] = None,
        address: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_primary: Optional[bool] = None,
    ) -> ServiceResult:
        """
        Update contact information (type, address, active and primary status).

        Args:
            contact_uuid: Contact UUID
            contact_type: New contact type (optional)
            address: New address (optional)
            is_active: New active status (optional)
            is_primary: Set as primary contact (optional; True delegates to set_primary logic)

        Returns:
            ServiceResult with updated contact info
        """
        try:
            # Check if contact exists
            # #3956
            contacts = self.user_contact_crud.find(filters={"uuid": contact_uuid}, page_size=1)
            if not contacts:
                return ServiceResult.error(
                    f"Contact not found: {contact_uuid}",
                    message="Contact does not exist"
                )

            contact = contacts[0]

            # Build updates dict
            updates = {}
            if contact_type is not None:
                # Validate and convert contact_type
                if isinstance(contact_type, str):
                    type_map = {
                        "EMAIL": CONTACT_TYPES.EMAIL,
                        "WEBHOOK": CONTACT_TYPES.WEBHOOK
                    }
                    contact_type = type_map.get(contact_type.upper(), CONTACT_TYPES.EMAIL)

                validated_type = CONTACT_TYPES.validate_input(contact_type)
                if validated_type is None:
                    return ServiceResult.error(
                        f"Invalid contact_type: {contact_type}",
                        message="Contact type must be EMAIL or WEBHOOK"
                    )
                updates["contact_type"] = validated_type

            if address is not None:
                updates["address"] = address
            if is_active is not None:
                updates["is_active"] = is_active

            if not updates and is_primary is None:
                return ServiceResult.error(
                    "No updates provided",
                    message="At least one field must be specified for update"
                )

            # Handle is_primary=True via set_primary logic (clears others first)
            if is_primary is True:
                self.set_primary(contact_uuid)
            elif is_primary is False:
                updates["is_primary"] = False

            # Use modify to update
            if updates:
                self.user_contact_crud.modify(filters={"uuid": contact_uuid}, updates=updates)

            GLOG.INFO(f"Updated contact: {contact_uuid}")

            # Re-fetch to get updated data
            # #3956
            contacts = self.user_contact_crud.find(filters={"uuid": contact_uuid}, page_size=1)
            if not contacts:
                return ServiceResult.error(
                    "Failed to fetch updated contact",
                    message="Contact disappeared after update"
                )

            updated_contact = contacts[0]

            return ServiceResult.success(
                data={
                    "uuid": contact_uuid,
                    "contact_type": CONTACT_TYPES.from_int(updated_contact.contact_type).name,
                    "address": updated_contact.address,
                    "is_primary": updated_contact.is_primary,
                    "is_active": updated_contact.is_active
                },
                message="Contact updated successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error updating contact: {e}")
            return ServiceResult.error(
                f"Failed to update contact: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def set_primary(self, contact_uuid: str) -> ServiceResult:
        """
        Set a contact as the primary contact for its user.
        This will set is_primary=False for all other contacts of the same user.

        Args:
            contact_uuid: Contact UUID to set as primary

        Returns:
            ServiceResult with updated contact info
        """
        try:
            # Get the contact to find its user
            # #3956
            contacts = self.user_contact_crud.find(filters={"uuid": contact_uuid}, page_size=1)
            if not contacts:
                return ServiceResult.error(
                    f"Contact not found: {contact_uuid}",
                    message="Contact does not exist"
                )

            contact = contacts[0]
            user_id = contact.user_id

            # Set all other contacts to is_primary=False
            # #3956
            existing_contacts = self.user_contact_crud.find_by_user_id(user_id=contact.user_id)
            for other_contact in existing_contacts:
                if other_contact.uuid != contact_uuid and other_contact.is_primary:
                    self.user_contact_crud.modify(
                        filters={"uuid": other_contact.uuid},
                        updates={"is_primary": False}
                    )
                    GLOG.DEBUG(f"Set contact {other_contact.uuid} to non-primary")

            # Set this contact as primary
            self.user_contact_crud.modify(
                filters={"uuid": contact_uuid},
                updates={"is_primary": True}
            )

            GLOG.INFO(f"Set contact {contact_uuid} as primary for user {user_id}")

            return ServiceResult.success(
                data={
                    "uuid": contact_uuid,
                    "user_uuid": user_id,
                    "is_primary": True
                },
                message="Contact set as primary successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error setting primary contact: {e}")
            return ServiceResult.error(
                f"Failed to set primary contact: {str(e)}",
                message=f"Error: {str(e)}"
            )

    @retry(max_try=3)
    def delete_contact(self, contact_uuid: str) -> ServiceResult:
        """
        Delete a contact

        Args:
            contact_uuid: Contact UUID to delete

        Returns:
            ServiceResult indicating success or failure
        """
        try:
            # Use remove instead of delete
            self.user_contact_crud.remove(filters={"uuid": contact_uuid})

            GLOG.INFO(f"Deleted contact: {contact_uuid}")

            return ServiceResult.success(
                data={"contact_uuid": contact_uuid},
                message="Contact deleted successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"Error deleting contact: {e}")
            return ServiceResult.error(
                f"Failed to delete contact: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def get_user_contacts(self, user_uuid: str) -> ServiceResult:
        """
        Get all contacts for a user

        Args:
            user_uuid: User UUID

        Returns:
            ServiceResult with list of contacts
        """
        try:
            contacts = self.user_contact_crud.find_by_user_id(
                user_id=user_uuid,
            )

            contact_list = []
            for contact in contacts:
                contact_list.append({
                    "uuid": contact.uuid,
                    "contact_type": CONTACT_TYPES.from_int(contact.contact_type).name,
                    "address": contact.address,
                    "is_primary": contact.is_primary,
                    "is_active": contact.is_active
                })

            return ServiceResult.success(
                data={"contacts": contact_list, "count": len(contact_list)},
                message=f"Retrieved {len(contact_list)} contacts"
            )

        except Exception as e:
            GLOG.ERROR(f"Error getting user contacts: {e}")
            return ServiceResult.error(
                f"Failed to get contacts: {str(e)}",
                message=f"Error: {str(e)}"
            )

    def get_active_contacts(self, user_uuid: str, is_active: bool = True) -> ServiceResult:
        """
        获取用户的活跃联系方式

        Args:
            user_uuid: 用户 UUID
            is_active: 是否只查询活跃联系方式

        Returns:
            ServiceResult: data 为 List[MUserContact]
        """
        try:
            contacts = self.user_contact_crud.get_by_user(user_uuid, is_active=is_active)
            return ServiceResult.success(contacts)
        except Exception as e:
            GLOG.ERROR(f"Failed to get active contacts: {e}")
            return ServiceResult.error(str(e))

    def fuzzy_search(self, query: str, limit: int = 100) -> ServiceResult:
        """
        Fuzzy search users by UUID or name

        Searches in both uuid and name fields with partial matching.
        Full UUID (32 hex chars) will match exactly, otherwise uses LIKE query.

        Args:
            query: Search keyword (UUID or user name)
            limit: Maximum results to return

        Returns:
            ServiceResult with list of matching users

        Examples:
            result = service.fuzzy_search("Alice")
            result = service.fuzzy_search("a2eaba95")
        """
        try:
            users = self.user_crud.fuzzy_search(query)

            # Apply limit
            if limit and len(users) > limit:
                users = users.head(limit)

            user_list = []
            for user in users:
                user_list.append({
                    "uuid": user.uuid,
                    "username": user.username,
                    "display_name": user.display_name,
                    "description": user.description,
                    "user_type": USER_TYPES.from_int(user.user_type).name,
                    "is_active": user.is_active,
                    "create_at": user.create_at.isoformat() if user.create_at else None
                })

            return ServiceResult.success(
                data={"users": user_list, "count": len(user_list)},
                message=f"Found {len(user_list)} users matching '{query}'"
            )

        except Exception as e:
            GLOG.ERROR(f"Error fuzzy searching users: {e}")
            return ServiceResult.error(
                f"Failed to search users: {str(e)}",
                message=f"Error: {str(e)}"
            )

    # ==================== 凭据方法 (#4604 迁移自 data/services) ====================

    def get_credential(self, user_id: str):
        """根据用户 ID 获取凭据对象，未找到返回 None"""
        return self.user_credential_crud.get_by_user_id(user_id)

    def get_all_credentials(self) -> dict:
        """批量获取所有凭证，返回 {user_id: credential} 字典"""
        try:
            credentials = self.user_credential_crud.find()
            return {c.user_id: c for c in credentials if hasattr(c, 'user_id')}
        except Exception as e:
            GLOG.ERROR(f"Failed to get all credentials: {e}")
            return {}

    def update_last_login(self, credential_uuid: str, ip: str = "") -> bool:
        """更新最后登录时间和 IP"""
        from datetime import datetime
        try:
            self.user_credential_crud.modify(
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
            self.user_credential_crud.modify(
                {"uuid": credential_uuid},
                {"password_hash": new_password_hash},
            )
            return True
        except Exception as e:
            GLOG.ERROR(f"Failed to update password: {e}")
            return False

    def reset_password(self, user_uuid: str, new_password_hash: str) -> ServiceResult:
        """通过用户 UUID 重置密码"""
        try:
            credential = self.user_credential_crud.get_by_user_id(user_uuid)
            if not credential:
                return ServiceResult.error("Credential not found")
            self.user_credential_crud.modify(
                {"uuid": credential.uuid},
                {"password_hash": new_password_hash},
            )
            return ServiceResult.success({"reset": True})
        except Exception as e:
            GLOG.ERROR(f"Failed to reset password: {e}")
            return ServiceResult.error(str(e))

    def get_contact(self, contact_uuid: str) -> ServiceResult:
        """获取单个联系方式"""
        try:
            contacts = self.user_contact_crud.find(filters={"uuid": contact_uuid})
            if not contacts:
                return ServiceResult.error("Contact not found")
            return ServiceResult.success(contacts[0])
        except Exception as e:
            GLOG.ERROR(f"Failed to get contact: {e}")
            return ServiceResult.error(str(e))

