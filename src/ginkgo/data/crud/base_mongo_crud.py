# Upstream: All Concrete MongoDB CRUD Classes (继承)
# Downstream: MMongoBase (MongoDB文档模型)、GinkgoMongo (MongoDB驱动)
# Role: BaseMongoCRUD MongoDB CRUD抽象类定义增删改查操作接口支持文档持久化支持通知系统功能


from typing import TypeVar, Generic, List, Optional, Any, Dict, Type, Callable
from abc import ABC, abstractmethod
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from ginkgo.data.models.model_mongobase import MMongoBase
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
from ginkgo.libs import GLOG, time_logger, retry, cache_with_expiration
from ginkgo.data.crud.model_crud_mapping import ModelCRUDMapping

T = TypeVar("T", bound=MMongoBase)


class BaseMongoCRUD(Generic[T], ABC):
    """
    MongoDB CRUD 抽象基类

    提供 MongoDB 文档的 CRUD 操作，使用 GinkgoMongo 驱动

    Features:
    - 统一的装饰器支持 (@time_logger, @retry)
    - 泛型类型支持
    - MongoDB 特定操作 (insert_one, insert_many, find_one, find, update_one, delete_one)
    - 软删除支持 (is_del 字段)
    - ModelConversion 兼容性

    Subclass Requirements:
    - Must override _model_class with the appropriate MMongoBase subclass
    - Must override _driver with GinkgoMongo instance
    """

    # 抽象属性：子类必须重写
    _model_class: Optional[Type[T]] = None

    def __init__(self, model_class: Type[T], driver: GinkgoMongo):
        """
        初始化 MongoDB CRUD 实例

        Args:
            model_class: 对应的 MMongoBase 子类
            driver: GinkgoMongo 驱动实例
        """
        self.model_class = model_class
        self._driver = driver

    def __init_subclass__(cls, **kwargs):
        """
        子类创建时自动注册到 ModelCRUDMapping
        """
        super().__init_subclass__(**kwargs)

        # 验证子类是否重写了 _model_class
        if cls._model_class is None:
            raise NotImplementedError(
                f"MongoDB CRUD subclass '{cls.__name__}' must override '_model_class' attribute."
            )

        # 验证 model_class 是否继承自 MMongoBase
        if not issubclass(cls._model_class, MMongoBase):
            raise ValueError(
                f"Model class '{cls._model_class.__name__}' must inherit from MMongoBase"
            )

        # 自动注册到 ModelCRUDMapping
        ModelCRUDMapping.register(cls._model_class, cls)

        GLOG.DEBUG(f"Registered MongoDB CRUD: {cls.__name__} -> {cls._model_class.__name__}")

    # ==================== CRUD 操作 ====================

    @time_logger
    @retry
    def add(self, obj: T) -> Optional[str]:
        """
        添加单个文档

        Args:
            obj: MMongoBase 模型实例

        Returns:
            插入的文档 UUID，失败返回 None

        Raises:
            PyMongoError: MongoDB 操作失败
        """
        try:
            collection = self._get_collection()
            data = obj.model_dump_for_mongo()
            result = collection.insert_one(data)

            if result.inserted_id:
                GLOG.DEBUG(f"Inserted document with UUID: {obj.uuid}")
                return obj.uuid
            return None

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to insert document: {e}")
            raise

    @time_logger
    @retry
    def add_many(self, objs: List[T]) -> int:
        """
        批量添加文档

        Args:
            objs: MMongoBase 模型实例列表

        Returns:
            成功插入的文档数量

        Raises:
            PyMongoError: MongoDB 操作失败
        """
        try:
            collection = self._get_collection()
            data_list = [obj.model_dump_for_mongo() for obj in objs]
            result = collection.insert_many(data_list)

            inserted_count = len(result.inserted_ids)
            GLOG.DEBUG(f"Inserted {inserted_count} documents")
            return inserted_count

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to insert documents: {e}")
            raise

    @time_logger
    @retry
    @cache_with_expiration(expiration_seconds=60)
    def get(self, uuid: str) -> Optional[T]:
        """
        根据 UUID 查询单个文档

        缓存: 结果缓存60秒

        Args:
            uuid: 文档 UUID

        Returns:
            MMongoBase 模型实例，不存在返回 None
        """
        try:
            collection = self._get_collection()
            doc = collection.find_one({"uuid": uuid, "is_del": False})

            if doc:
                # 移除 MongoDB 的 _id 字段
                doc.pop('_id', None)
                return self.model_class.from_mongo(doc)
            return None

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to get document {uuid}: {e}")
            raise

    @time_logger
    @retry
    @cache_with_expiration(expiration_seconds=30)
    def get_all(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        sort: Optional[List[tuple]] = None
    ) -> List[T]:
        """
        查询多个文档

        缓存: 结果缓存30秒（基于查询参数）

        Args:
            filter_dict: 查询过滤条件（默认只查询未删除文档）
            limit: 返回结果数量限制
            skip: 跳过文档数量
            sort: 排序规则，如 [("create_at", -1)]

        Returns:
            MMongoBase 模型实例列表
        """
        try:
            collection = self._get_collection()

            # 默认只查询未删除的文档
            query = filter_dict.copy() if filter_dict else {}
            query.setdefault("is_del", False)

            # 构建 MongoDB 查询
            cursor = collection.find(query)

            # 应用排序
            if sort:
                cursor = cursor.sort(sort)

            # 应用跳过
            if skip:
                cursor = cursor.skip(skip)

            # 应用限制
            if limit:
                cursor = cursor.limit(limit)

            # 转换为模型列表
            results = []
            for doc in cursor:
                doc.pop('_id', None)
                results.append(self.model_class.from_mongo(doc))

            GLOG.DEBUG(f"Found {len(results)} documents")
            return results

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to query documents: {e}")
            raise

    @time_logger
    @retry
    def update(self, uuid: str, update_dict: Dict[str, Any]) -> bool:
        """
        更新文档

        Args:
            uuid: 文档 UUID
            update_dict: 更新的字段字典

        Returns:
            更新成功返回 True，文档不存在返回 False
        """
        try:
            collection = self._get_collection()

            # 自动更新 update_at 字段
            update_dict.setdefault("update_at", pd.Timestamp.now().isoformat())

            result = collection.update_one(
                {"uuid": uuid, "is_del": False},
                {"$set": update_dict}
            )

            if result.modified_count > 0:
                GLOG.DEBUG(f"Updated document {uuid}")
                return True
            return False

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to update document {uuid}: {e}")
            raise

    @time_logger
    @retry
    def delete(self, uuid: str) -> bool:
        """
        软删除文档（标记 is_del=True）

        Args:
            uuid: 文档 UUID

        Returns:
            删除成功返回 True，文档不存在返回 False
        """
        try:
            collection = self._get_collection()

            result = collection.update_one(
                {"uuid": uuid, "is_del": False},
                {"$set": {"is_del": True, "update_at": pd.Timestamp.now().isoformat()}}
            )

            if result.modified_count > 0:
                GLOG.DEBUG(f"Soft deleted document {uuid}")
                return True
            return False

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to delete document {uuid}: {e}")
            raise

    def delete_by_filters(self, filters: Dict[str, Any]) -> int:
        """
        按条件软删除文档（兼容 MySQL CRUD 接口）

        Args:
            filters: 查询过滤条件

        Returns:
            删除的文档数量
        """
        try:
            collection = self._get_collection()

            # 默认只删除未删除的文档
            filters = filters.copy()
            filters.setdefault("is_del", False)

            result = collection.update_many(
                filters,
                {"$set": {"is_del": True, "update_at": pd.Timestamp.now().isoformat()}}
            )

            GLOG.DEBUG(f"Soft deleted {result.modified_count} documents")
            return result.modified_count

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to delete documents: {e}")
            raise

    @time_logger
    @retry
    def hard_delete(self, uuid: str) -> bool:
        """
        硬删除文档（从数据库中永久删除）

        Args:
            uuid: 文档 UUID

        Returns:
            删除成功返回 True，文档不存在返回 False
        """
        try:
            collection = self._get_collection()

            result = collection.delete_one({"uuid": uuid})

            if result.deleted_count > 0:
                GLOG.DEBUG(f"Hard deleted document {uuid}")
                return True
            return False

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to hard delete document {uuid}: {e}")
            raise

    @time_logger
    def count(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        统计文档数量

        Args:
            filter_dict: 查询过滤条件

        Returns:
            文档数量
        """
        try:
            collection = self._get_collection()

            # 默认只统计未删除的文档
            query = filter_dict.copy() if filter_dict else {}
            query.setdefault("is_del", False)

            count = collection.count_documents(query)
            GLOG.DEBUG(f"Counted {count} documents")
            return count

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to count documents: {e}")
            raise

    # ==================== 兼容 MySQL CRUD 接口 ====================

    def find(
        self,
        filters: Optional[Dict[str, Any]] = None,
        as_dataframe: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort: Optional[List[tuple]] = None
    ) -> Any:
        """
        查询文档（兼容 MySQL CRUD 接口）

        Args:
            filters: 查询过滤条件（默认只查询未删除文档）
            as_dataframe: 是否返回 DataFrame（默认返回模型列表）
            limit: 返回结果数量限制
            offset: 跳过文档数量
            sort: 排序规则

        Returns:
            模型列表或 DataFrame
        """
        # 映射参数名：MySQL 使用 offset，MongoDB 使用 skip
        skip = offset

        results = self.get_all(
            filter_dict=filters,
            limit=limit,
            skip=skip,
            sort=sort
        )

        if as_dataframe:
            return self._convert_models_to_dataframe(results)
        return results

    def modify(self, filters: Dict[str, Any], updates: Dict[str, Any]) -> int:
        """
        更新文档（兼容 MySQL CRUD 接口）

        注意：此方法会更新所有匹配的文档，请确保 filters 精确

        Args:
            filters: 查询过滤条件
            updates: 更新的字段字典

        Returns:
            更新的文档数量
        """
        try:
            collection = self._get_collection()

            # 自动更新 update_at 字段
            updates.setdefault("update_at", pd.Timestamp.now().isoformat())

            # 默认只操作未删除的文档
            filters = filters.copy()
            filters.setdefault("is_del", False)

            result = collection.update_many(
                filters,
                {"$set": updates}
            )

            GLOG.DEBUG(f"Modified {result.modified_count} documents")
            return result.modified_count

        except PyMongoError as e:
            GLOG.ERROR(f"Failed to modify documents: {e}")
            raise

    # ==================== 辅助方法 ====================

    def _get_collection(self):
        """
        获取 MongoDB 集合

        Returns:
            MongoDB 集合对象
        """
        return self._driver.get_collection(
            self.model_class.get_collection_name()
        )

    def exists(self, uuid: str) -> bool:
        """
        检查文档是否存在（未删除）

        Args:
            uuid: 文档 UUID

        Returns:
            存在返回 True，否则返回 False
        """
        return self.get(uuid) is not None

    @time_logger
    def _convert_to_business_objects(self, models: List[T]) -> List[Any]:
        """
        转换为业务对象（占位实现）

        Args:
            models: 模型列表

        Returns:
            业务对象列表
        """
        # 默认返回模型本身，子类可以重写
        return models

    @time_logger
    def _convert_models_to_dataframe(self, models: List[T]) -> pd.DataFrame:
        """
        转换为 DataFrame

        Args:
            models: 模型列表

        Returns:
            pandas DataFrame
        """
        if not models:
            return pd.DataFrame()

        # 使用 Pydantic 的 model_dump 方法
        return pd.DataFrame([model.model_dump() for model in models])

    @time_logger
    def _process_dataframe_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理 DataFrame 输出（占位实现）

        Args:
            df: 输入 DataFrame

        Returns:
            处理后的 DataFrame
        """
        # 默认不做处理，子类可以重写
        return df
