# Upstream: UserService (用户管理业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器)、MUserCredential (MySQL凭据模型)
# Role: UserCredentialCRUD凭据CRUD操作继承BaseCRUD提供用户凭据管理功能


from typing import List, Optional, Any, Dict

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MUserCredential
from ginkgo.enums import SOURCE_TYPES
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class UserCredentialCRUD(BaseCRUD[MUserCredential]):

    _model_class = MUserCredential

    def __init__(self):
        super().__init__(MUserCredential)

    def _get_enum_mappings(self) -> Dict[str, Any]:
        return {
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        return {
            'user_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            'password_hash': {
                'type': 'string',
                'min': 0,
                'max': 256
            },
            'is_active': {
                'type': 'boolean'
            },
            'is_admin': {
                'type': 'boolean'
            }
        }

    def _create_from_params(self, **kwargs) -> MUserCredential:
        if 'user_id' not in kwargs:
            raise ValueError("user_id 是必填参数")

        return MUserCredential(
            user_id=kwargs["user_id"],
            password_hash=kwargs.get("password_hash", ""),
            is_active=kwargs.get("is_active", True),
            is_admin=kwargs.get("is_admin", False),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.OTHER)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MUserCredential]:
        return None

    def _convert_models_to_business_objects(self, models: List) -> List:
        return models

    def _convert_output_items(self, items: List[MUserCredential], output_type: str = "model") -> List[Any]:
        return items

    def get_by_user_id(self, user_id: str) -> Optional[MUserCredential]:
        results = self.find(filters={"user_id": user_id})
        return results.first()
