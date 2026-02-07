# Upstream: PortfolioService, API Controllers
# Downstream: MPortfolioConfig (Model), GinkgoMongo (Driver)
# Role: PortfolioConfigCRUD 投资组合配置 CRUD 操作


from typing import Optional, List, Dict, Any
from pydantic import validate_call

from ginkgo.data.models.model_portfolio_config import MPortfolioConfig
from ginkgo.data.crud.base_mongo_crud import BaseMongoCRUD
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
from ginkgo.libs import GLOG
from ginkgo.enums import SOURCE_TYPES


class PortfolioConfigCRUD(BaseMongoCRUD[MPortfolioConfig]):
    """
    投资组合配置 CRUD 操作

    提供 MongoDB 文档的 CRUD 操作，支持：
    - 基本增删改查
    - 按投资组合查询配置
    - 版本历史查询
    - 模板管理
    - 使用统计

    Attributes:
        _model_class: MPortfolioConfig 模型类
        _driver: GinkgoMongo 驱动实例

    Examples:
        >>> crud = PortfolioConfigCRUD(model_class=MPortfolioConfig, driver=mongo)
        >>> config = MPortfolioConfig(
        ...     portfolio_uuid="abc123",
        ...     name="测试配置",
        ...     graph_data='{"nodes": [], "edges": []}',
        ...     user_uuid="user123"
        ... )
        >>> crud.add(config)
    """

    # 模型类（必须重写）
    _model_class = MPortfolioConfig

    def __init__(self, driver: GinkgoMongo):
        """
        初始化 PortfolioConfigCRUD

        Args:
            driver: GinkgoMongo 驱动实例
        """
        super().__init__(model_class=self._model_class, driver=driver)

    # ==================== 基本操作 ====================

    @validate_call
    def add(self, obj: MPortfolioConfig) -> Optional[str]:
        """
        添加配置文档

        Args:
            obj: MPortfolioConfig 模型实例

        Returns:
            插入的配置 UUID，失败返回 None

        Examples:
            >>> config = MPortfolioConfig(...)
            >>> uuid = crud.add(config)
        """
        return super().add(obj)

    @validate_call
    def get(self, uuid: str) -> Optional[MPortfolioConfig]:
        """
        根据 UUID 查询配置

        Args:
            uuid: 配置 UUID

        Returns:
            MPortfolioConfig 实例，不存在返回 None

        Examples:
            >>> config = crud.get("abc123...")
        """
        return super().get(uuid)

    def get_by_portfolio(self, portfolio_uuid: str, version: Optional[int] = None) -> Optional[MPortfolioConfig]:
        """
        查询投资组合的指定版本配置

        Args:
            portfolio_uuid: 投资组合 UUID
            version: 版本号，None 表示最新版本

        Returns:
            MPortfolioConfig 实例，不存在返回 None

        Examples:
            >>> config = crud.get_by_portfolio("portfolio_uuid")
            >>> config = crud.get_by_portfolio("portfolio_uuid", version=2)
        """
        try:
            collection = self._get_collection()

            # 构建查询条件
            query = {
                "portfolio_uuid": portfolio_uuid,
                "is_del": False
            }

            if version is not None:
                query["version"] = version
            else:
                # 查询最新版本（version 最大的）
                sort = [("version", -1)]
                docs = list(collection.find(query).sort(sort).limit(1))
                if docs:
                    docs[0].pop('_id', None)
                    return self._model_class.from_mongo(docs[0])
                return None

            doc = collection.find_one(query)
            if doc:
                doc.pop('_id', None)
                return self._model_class.from_mongo(doc)
            return None

        except Exception as e:
            GLOG.ERROR(f"Failed to get config for portfolio {portfolio_uuid}: {e}")
            return None

    def get_all_versions(self, portfolio_uuid: str) -> List[MPortfolioConfig]:
        """
        查询投资组合的所有版本配置

        Args:
            portfolio_uuid: 投资组合 UUID

        Returns:
            配置列表，按版本号降序排列

        Examples:
            >>> versions = crud.get_all_versions("portfolio_uuid")
        """
        try:
            collection = self._get_collection()

            query = {
                "portfolio_uuid": portfolio_uuid,
                "is_del": False
            }

            sort = [("version", -1)]
            docs = collection.find(query).sort(sort)

            results = []
            for doc in docs:
                doc.pop('_id', None)
                results.append(self._model_class.from_mongo(doc))

            return results

        except Exception as e:
            GLOG.ERROR(f"Failed to get versions for portfolio {portfolio_uuid}: {e}")
            return []

    def get_active_config(self, portfolio_uuid: str) -> Optional[MPortfolioConfig]:
        """
        获取投资组合的活跃配置（最新版本）

        Args:
            portfolio_uuid: 投资组合 UUID

        Returns:
            MPortfolioConfig 实例，不存在返回 None

        Examples:
            >>> config = crud.get_active_config("portfolio_uuid")
        """
        return self.get_by_portfolio(portfolio_uuid, version=None)

    # ==================== 版本管理 ====================

    def create_version(self, portfolio_uuid: str, graph_data: Dict[str, Any],
                       name: Optional[str] = None, description: Optional[str] = None,
                       user_uuid: Optional[str] = None) -> Optional[MPortfolioConfig]:
        """
        创建配置的新版本

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 新的节点图数据
            name: 配置名称（可选，继承父版本）
            description: 配置描述（可选）
            user_uuid: 用户 UUID

        Returns:
            新版本配置实例，失败返回 None

        Examples:
            >>> new_config = crud.create_version(
            ...     portfolio_uuid="abc123",
            ...     graph_data={"nodes": [...], "edges": [...]},
            ...     user_uuid="user123"
            ... )
        """
        try:
            import uuid
            import json

            # 获取当前最新版本作为父版本
            current = self.get_active_config(portfolio_uuid)

            # 构建新版本数据
            version_data = {
                "portfolio_uuid": portfolio_uuid,
                "graph_data": json.dumps(graph_data, ensure_ascii=False),
                "mode": current.mode if current else "BACKTEST",
                "version": (current.version if current else 0) + 1,
                "parent_uuid": current.uuid if current else None,
                "user_uuid": user_uuid or (current.user_uuid if current else ""),
                "name": name or (current.name if current else "未命名配置"),
                "description": description or (current.description if current else ""),
                "is_template": False,
                "is_public": False,
                "tags": current.tags if current else [],
                "config_locked": False
            }

            # 保存新版本
            new_config = MPortfolioConfig(**version_data)
            return self.add(new_config)

        except Exception as e:
            GLOG.ERROR(f"Failed to create version for portfolio {portfolio_uuid}: {e}")
            return None

    # ==================== 模板管理 ====================

    def get_templates(self, user_uuid: Optional[str] = None,
                     mode: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     limit: int = 50) -> List[MPortfolioConfig]:
        """
        查询模板配置列表

        Args:
            user_uuid: 用户 UUID（None 表示查询公共模板）
            mode: 运行模式过滤
            tags: 标签过滤（包含任一标签）
            limit: 返回数量限制

        Returns:
            模板配置列表

        Examples:
            >>> templates = crud.get_templates(mode="BACKTEST")
            >>> templates = crud.get_templates(tags=["双均线"])
        """
        try:
            collection = self._get_collection()

            query = {
                "is_template": True,
                "is_del": False
            }

            if user_uuid:
                query["user_uuid"] = user_uuid
            else:
                query["is_public"] = True

            if mode:
                query["mode"] = mode

            if tags:
                query["tags"] = {"$in": tags}

            sort = [("usage_count", -1), ("create_at", -1)]

            docs = collection.find(query).sort(sort).limit(limit)

            results = []
            for doc in docs:
                doc.pop('_id', None)
                results.append(self._model_class.from_mongo(doc))

            return results

        except Exception as e:
            GLOG.ERROR(f"Failed to get templates: {e}")
            return []

    def save_as_template(self, config_uuid: str, template_name: str,
                        is_public: bool = False,
                        description: Optional[str] = None) -> bool:
        """
        将现有配置保存为模板

        Args:
            config_uuid: 配置 UUID
            template_name: 模板名称
            is_public: 是否为公共模板
            description: 模板描述

        Returns:
            成功返回 True，失败返回 False

        Examples:
            >>> success = crud.save_as_template(
            ...     config_uuid="abc123...",
            ...     template_name="双均线策略模板",
            ...     is_public=True
            ... )
        """
        try:
            config = self.get(config_uuid)
            if not config:
                return False

            # 创建模板副本
            import uuid
            template_data = {
                "portfolio_uuid": "",  # 模板不属于任何 portfolio
                "name": template_name,
                "description": description or config.description,
                "graph_data": config.graph_data,
                "mode": config.mode,
                "version": 1,
                "parent_uuid": None,
                "user_uuid": config.user_uuid,
                "is_template": True,
                "is_public": is_public,
                "tags": config.tags.copy(),
                "initial_cash": config.initial_cash,
                "config_locked": False
            }

            template = MPortfolioConfig(**template_data)
            result = self.add(template)
            return result is not None

        except Exception as e:
            GLOG.ERROR(f"Failed to save template from {config_uuid}: {e}")
            return False

    def use_template(self, template_uuid: str, portfolio_uuid: str,
                    user_uuid: str, name: Optional[str] = None) -> Optional[str]:
        """
        从模板创建配置

        Args:
            template_uuid: 模板 UUID
            portfolio_uuid: 投资组合 UUID
            user_uuid: 用户 UUID
            name: 配置名称（可选，使用模板名称）

        Returns:
            新配置 UUID，失败返回 None

        Examples:
            >>> config_uuid = crud.use_template(
            ...     template_uuid="template123...",
            ...     portfolio_uuid="portfolio123...",
            ...     user_uuid="user123"
            ... )
        """
        try:
            template = self.get(template_uuid)
            if not template:
                return None

            import uuid
            config_data = {
                "portfolio_uuid": portfolio_uuid,
                "name": name or template.name,
                "description": template.description,
                "graph_data": template.graph_data,
                "mode": template.mode,
                "version": 1,
                "parent_uuid": None,
                "user_uuid": user_uuid,
                "is_template": False,
                "is_public": False,
                "tags": template.tags.copy(),
                "initial_cash": template.initial_cash,
                "config_locked": False
            }

            config = MPortfolioConfig(**config_data)
            config_uuid = self.add(config)

            # 增加模板使用计数
            if config_uuid:
                self.update(  template_uuid,
                    {"usage_count": template.usage_count + 1}
                )

            return config_uuid

        except Exception as e:
            GLOG.ERROR(f"Failed to use template {template_uuid}: {e}")
            return None

    # ==================== 查询操作 ====================

    def search(self, keyword: str, user_uuid: Optional[str] = None,
               limit: int = 20) -> List[MPortfolioConfig]:
        """
        搜索配置（按名称或描述）

        Args:
            keyword: 搜索关键词
            user_uuid: 用户 UUID（None 表示搜索公共模板）
            limit: 返回数量限制

        Returns:
            配置列表

        Examples:
            >>> results = crud.search("双均线", user_uuid="user123")
        """
        try:
            collection = self._get_collection()

            query = {
                "is_del": False,
                "$or": [
                    {"name": {"$regex": keyword, "$options": "i"}},
                    {"description": {"$regex": keyword, "$options": "i"}}
                ]
            }

            if user_uuid:
                query["$and"] = [
                    {"$or": [{"user_uuid": user_uuid}, {"is_public": True}]}
                ]
            else:
                query["is_public"] = True

            sort = [("update_at", -1)]
            docs = collection.find(query).sort(sort).limit(limit)

            results = []
            for doc in docs:
                doc.pop('_id', None)
                results.append(self._model_class.from_mongo(doc))

            return results

        except Exception as e:
            GLOG.ERROR(f"Failed to search configs: {e}")
            return []

    def get_user_configs(self, user_uuid: str, mode: Optional[str] = None) -> List[MPortfolioConfig]:
        """
        获取用户的配置列表

        Args:
            user_uuid: 用户 UUID
            mode: 运行模式过滤

        Returns:
            配置列表

        Examples:
            >>> configs = crud.get_user_configs("user123", mode="BACKTEST")
        """
        try:
            collection = self._get_collection()

            query = {
                "user_uuid": user_uuid,
                "is_del": False,
                "is_template": False  # 排除模板
            }

            if mode:
                query["mode"] = mode

            sort = [("update_at", -1)]
            docs = collection.find(query).sort(sort)

            results = []
            for doc in docs:
                doc.pop('_id', None)
                results.append(self._model_class.from_mongo(doc))

            return results

        except Exception as e:
            GLOG.ERROR(f"Failed to get user configs: {e}")
            return []

    # ==================== 统计操作 ====================

    def count_by_mode(self, mode: str) -> int:
        """
        统计指定模式的配置数量

        Args:
            mode: 运行模式

        Returns:
            配置数量

        Examples:
            >>> count = crud.count_by_mode("BACKTEST")
        """
        try:
            collection = self._get_collection()
            query = {
                "mode": mode,
                "is_del": False
            }
            return collection.count_documents(query)

        except Exception as e:
            GLOG.ERROR(f"Failed to count configs by mode {mode}: {e}")
            return 0

    def count_user_configs(self, user_uuid: str) -> int:
        """
        统计用户的配置数量

        Args:
            user_uuid: 用户 UUID

        Returns:
            配置数量

        Examples:
            >>> count = crud.count_user_configs("user123")
        """
        try:
            collection = self._get_collection()
            query = {
                "user_uuid": user_uuid,
                "is_del": False
            }
            return collection.count_documents(query)

        except Exception as e:
            GLOG.ERROR(f"Failed to count user configs: {e}")
            return 0
