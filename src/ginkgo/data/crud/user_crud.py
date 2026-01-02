# Upstream: UserService (用户管理业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器)、MUser (MySQL用户模型)、USER_TYPES (用户类型枚举)
# Role: UserCRUD用户CRUD操作继承BaseCRUD提供用户管理和级联软删除功能支持通知系统用户管理功能


from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime
from sqlalchemy import update, or_, and_
import re

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MUser, MUserContact, MUserGroupMapping
from ginkgo.enums import SOURCE_TYPES, USER_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class UserCRUD(BaseCRUD[MUser]):
    """
    User CRUD operations with cascade soft delete.

    支持用户管理和级联软删除：
    - 删除用户时，自动软删除所有相关联系方式（MUserContact）
    - 删除用户时，自动软删除所有用户组映射（MUserGroupMapping）
    """

    _model_class = MUser

    def __init__(self):
        super().__init__(MUser)

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for UserCRUD.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'user_type': USER_TYPES,
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """
        定义 User 数据的字段配置 - 必填字段验证

        Returns:
            dict: 字段配置字典
        """
        return {
            # 用户类型 - 枚举值
            'user_type': {
                'type': 'enum',
                'choices': [t for t in USER_TYPES]
            },

            # 用户名 - 非空字符串，最大128字符
            'name': {
                'type': 'string',
                'min': 0,
                'max': 128
            },

            # 是否激活 - 布尔值
            'is_active': {
                'type': 'bool'
            }

            # source字段使用模型默认值 SOURCE_TYPES.OTHER
        }

    def _create_from_params(self, **kwargs) -> MUser:
        """
        Hook method: Create MUser from parameters.
        """
        return MUser(
            name=kwargs.get("name", ""),
            user_type=USER_TYPES.validate_input(kwargs.get("user_type", USER_TYPES.PERSON)),
            is_active=kwargs.get("is_active", True),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.OTHER)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MUser]:
        """
        Hook method: Convert objects to MUser.
        """
        # 目前没有业务对象，返回None
        return None

    def _convert_models_to_business_objects(self, models: List) -> List:
        """
        🎯 Convert models to business objects.

        Args:
            models: List of models with enum fields already fixed

        Returns:
            List of models (business object doesn't exist yet)
        """
        return models

    def _convert_output_items(self, items: List[MUser], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MUser objects for business layer.
        """
        return items

    # ==================== 级联软删除实现 ====================

    def delete(self, filters: Optional[Dict[str, Any]] = None, *args, **kwargs) -> int:
        """
        软删除用户，并级联软删除相关记录

        级联删除逻辑（按顺序避免外键约束）：
        1. 先软删除用户组映射（MUserGroupMapping.is_del=True）
        2. 再软删除联系方式（MUserContact.is_del=True）
        3. 最后软删除用户本身（set is_del=True）

        Args:
            filters: 过滤条件，如 {"uuid": "xxx"} 或 {"name": "test"}

        Returns:
            删除的用户数量

        Raises:
            ValueError: 当filters为None时
        """
        if filters is None:
            raise ValueError("filters参数必须提供")

        # 1. 查询要删除的用户
        users = self.find(filters=filters, page_size=10000, as_dataframe=False)
        user_uuids = [u.uuid for u in users]

        if not user_uuids:
            GLOG.WARNING(f"未找到匹配的用户: filters={filters}")
            return 0

        GLOG.INFO(f"开始软删除用户及其相关记录: {len(user_uuids)} 个用户")

        # 2. 先级联软删除用户组映射（避免外键约束）
        self._cascade_delete_group_mappings(user_uuids)

        # 3. 级联软删除联系方式
        self._cascade_delete_contacts(user_uuids)

        # 4. 最后软删除用户本身（直接执行 UPDATE）
        import datetime
        from sqlalchemy import update

        conn = self._get_connection()
        with conn.get_session() as session:
            # 构建过滤条件
            filter_conditions = []
            for field, value in filters.items():
                if hasattr(MUser, field):
                    filter_conditions.append(getattr(MUser, field) == value)

            # 执行软删除
            if filter_conditions:
                stmt = (
                    update(MUser.__table__)
                    .where(and_(*filter_conditions))
                    .values(is_del=True, update_at=datetime.datetime.now())
                )
                result = session.execute(stmt)
                session.commit()
                count = result.rowcount
            else:
                count = 0

        GLOG.INFO(f"已软删除用户: {count} 个")
        return count

    def _cascade_delete_contacts(self, user_uuids: List[str]) -> int:
        """
        级联软删除用户联系方式

        Args:
            user_uuids: 用户UUID列表

        Returns:
            删除的联系方式数量
        """
        try:
            # 使用 CRUD 自己的连接
            conn = self._get_connection()

            with conn.get_session() as session:
                # 批量更新联系方式
                from sqlalchemy import update
                stmt = (
                    update(MUserContact.__table__)
                    .where(MUserContact.user_id.in_(user_uuids))
                    .where(MUserContact.is_del == False)
                    .values(is_del=True, update_at=datetime.now())
                )

                result = session.execute(stmt)
                session.commit()

                contact_count = result.rowcount
                GLOG.INFO(f"已级联软删除联系方式: {contact_count} 条")
                return contact_count

        except Exception as e:
            GLOG.ERROR(f"级联删除联系方式失败: {e}")
            return 0

    def _cascade_delete_group_mappings(self, user_uuids: List[str]) -> int:
        """
        级联删除用户组映射（硬删除）

        Args:
            user_uuids: 用户UUID列表

        Returns:
            删除的映射数量
        """
        try:
            # 使用 CRUD 自己的连接
            conn = self._get_connection()

            with conn.get_session() as session:
                # 硬删除用户组映射
                from sqlalchemy import delete
                stmt = (
                    delete(MUserGroupMapping.__table__)
                    .where(MUserGroupMapping.user_uuid.in_(user_uuids))
                )

                result = session.execute(stmt)
                session.commit()

                mapping_count = result.rowcount
                GLOG.INFO(f"已级联删除用户组映射: {mapping_count} 条")
                return mapping_count

        except Exception as e:
            GLOG.ERROR(f"级联删除用户组映射失败: {e}")
            return 0

    # ==================== 业务辅助方法 ====================

    def find_by_name(self, name: str, as_dataframe: bool = False) -> Union[List[MUser], pd.DataFrame]:
        """
        按名称查询用户

        Args:
            name: 用户名称
            as_dataframe: 是否返回DataFrame

        Returns:
            用户列表或DataFrame
        """
        return self.find(filters={"name": name}, as_dataframe=as_dataframe)

    def find_by_user_type(
        self,
        user_type: Union[USER_TYPES, int],
        as_dataframe: bool = False
    ) -> Union[List[MUser], pd.DataFrame]:
        """
        按用户类型查询

        Args:
            user_type: 用户类型（枚举或整数）
            as_dataframe: 是否返回DataFrame

        Returns:
            用户列表或DataFrame
        """
        validated_type = USER_TYPES.validate_input(user_type)
        if validated_type is None:
            GLOG.WARNING(f"无效的用户类型: {user_type}")
            return [] if not as_dataframe else pd.DataFrame()

        return self.find(filters={"user_type": validated_type}, as_dataframe=as_dataframe)

    def find_active_users(self, as_dataframe: bool = False) -> Union[List[MUser], pd.DataFrame]:
        """
        查询所有激活用户

        Args:
            as_dataframe: 是否返回DataFrame

        Returns:
            用户列表或DataFrame
        """
        return self.find(filters={"is_active": True}, as_dataframe=as_dataframe)

    def fuzzy_search(
        self,
        query: str
    ) -> ModelList[MUser]:
        """
        模糊搜索用户 - 在 uuid 和 name 字段中搜索

        支持的输入格式：
        - UUID格式（32位16进制字符）：精确匹配uuid字段
        - 其他格式：在uuid和name字段中进行模糊匹配

        Args:
            query: 搜索关键词（UUID或用户名）

        Returns:
            ModelList[MUser]: 用户模型列表，支持 .to_dataframe() 和 .to_entity() 转换

        Examples:
            users = user_crud.fuzzy_search("Alice")
            df = users.to_dataframe()  # 转换为DataFrame
            entities = users.to_entity()  # 转换为实体
            first_10 = users.head(10)  # 获取前10条
        """
        # 检测是否为完整UUID格式（32位16进制字符）
        uuid_pattern = re.compile(r'^[a-f0-9]{32}$', re.IGNORECASE)
        is_full_uuid = uuid_pattern.match(query) is not None

        conn = self._get_connection()
        with conn.get_session() as s:
            if is_full_uuid:
                # 完整UUID格式：精确匹配uuid字段
                query_obj = s.query(MUser).filter(
                    MUser.uuid == query.lower()
                )
            else:
                # 非UUID格式：在uuid和name字段中进行模糊匹配
                search_pattern = f"%{query}%"
                query_obj = s.query(MUser).filter(
                    or_(
                        MUser.uuid.like(search_pattern),
                        MUser.name.like(search_pattern)
                    )
                )

            results = query_obj.all()
            # Detach objects from session
            for obj in results:
                s.expunge(obj)

        return ModelList(results, self)
