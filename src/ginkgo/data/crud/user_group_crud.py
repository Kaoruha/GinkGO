# Upstream: UserGroupService (用户组管理业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器)、MUserGroup (MySQL用户组模型)
# Role: UserGroupCRUD用户组CRUD操作继承BaseCRUD提供用户组管理功能支持通知系统用户组管理功能


from typing import List, Optional, Union, Any, Dict
import pandas as pd
from sqlalchemy import or_
import re

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MUserGroup
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class UserGroupCRUD(BaseCRUD[MUserGroup]):
    """
    UserGroup CRUD operations.

    支持用户组管理：
    - 组名称（唯一标识符）
    - 组描述
    """

    _model_class = MUserGroup

    def __init__(self):
        super().__init__(MUserGroup)

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for UserGroupCRUD.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """
        定义 UserGroup 数据的字段配置 - 必填字段验证

        Returns:
            dict: 字段配置字典
        """
        return {
            # 组名称 - 必填，最大128字符
            'name': {
                'type': 'string',
                'min': 1,
                'max': 128
            },

            # 组描述 - 最大512字符
            'description': {
                'type': 'string',
                'min': 0,
                'max': 512
            }
        }

    def _create_from_params(self, **kwargs) -> MUserGroup:
        """
        Hook method: Create MUserGroup from parameters.
        """
        if 'name' not in kwargs:
            raise ValueError("name 是必填参数")

        return MUserGroup(
            name=kwargs["name"],
            description=kwargs.get("description", ""),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.OTHER)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MUserGroup]:
        """
        Hook method: Convert objects to MUserGroup.
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

    def _convert_output_items(self, items: List[MUserGroup], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MUserGroup objects for business layer.
        """
        return items

    # ==================== 业务辅助方法 ====================

    def find_by_name_pattern(self, name_pattern: str) -> List[MUserGroup]:
        """
        按名称模糊查询

        Args:
            name_pattern: 名称模式

        Returns:
            用户组列表
        """
        return self.find(filters={"name__like": name_pattern})

    def fuzzy_search(
        self,
        query: str
    ) -> ModelList[MUserGroup]:
        """
        模糊搜索用户组 - 在 uuid 和 name 字段中搜索

        支持的输入格式：
        - UUID格式（32位16进制字符）：精确匹配uuid字段
        - 其他格式：在uuid和name字段中进行模糊匹配

        Args:
            query: 搜索关键词（UUID或组名）

        Returns:
            ModelList[MUserGroup]: 用户组模型列表，支持 .to_dataframe() 和 .to_entity() 转换

        Examples:
            groups = group_crud.fuzzy_search("traders")
            df = groups.to_dataframe()  # 转换为DataFrame
            entities = groups.to_entity()  # 转换为实体
            first_10 = groups.head(10)  # 获取前10条
        """
        # 检测是否为完整UUID格式（32位16进制字符）
        uuid_pattern = re.compile(r'^[a-f0-9]{32}$', re.IGNORECASE)
        is_full_uuid = uuid_pattern.match(query) is not None

        conn = self._get_connection()
        with conn.get_session() as s:
            if is_full_uuid:
                # 完整UUID格式：精确匹配uuid字段
                query_obj = s.query(MUserGroup).filter(
                    MUserGroup.uuid == query.lower()
                )
            else:
                # 非UUID格式：在uuid和name字段中进行模糊匹配
                search_pattern = f"%{query}%"
                query_obj = s.query(MUserGroup).filter(
                    or_(
                        MUserGroup.uuid.like(search_pattern),
                        MUserGroup.name.like(search_pattern)
                    )
                )

            results = query_obj.all()
            # Detach objects from session
            for obj in results:
                s.expunge(obj)

        return ModelList(results, self)
