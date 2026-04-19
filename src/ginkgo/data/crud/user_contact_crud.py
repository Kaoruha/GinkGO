# Upstream: UserService (用户管理业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器)、MUserContact (MySQL联系方式模型)、CONTACT_TYPES (联系方式类型枚举)
# Role: UserContactCRUD联系方式CRUD操作继承BaseCRUD提供联系方式管理功能支持通知系统联系方式管理功能


from typing import List, Optional, Union, Any, Dict
import pandas as pd

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MUserContact
from ginkgo.enums import SOURCE_TYPES, CONTACT_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class UserContactCRUD(BaseCRUD[MUserContact]):
    """
    UserContact CRUD operations.

    支持用户联系方式管理：
    - 邮箱联系方式（EMAIL）
    - Discord Webhook联系方式（DISCORD）
    - 主联系方式标记（is_primary）
    """

    _model_class = MUserContact

    def __init__(self):
        super().__init__(MUserContact)

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for UserContactCRUD.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'contact_type': CONTACT_TYPES,
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """
        定义 UserContact 数据的字段配置 - 必填字段验证

        Returns:
            dict: 字段配置字典
        """
        return {
            # 联系方式类型 - 枚举值
            'contact_type': {
                'type': 'enum',
                'choices': [t for t in CONTACT_TYPES]
            },

            # 用户ID - 必填
            'user_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },

            # 联系地址 - 最大512字符
            'address': {
                'type': 'string',
                'min': 0,
                'max': 512
            },

            # 是否主要联系方式 - 布尔值
            'is_primary': {
                'type': 'boolean'
            },

            # 是否启用 - 布尔值
            'is_active': {
                'type': 'boolean'
            }
        }

    def _create_from_params(self, **kwargs) -> MUserContact:
        """
        Hook method: Create MUserContact from parameters.
        """
        if 'user_id' not in kwargs:
            raise ValueError("user_id 是必填参数")

        return MUserContact(
            user_id=kwargs["user_id"],
            contact_type=CONTACT_TYPES.validate_input(kwargs.get("contact_type", CONTACT_TYPES.EMAIL)),
            address=kwargs.get("address", ""),
            is_primary=kwargs.get("is_primary", False),
            is_active=kwargs.get("is_active", True),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.OTHER)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MUserContact]:
        """
        Hook method: Convert objects to MUserContact.
        """
        return None

    def _convert_models_to_business_objects(self, models: List) -> List:
        """
        🎯 Convert models to business objects.

        Args:
            models: List of models with enum fields already fixed

        Returns:
            List of models
        """
        return models

    def _convert_output_items(self, items: List[MUserContact], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MUserContact objects for business layer.
        """
        return items

    # ==================== 业务辅助方法 ====================

    def get_by_user(
        self,
        user_id: str,
        is_active: Optional[bool] = None
    ) -> List[MUserContact]:
        """
        按用户ID查询联系方式（别名方法）

        Args:
            user_id: 用户UUID
            is_active: 是否只查询启用的联系方式（可选）

        Returns:
            联系方式列表
        """
        filters = {"user_id": user_id}
        if is_active is not None:
            filters["is_active"] = is_active


    def find_by_user_id(
        self,
        user_id: str,
    ) -> List[MUserContact]:
        """
        按用户ID查询联系方式

        Args:
            user_id: 用户UUID

        Returns:
            联系方式列表
        """
        return self.find(filters={"user_id": user_id})

    def find_by_contact_type(
        self,
        contact_type: Union[CONTACT_TYPES, int],
    ) -> List[MUserContact]:
        """
        按联系方式类型查询

        Args:
            contact_type: 联系方式类型（枚举或整数）

        Returns:
            联系方式列表
        """
        validated_type = CONTACT_TYPES.validate_input(contact_type)
        if validated_type is None:
            GLOG.WARN(f"无效的联系方式类型: {contact_type}")
            return []

        return self.find(filters={"contact_type": validated_type})

    def find_primary_contacts(self) -> List[MUserContact]:
        """
        查询所有主联系方式

        Returns:
            联系方式列表
        """
        return self.find(filters={"is_primary": True})

    def find_active_contacts(
        self,
        user_id: Optional[str] = None,
    ) -> List[MUserContact]:
        """
        查询启用的联系方式

        Args:
            user_id: 用户UUID（可选，如果提供则只查询该用户的启用联系方式）

        Returns:
            联系方式列表
        """
        filters = {"is_active": True}
        if user_id:
            filters["user_id"] = user_id

        return self.find(filters=filters)
