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
from ginkgo.data.crud import UserCRUD, UserContactCRUD
from ginkgo.data.models import MUser, MUserContact
from ginkgo.enums import USER_TYPES, SOURCE_TYPES, CONTACT_TYPES


class UserService(BaseService):
    """
    User Management Service

    Provides business logic for user management operations including
    user creation, contact management, and cascade deletion.
    """

    def __init__(self, user_crud: UserCRUD, user_contact_crud: UserContactCRUD):
        """
        Initialize UserService with CRUD dependencies

        Args:
            user_crud: User CRUD repository instance
            user_contact_crud: UserContact CRUD repository instance
        """
        super().__init__(crud_repo=user_crud)
        self.user_crud = user_crud
        self.user_contact_crud = user_contact_crud

    @retry(max_try=3)
    def add_user(
        self,
        name: str,
        user_type: Union[USER_TYPES, int, str] = USER_TYPES.PERSON,
        description: Optional[str] = None,
        is_active: bool = True
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
                display_name=name,
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
            from ginkgo.data.models.model_user_credential import MUserCredential

            password_hash = bcrypt.hashpw(name.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
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

            return ServiceResult.success(
                data={
                    "uuid": user_uuid,
                    "username": name,
                    "display_name": name,
                    "description": description or "",
                    "user_type": USER_TYPES.from_int(validated_type).name,
                    "is_active": is_active
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
                existing_contacts = self.user_contact_crud.find_by_user_id(user_id=user_uuid, as_dataframe=False)
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
            users = self.user_crud.find(filters={"uuid": user_uuid}, page_size=1, as_dataframe=False)

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
        is_active: Optional[bool] = None
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
            users = self.user_crud.find(filters={"uuid": user_uuid}, page_size=1, as_dataframe=False)
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
            if description is not None:
                updates["description"] = description
            if is_active is not None:
                updates["is_active"] = is_active

            if not updates:
                return ServiceResult.error(
                    "No updates provided",
                    message="At least one field must be specified for update"
                )

            # Use modify to update
            self.user_crud.modify(filters={"uuid": user_uuid}, updates=updates)

            GLOG.INFO(f"Updated user: {user_uuid}")

            # Re-fetch user to get updated data
            users = self.user_crud.find(filters={"uuid": user_uuid}, page_size=1, as_dataframe=False)
            if not users:
                return ServiceResult.error(
                    "Failed to fetch updated user",
                    message="User disappeared after update"
                )

            updated_user = users[0]

            return ServiceResult.success(
                data={
                    "uuid": user_uuid,
                    "username": updated_user.username,
                    "display_name": updated_user.display_name,
                    "description": updated_user.description,
                    "user_type": USER_TYPES.from_int(updated_user.user_type).name,
                    "is_active": updated_user.is_active
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
            filters = {"is_del": False}  # 默认过滤已删除的用户
            if user_type is not None:
                validated = USER_TYPES.validate_input(user_type)
                if validated is not None:
                    filters["user_type"] = validated
            if is_active is not None:
                filters["is_active"] = is_active

            users = self.user_crud.find(filters=filters, page_size=limit, as_dataframe=False)

            # 按 name 过滤（在 Python 端实现模糊匹配，搜索 username 和 display_name）
            if name:
                name_lower = name.lower()
                users = [u for u in users if name_lower in u.username.lower() or (u.display_name and name_lower in u.display_name.lower())]

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
        is_active: Optional[bool] = None
    ) -> ServiceResult:
        """
        Update contact information (type, address and active status).
        Use set_primary() to change primary status.

        Args:
            contact_uuid: Contact UUID
            contact_type: New contact type (optional)
            address: New address (optional)
            is_active: New active status (optional)

        Returns:
            ServiceResult with updated contact info
        """
        try:
            # Check if contact exists
            contacts = self.user_contact_crud.find(filters={"uuid": contact_uuid}, page_size=1, as_dataframe=False)
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

            if not updates:
                return ServiceResult.error(
                    "No updates provided",
                    message="At least one field must be specified for update"
                )

            # Use modify to update
            self.user_contact_crud.modify(filters={"uuid": contact_uuid}, updates=updates)

            GLOG.INFO(f"Updated contact: {contact_uuid}")

            # Re-fetch to get updated data
            contacts = self.user_contact_crud.find(filters={"uuid": contact_uuid}, page_size=1, as_dataframe=False)
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
            contacts = self.user_contact_crud.find(filters={"uuid": contact_uuid}, page_size=1, as_dataframe=False)
            if not contacts:
                return ServiceResult.error(
                    f"Contact not found: {contact_uuid}",
                    message="Contact does not exist"
                )

            contact = contacts[0]
            user_id = contact.user_id

            # Set all other contacts to is_primary=False
            existing_contacts = self.user_contact_crud.find_by_user_id(user_id=user_id, as_dataframe=False)
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
                as_dataframe=False
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
