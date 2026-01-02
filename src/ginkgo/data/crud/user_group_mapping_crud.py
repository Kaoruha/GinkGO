# Upstream: UserGroupService (用户组管理业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器)、MUserGroupMapping (MySQL用户组映射模型)
# Role: UserGroupMappingCRUD用户组映射CRUD操作继承BaseCRUD提供用户与组的多对多关系管理功能支持通知系统用户组成员管理功能


from typing import List, Optional, Union, Any, Dict
import pandas as pd

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MUserGroupMapping
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class UserGroupMappingCRUD(BaseCRUD[MUserGroupMapping]):
    """
    UserGroupMapping CRUD operations.

    支持用户与组的多对多关系管理：
    - 用户可以加入多个组
    - 一个组可以包含多个用户
    - 唯一约束：user_uuid + group_uuid
    """

    _model_class = MUserGroupMapping

    def __init__(self):
        super().__init__(MUserGroupMapping)

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for UserGroupMappingCRUD.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """
        定义 UserGroupMapping 数据的字段配置 - 必填字段验证

        Returns:
            dict: 字段配置字典
        """
        return {
            # 用户UUID - 必填
            'user_uuid': {
                'type': 'string',
                'min': 1,
                'max': 32
            },

            # 组UUID - 必填
            'group_uuid': {
                'type': 'string',
                'min': 1,
                'max': 32
            }
        }

    def _create_from_params(self, **kwargs) -> MUserGroupMapping:
        """
        Hook method: Create MUserGroupMapping from parameters.
        """
        if 'user_uuid' not in kwargs:
            raise ValueError("user_uuid 是必填参数")
        if 'group_uuid' not in kwargs:
            raise ValueError("group_uuid 是必填参数")

        return MUserGroupMapping(
            user_uuid=kwargs["user_uuid"],
            group_uuid=kwargs["group_uuid"],
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.OTHER)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MUserGroupMapping]:
        """
        Hook method: Convert objects to MUserGroupMapping.
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

    def _convert_output_items(self, items: List[MUserGroupMapping], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MUserGroupMapping objects for business layer.
        """
        return items

    # ==================== 业务辅助方法 ====================

    def find_by_user(self, user_uuid: str, as_dataframe: bool = False) -> Union[List[MUserGroupMapping], pd.DataFrame]:
        """
        查询用户所属的所有组

        Args:
            user_uuid: 用户UUID
            as_dataframe: 是否返回DataFrame

        Returns:
            映射列表或DataFrame
        """
        return self.find(filters={"user_uuid": user_uuid}, as_dataframe=as_dataframe)

    def find_by_group(self, group_uuid: str, as_dataframe: bool = False) -> Union[List[MUserGroupMapping], pd.DataFrame]:
        """
        查询组中包含的所有用户

        Args:
            group_uuid: 组UUID
            as_dataframe: 是否返回DataFrame

        Returns:
            映射列表或DataFrame
        """
        return self.find(filters={"group_uuid": group_uuid}, as_dataframe=as_dataframe)

    def check_mapping_exists(self, user_uuid: str, group_uuid: str) -> bool:
        """
        检查映射是否存在（用户是否已在组中）

        Args:
            user_uuid: 用户UUID
            group_uuid: 组UUID

        Returns:
            存在返回True，否则返回False
        """
        results = self.find(
            filters={"user_uuid": user_uuid, "group_uuid": group_uuid},
            page_size=1,
            as_dataframe=False
        )
        return len(results) > 0

    def remove_user_from_group(self, user_uuid: str, group_uuid: str) -> int:
        """
        将用户从组中移除（软删除）

        Args:
            user_uuid: 用户UUID
            group_uuid: 组UUID

        Returns:
            删除的映射数量（0或1）
        """
        if not self.check_mapping_exists(user_uuid, group_uuid):
            GLOG.INFO(f"Mapping not found: user={user_uuid}, group={group_uuid}")
            return 0

        return self.remove(filters={"user_uuid": user_uuid, "group_uuid": group_uuid})

    def remove_user_from_all_groups(self, user_uuid: str) -> int:
        """
        将用户从所有组中移除

        Args:
            user_uuid: 用户UUID

        Returns:
            删除的映射数量
        """
        return self.remove(filters={"user_uuid": user_uuid})
