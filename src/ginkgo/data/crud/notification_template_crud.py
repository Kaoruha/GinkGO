# Upstream: NotificationTemplateService (通知模板业务逻辑)、TemplateEngine (模板引擎渲染)
# Downstream: BaseMongoCRUD (继承提供MongoDB CRUD基础能力)、MNotificationTemplate (通知模板模型)
# Role: NotificationTemplateCRUD通知模板CRUD操作封装模板的增删改查和按template_id查询支持通知模板管理功能


"""
Notification Template CRUD

通知模板 CRUD 操作层，提供模板的增删改查功能。
"""

from typing import Dict, Any, List, Optional, Generic
from datetime import datetime

from ginkgo.data.crud.base_mongo_crud import BaseMongoCRUD
from ginkgo.data.models.model_notification_template import MNotificationTemplate
from ginkgo.libs import GLOG


class NotificationTemplateCRUD(BaseMongoCRUD[MNotificationTemplate]):
    """
    通知模板 CRUD 操作

    提供模板的基本 CRUD 操作和业务辅助方法。
    """

    # 必须重写的类属性
    _model_class = MNotificationTemplate

    def __init__(self, model_class=None, driver=None):
        """
        初始化 NotificationTemplateCRUD

        Args:
            model_class: MNotificationTemplate 类 (可选，默认使用 _model_class)
            driver: GinkgoMongo 驱动实例 (可选，从全局获取)
        """
        from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
        from ginkgo.libs import GCONF

        # 使用默认值
        if model_class is None:
            model_class = self._model_class
        if driver is None:
            driver = GinkgoMongo(
                user=GCONF.MONGOUSER,
                pwd=GCONF.MONGOPWD,
                host=GCONF.MONGOHOST,
                port=int(GCONF.MONGOPORT),
                db=GCONF.MONGODB,
            )

        super().__init__(model_class=model_class, driver=driver)

    def add(self, template: MNotificationTemplate) -> Optional[str]:
        """
        添加通知模板

        Args:
            template: MNotificationTemplate 实例

        Returns:
            str: 模板的 UUID，失败返回 None
        """
        try:
            # 检查 template_id 是否已存在
            existing = self.get_by_template_id(template.template_id)
            if existing is not None:
                GLOG.ERROR(f"Template with template_id '{template.template_id}' already exists")
                return None

            # 调用父类方法添加
            return super().add(template)

        except Exception as e:
            GLOG.ERROR(f"Error adding notification template: {e}")
            return None

    def get_by_template_id(self, template_id: str) -> Optional[MNotificationTemplate]:
        """
        根据 template_id 查询模板

        Args:
            template_id: 模板唯一标识符

        Returns:
            MNotificationTemplate: 模板实例，不存在返回 None
        """
        try:
            collection = self._get_collection()

            doc = collection.find_one({
                "template_id": template_id,
                "is_del": False
            })

            if doc:
                return self._doc_to_model(doc)

            return None

        except Exception as e:
            GLOG.ERROR(f"Error getting template by template_id '{template_id}': {e}")
            return None

    def get_by_template_name(self, template_name: str) -> List[MNotificationTemplate]:
        """
        根据模板名称模糊查询模板

        Args:
            template_name: 模板名称（支持部分匹配）

        Returns:
            List[MNotificationTemplate]: 模板列表
        """
        try:
            collection = self._get_collection()

            docs = collection.find({
                "template_name": {"$regex": template_name, "$options": "i"},
                "is_del": False
            }).to_list(None)

            return [self._doc_to_model(doc) for doc in docs]

        except Exception as e:
            GLOG.ERROR(f"Error getting templates by name '{template_name}': {e}")
            return []

    def get_active_templates(self, template_type: Optional[int] = None) -> List[MNotificationTemplate]:
        """
        获取所有启用的模板

        Args:
            template_type: 可选的模板类型过滤

        Returns:
            List[MNotificationTemplate]: 启用的模板列表
        """
        try:
            collection = self._get_collection()

            query = {"is_active": True, "is_del": False}
            if template_type is not None:
                query["template_type"] = template_type

            docs = collection.find(query).to_list(None)

            return [self._doc_to_model(doc) for doc in docs]

        except Exception as e:
            GLOG.ERROR(f"Error getting active templates: {e}")
            return []

    def get_by_tags(self, tags: List[str], match_all: bool = False) -> List[MNotificationTemplate]:
        """
        根据标签查询模板

        Args:
            tags: 标签列表
            match_all: 是否匹配所有标签（True）或任一标签（False）

        Returns:
            List[MNotificationTemplate]: 模板列表
        """
        try:
            collection = self._get_collection()

            if match_all:
                # 匹配所有标签
                query = {
                    "tags": {"$all": tags},
                    "is_del": False
                }
            else:
                # 匹配任一标签
                query = {
                    "tags": {"$in": tags},
                    "is_del": False
                }

            docs = collection.find(query).to_list(None)

            return [self._doc_to_model(doc) for doc in docs]

        except Exception as e:
            GLOG.ERROR(f"Error getting templates by tags '{tags}': {e}")
            return []

    def update_by_template_id(
        self,
        template_id: str,
        content: Optional[str] = None,
        subject: Optional[str] = None,
        is_active: Optional[bool] = None,
        variables: Optional[str] = None,
        template_name: Optional[str] = None,
        desc: Optional[str] = None
    ) -> int:
        """
        根据 template_id 更新模板

        Args:
            template_id: 模板唯一标识符
            content: 新的模板内容
            subject: 新的主题
            is_active: 是否启用
            variables: 新的变量定义（JSON字符串）
            template_name: 新的模板名称
            desc: 新的模板描述

        Returns:
            int: 更新的文档数量
        """
        try:
            collection = self._get_collection()

            update_data = {"update_at": datetime.now()}

            if content is not None:
                update_data["content"] = content
            if subject is not None:
                update_data["subject"] = subject
            if is_active is not None:
                update_data["is_active"] = is_active
            if variables is not None:
                update_data["variables"] = variables
            if template_name is not None:
                update_data["template_name"] = template_name
            if desc is not None:
                update_data["desc"] = desc

            result = collection.update_many(
                {"template_id": template_id, "is_del": False},
                {"$set": update_data}
            )

            return result.modified_count

        except Exception as e:
            GLOG.ERROR(f"Error updating template by template_id '{template_id}': {e}")
            return 0

    def _doc_to_model(self, doc: Dict[str, Any]) -> MNotificationTemplate:
        """
        将 MongoDB 文档转换为模型实例

        Args:
            doc: MongoDB 文档

        Returns:
            MNotificationTemplate: 模型实例
        """
        return MNotificationTemplate.from_mongo(doc)
