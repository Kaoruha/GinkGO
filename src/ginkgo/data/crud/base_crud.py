# Upstream: 所有具体CRUD类 (BarCRUD/TickCRUD/AnalyzerRecordCRUD等30+个)
# Downstream: MClickBase/MMysqlBase/MMongoBase (数据模型基类)、ClickHouse/MySQL/MongoDB (数据库驱动)
# Role: 抽象基类CRUD，定义模板方法和增删改查接口，支持分页和source字段过滤




from typing import TypeVar, Generic, List, Optional, Any, Union, Dict, Callable, Type
from abc import ABC, abstractmethod
import pandas as pd
from sqlalchemy import and_, delete, text, update
from sqlalchemy.orm import Session

from ginkgo.data.drivers import get_db_connection, add, add_all
from ginkgo.data.models import MClickBase, MMysqlBase, MMongoBase
from ginkgo.libs import GLOG, time_logger, retry, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access
from ginkgo.data.crud.model_crud_mapping import ModelCRUDMapping
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.crud.mixins import _Conversion, _Validation, _Streaming

T = TypeVar("T", bound=Union[MClickBase, MMysqlBase, MMongoBase])


class CRUDResult:
    """
    CRUD查询结果包装器

    统一处理CRUD操作的结果，支持链式转换：
    - to_entities(): 转换为实体
    - to_dataframe(): 转换为DataFrame
    - first(): 获取第一个结果
    - count(): 获取结果数量
    """

    def __init__(self, models: List[T], crud_instance: 'BaseCRUD'):
        """
        初始化CRUD结果包装器

        Args:
            models: 原始模型对象列表
            crud_instance: CRUD实例，用于转换方法
        """
        self._models = models
        self._crud_instance = crud_instance
        self._business_objects_cache = None
        self._dataframe_cache = None

    def to_business_objects(self) -> List[Any]:
        """
        转换为业务对象

        Returns:
            List of business objects with enum fields converted
        """
        if self._business_objects_cache is None:
            self._business_objects_cache = self._crud_instance._convert_to_business_objects(self._models)
        return self._business_objects_cache

    def to_dataframe(self) -> pd.DataFrame:
        """
        转换为DataFrame

        支持多种模型类型：
        - SQLAlchemy 模型：使用 __dict__ 属性
        - Pydantic 模型：使用 model_dump() 方法

        Returns:
            pandas DataFrame containing the data
        """
        if self._dataframe_cache is None:
            if not self._models:
                self._dataframe_cache = pd.DataFrame()
            else:
                # 检测模型类型并使用相应的序列化方法
                if self._models and hasattr(self._models[0], 'model_dump'):
                    # Pydantic 模型 (MMongoBase)
                    df = pd.DataFrame([model.model_dump() for model in self._models])
                else:
                    # SQLAlchemy 模型 (MClickBase, MMysqlBase)
                    df = pd.DataFrame([model.__dict__ for model in self._models])
                    # 移除非数据列
                    columns_to_remove = ['_sa_instance_state']
                    for col in columns_to_remove:
                        if col in df.columns:
                            df = df.drop(col, axis=1)
                # 应用enum转换
                self._dataframe_cache = self._crud_instance._process_dataframe_output(df)
        return self._dataframe_cache

    def first(self) -> Optional[T]:
        """
        获取第一个结果

        Returns:
            First model in the result list, or None if empty
        """
        return self._models[0] if self._models else None

    def count(self) -> int:
        """
        获取结果数量

        Returns:
            Number of results
        """
        return len(self._models)

    def is_empty(self) -> bool:
        """
        检查结果是否为空

        Returns:
            True if no results, False otherwise
        """
        return len(self._models) == 0

    def filter(self, predicate: Callable[[T], bool]) -> 'CRUDResult':
        """
        过滤结果

        Args:
            predicate: 过滤函数，接受model参数，返回bool

        Returns:
            New CRUDResult with filtered models
        """
        filtered_models = [model for model in self._models if predicate(model)]
        return CRUDResult(filtered_models, self._crud_instance)

    def map(self, func: Callable[[T], Any]) -> List[Any]:
        """
        映射结果

        Args:
            func: 映射函数，接受model参数

        Returns:
            List of mapped results
        """
        return [func(model) for model in self._models]

    def __iter__(self):
        """支持迭代"""
        return iter(self._models)

    def __len__(self):
        """支持len()函数"""
        return len(self._models)

    def __getitem__(self, index):
        """支持索引访问"""
        return self._models[index]

    def __bool__(self):
        """支持布尔判断"""
        return bool(self._models)

    def __repr__(self):
        """字符串表示"""
        model_type = type(self._models[0]).__name__ if self._models else "No models"
        return f"CRUDResult(count={len(self._models)}, type={model_type})"


@restrict_crud_access
class _CoreCRUD(Generic[T], ABC):
    """
    BaseCRUD 的核心 CRUD 实现（内部类，不对外导出）。

    通过 Python 多重继承将实现分散到多个文件：
    - _CoreCRUD: 核心 CRUD 操作（本文件）
    - _Conversion: 类型转换和枚举处理
    - _Validation: 数据验证和 ClickHouse 处理
    - _Streaming: 流式查询和监控

    公开 API 是 BaseCRUD，子类继承 BaseCRUD 即可。

    Validation Architecture:
    - create() → _validate_before_database() → validate_data_by_config(_get_field_config())
    - Subclasses define validation rules by overriding _get_field_config()
    - All validation is configuration-driven and executed automatically

    Subclass Requirements:
    - Must override _model_class with the appropriate Model class
    - Must implement _get_field_config() for validation
    """

    # 抽象属性：子类必须重写
    # 用法说明：
    # 1. 子类必须设置 _model_class = MYourModel 来指定对应的Model类
    # 2. __init_subclass__ 会验证 _model_class 是否被正确设置
    # 3. 自动注册机制会使用 _model_class 来建立 Model-CRUD 映射关系
    # 4. 如果 _model_class = None，则抛出 NotImplementedError（特殊类如TickCRUD除外）
    _model_class: Optional[Type[T]] = None

    def __init__(self, model_class: type[T]):
        """
        初始化CRUD实例

        Args:
            model_class: 对应的Model类，如 MBar, MStockInfo, MMongoBase 子类等

        用法说明：
        1. model_class 参数用于设置实例变量 self.model_class
        2. 与类级别的 _model_class 不同：_model_class 用于注册，model_class 用于运行时
        3. 子类通常调用 super().__init__(MYourModel) 来传递正确的Model类
        """
        self.model_class = model_class
        self._is_clickhouse = issubclass(model_class, MClickBase)
        self._is_mysql = issubclass(model_class, MMysqlBase)
        self._is_mongo = issubclass(model_class, MMongoBase)

        if not (self._is_clickhouse or self._is_mysql or self._is_mongo):
            raise ValueError(f"Model {model_class} must inherit from MClickBase, MMysqlBase, or MMongoBase")

        # 流式查询相关属性（默认禁用，不影响现有功能）
        self._streaming_enabled = False
        self._streaming_engine = None
        self._streaming_config = None
        self._streaming_initialized = False

    def __init_subclass__(cls, **kwargs):
        """
        🎯 关键：CRUD子类创建时自动注册关系和验证
        当任何CRUD子类被定义时，这个方法会被Python自动调用

        _model_class 生命周期和作用：
        1. 类定义时：Python调用 __init_subclass__，验证 cls._model_class 是否设置
        2. 验证阶段：检查 _model_class 是否继承自 MClickBase 或 MMysqlBase
        3. 注册阶段：使用 _model_class 调用 ModelCRUDMapping.register(model_class, cls)
        4. 运行时：可通过 self.model_class 访问实例变量（由__init__设置）

        特殊情况：
        - TickCRUD 等动态Model类可以豁免 _model_class 验证
        - 其他所有CRUD子类必须设置 _model_class
        """
        super().__init_subclass__(**kwargs)

        # 验证子类是否重写了 _model_class（特殊情况可以豁免）
        _exempt_classes = ['TickCRUD', 'BaseCRUD']
        if cls._model_class is None and cls.__name__ not in _exempt_classes:
            raise NotImplementedError(
                f"CRUD subclass '{cls.__name__}' must override '_model_class' attribute. "
                f"Example: _model_class = MYourModel"
            )

        # 验证 _model_class 是否继承自正确的基类（特殊情况跳过验证）
        if cls.__name__ not in _exempt_classes:
            model_class = cls._model_class
            if not (issubclass(model_class, MClickBase) or issubclass(model_class, MMysqlBase) or issubclass(model_class, MMongoBase)):
                raise TypeError(
                    f"CRUD subclass '{cls.__name__}': _model_class must inherit from "
                    f"MClickBase, MMysqlBase, or MMongoBase, but got {model_class.__bases__}"
                )

            # 自动建立Model-CRUD映射关系
            # 这里使用从类级别 _model_class 获取的 model_class 进行注册
            # 建立映射后，可以通过 ModelCRUDMapping.get_crud_class(MBar) 找到 BarCRUD
            ModelCRUDMapping.register(model_class, cls)
            GLOG.DEBUG(f"Auto-registered: {model_class.__name__} → {cls.__name__}")
        else:
            GLOG.DEBUG(f"Skipped auto-registration for {cls.__name__} (dynamic model class)")

    def _get_connection(self):
        """Get appropriate database connection based on model type"""
        return get_db_connection(self.model_class)

    def get_session(self) -> Session:
        """Get a new database session for external transaction management."""
        return self._get_connection().get_session()

    # ============================================================================
    # Template Methods - With unified decorators, should not be overridden
    # ============================================================================

    @time_logger
    @retry(max_try=3)
    def add(self, item: T, session: Optional[Session] = None) -> T:
        """
        Template method: Add single item to database.
        直接添加对象，不进行数据验证，依赖数据库约束确保数据完整性。
        Subclasses should override _do_add() instead.

        Args:
            item: Model instance to add
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            Added model instance
        """
        try:
            return self._do_add(item, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to add {self.model_class.__name__} item: {e}")
            raise

    @time_logger
    @retry(max_try=3)
    def add_batch(self, items: List[Any], session: Optional[Session] = None) -> ModelList:
        """
        Template method: Add multiple items to database in batch.
        支持自动类型转换，不进行数据验证，依赖数据库约束确保数据完整性。
        Subclasses should override _do_add_batch() instead.

        Args:
            items: List of model instances or convertible objects
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            ModelList of added model instances with conversion capabilities
        """
        try:
            # 只进行类型转换，不进行数据验证
            converted_items = self._convert_input_batch(items)
            result = self._do_add_batch(converted_items, session)
            # 返回实际插入的对象（已解绑session），而不是原始转换的对象
            return ModelList(converted_items, self)
        except Exception as e:
            GLOG.ERROR(f"Failed to add {self.model_class.__name__} items in batch: {e}")
            raise

    @time_logger
    @retry(max_try=3)
    def create(self, session: Optional[Session] = None, **kwargs) -> T:
        """
        Template method: Create object from parameters and add to database.
        Applies data validation before creating object.
        Subclasses should override _create_from_params() instead.

        Args:
            session: Optional SQLAlchemy session to use for the operation.
            **kwargs: Parameters to create the object

        Returns:
            Created model instance
        """
        try:
            # 先验证参数数据
            validated_kwargs = self._validate_before_database(kwargs)
            item = self._create_from_params(**validated_kwargs)
            return self._do_add(item, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to create {self.model_class.__name__} from params: {e}")
            raise

    @time_logger
    def find(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[str] = None,
        desc_order: bool = False,
        distinct_field: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> ModelList[T]:
        """
        Template method: Find items with enhanced filters and pagination.
        Supports operator filters like field__gte, field__lte, field__in.
        Subclasses should override _do_find() instead.

        Args:
            filters: Dictionary of field -> value filters (supports operators)
                    Examples: {"code": "000001.SZ", "timestamp__gte": "2023-01-01"}
                    source 字段筛选运行模式（使用 SOURCE_TYPES 枚举的 value）：
                    {"source": SOURCE_TYPES.BACKTEST.value}     # 回测数据
                    {"source": SOURCE_TYPES.PAPER_REPLAY.value}  # 历史模拟数据
                    {"source": SOURCE_TYPES.PAPER_LIVE.value}    # 实盘模拟数据
            page: Page number (0-based)
            page_size: Number of items per page
            order_by: Field name to order by
            desc_order: Whether to use descending order
            distinct_field: Field name for DISTINCT query (returns unique values of this field)
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            ModelList[T] - 支持to_dataframe()和to_entities()方法
        """
        try:
            # Execute query using existing _do_find method
            raw_results = self._do_find(
                filters, page, page_size, order_by, desc_order, distinct_field, session
            )

            # Ensure we always return a list
            if isinstance(raw_results, list):
                models = raw_results
            else:
                models = [raw_results] if raw_results else []

            # Return ModelList with conversion capabilities
            return ModelList(models, self)

        except Exception as e:
            GLOG.ERROR(f"Failed to find {self.model_class.__name__} items: {e}")
            return ModelList([], self)

    def remove(self, filters: Dict[str, Any], session: Optional[Session] = None) -> None:
        """
        Template method: Remove items by filters.
        Subclasses should override _do_remove() instead.

        Args:
            filters: Dictionary of field -> value filters for deletion
            session: Optional SQLAlchemy session to use for the operation.
        """
        if not filters:
            GLOG.ERROR("Remove operation requires filters for safety")
            return

        try:
            return self._do_remove(filters, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to remove {self.model_class.__name__} items: {e}")
            raise

    @time_logger
    def modify(self, filters: Dict[str, Any], updates: Dict[str, Any], session: Optional[Session] = None) -> None:
        """
        Template method: Update items by filters.
        Subclasses should override _do_modify() instead.

        Args:
            filters: Dictionary of field -> value filters for selection
            updates: Dictionary of field -> value updates to apply
            session: Optional SQLAlchemy session to use for the operation.
        """
        if not filters or not updates:
            GLOG.ERROR("Modify operation requires both filters and updates")
            return

        if self._is_clickhouse:
            GLOG.ERROR("ClickHouse doesn't support UPDATE operations")
            return

        try:
            return self._do_modify(filters, updates, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to modify {self.model_class.__name__} items: {e}")
            raise

    def replace(self, filters: Dict[str, Any], new_items: List[T], session: Optional[Session] = None) -> ModelList:
        """
        Template method: Atomically replace items with new ones.

        Universal implementation for both ClickHouse and MySQL:
        1. Type validation for new items
        2. Query existing items that match filters
        3. If no existing items found, return empty result (no insertion)
        4. Delete existing items
        5. Insert new items
        6. Restore backup if insertion fails

        Args:
            filters: Dictionary of field -> value filters for items to replace
            new_items: List of new items to replace the filtered ones
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            ModelList of inserted items with their database identifiers
            Returns empty ModelList if no existing items match filters

        Raises:
            Exception: If the operation fails and restoration fails
        """
        if not filters:
            raise ValueError("Filters cannot be empty for replace operation")

        if not new_items:
            GLOG.WARN(f"No new items provided for {self.model_class.__name__} replace operation")
            return ModelList([], self)

        # Type validation: ensure all new_items are correct model type
        for item in new_items:
            if not isinstance(item, self.model_class):
                raise TypeError(
                    f"Item type mismatch: expected {self.model_class.__name__}, "
                    f"got {type(item).__name__}"
                )

        # Step 1: Query existing items
        backup_items = []
        try:
            existing_items = self.find(filters=filters, session=session)
            backup_items = list(existing_items)

            if len(backup_items) == 0:
                GLOG.INFO(
                    f"No existing {self.model_class.__name__} items found matching filters. "
                    f"No replacement performed."
                )
                # Return empty result without performing any insertion
                return ModelList([], self)

            GLOG.DEBUG(f"Found {len(backup_items)} existing {self.model_class.__name__} items to replace")

        except Exception as e:
            GLOG.ERROR(f"Failed to query existing {self.model_class.__name__} items: {e}")
            raise

        # Step 2: Delete existing items
        try:
            removed_count = self.remove(filters=filters, session=session)
            GLOG.DEBUG(f"Deleted {removed_count} existing {self.model_class.__name__} items")
        except Exception as e:
            GLOG.ERROR(f"Failed to delete {self.model_class.__name__} items: {e}")
            raise

        # Step 3: Insert new items
        try:
            inserted_items = self.add_batch(new_items, session=session)
            GLOG.INFO(
                f"Successfully replaced {len(backup_items)} with {len(new_items)} "
                f"{self.model_class.__name__} items"
            )
            return inserted_items
        except Exception as e:
            GLOG.ERROR(f"Failed to insert new {self.model_class.__name__} items, attempting restoration: {e}")

            # Step 4: Restore from backup if insertion fails
            try:
                if backup_items:
                    self.add_batch(backup_items, session=session)
                    GLOG.INFO(f"Successfully restored {len(backup_items)} backed up {self.model_class.__name__} items")
            except Exception as restore_error:
                GLOG.CRITICAL(
                    f"CRITICAL: Failed to restore {self.model_class.__name__} backup! "
                    f"Original error: {e}, Restore error: {restore_error}"
                )
                raise Exception(f"Replace operation failed and restoration failed: {restore_error}")

            raise Exception(f"Replace operation failed: {e}")

    def count(self, filters: Optional[Dict[str, Any]] = None, session: Optional[Session] = None) -> int:
        """
        Template method: Count items with optional filters.
        Subclasses should override _do_count() instead.

        Args:
            filters: Optional dictionary of field -> value filters
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            Number of matching records
        """
        try:
            return self._do_count(filters, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to count {self.model_class.__name__} items: {e}")
            return 0

    def exists(self, filters: Optional[Dict[str, Any]] = None, session: Optional[Session] = None) -> bool:
        """
        Template method: Check if items exist with optional filters.
        Subclasses should override _do_exists() instead.

        Args:
            filters: Optional dictionary of field -> value filters
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            True if at least one matching record exists, False otherwise
        """
        try:
            return self._do_exists(filters, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to check if {self.model_class.__name__} items exist: {e}")
            return False

    def soft_remove(self, filters: Dict[str, Any], session: Optional[Session] = None) -> None:
        """
        Template method: Soft remove items by filters.
        For MySQL: Sets is_del=True
        For ClickHouse: Calls remove() directly
        Subclasses should override _do_soft_remove() instead.

        Args:
            filters: Dictionary of field -> value filters for soft removal
            session: Optional SQLAlchemy session to use for the operation.
        """
        if not filters:
            GLOG.ERROR("Soft remove operation requires filters for safety")
            return

        try:
            return self._do_soft_remove(filters, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to soft remove {self.model_class.__name__} items: {e}")
            raise

    # ============================================================================
    # Hook Methods - Subclasses can override these without worrying about decorators
    # ============================================================================

    def _do_add(self, item: T, session: Optional[Session] = None) -> T:
        """
        Hook method: Override to customize single item addition logic.
        """
        # 🎯 Validate enum fields before adding to database
        validated_item = self._validate_item_enum_fields(item)

        if session:
            result = add(validated_item, session=session)
        else:
            conn = self._get_connection()
            with conn.get_session() as s:
                result = add(validated_item, session=s)
        GLOG.DEBUG(f"Added {self.model_class.__name__} item successfully")
        return result

    def _do_add_batch(self, items: List[Any], session: Optional[Session] = None) -> tuple[int, int]:
        """
        Hook method: Override to customize batch addition logic.
        """
        converted_items = self._convert_input_batch(items)

        if session:
            result = add_all(converted_items, session=session)
        else:
            conn = self._get_connection()
            with conn.get_session() as s:
                result = add_all(converted_items, session=s)

        GLOG.DEBUG(f"Added {len(converted_items)} {self.model_class.__name__} items in batch")
        return result

    def _do_find(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[str] = None,
        desc_order: bool = False,
        distinct_field: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Union[List[Any], pd.DataFrame]:
        """
        Hook method: Override to customize find logic.
        """
        if session is None:
            conn = self._get_connection()
            session_context = conn.get_session()
        else:
            session_context = session

        with session_context as s:
            # Handle DISTINCT query for specific field
            if distinct_field and hasattr(self.model_class, distinct_field):
                from sqlalchemy import distinct

                field_attr = getattr(self.model_class, distinct_field)
                query = s.query(distinct(field_attr))

                # Apply enhanced filters (supports operators)
                if filters:
                    filter_conditions = self._parse_filters(filters)
                    if filter_conditions:
                        query = query.filter(and_(*filter_conditions))

                # Apply ordering for DISTINCT field
                if order_by and order_by == distinct_field:
                    if desc_order:
                        query = query.order_by(field_attr.desc())
                    else:
                        query = query.order_by(field_attr)

                # Apply pagination
                if page_size is not None:
                    if page is not None:
                        query = query.offset(page * page_size).limit(page_size)
                    else:
                        query = query.limit(page_size)  # 默认从第0页开始

                # Execute DISTINCT query
                results = query.all()
                distinct_values = [row[0] for row in results]

                # Clean ClickHouse FixedString null bytes for string fields
                if self._is_clickhouse and distinct_field in self.CLICKHOUSE_STRING_FIELDS:
                    distinct_values = self._clean_clickhouse_strings(distinct_values)

                GLOG.DEBUG(f"Found {len(distinct_values)} distinct {distinct_field} values")
                return distinct_values

            # Regular query (not DISTINCT)
            query = s.query(self.model_class)

            # Apply enhanced filters (supports operators)
            if filters:
                filter_conditions = self._parse_filters(filters)
                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))

            # Apply ordering
            if order_by and hasattr(self.model_class, order_by):
                order_field = getattr(self.model_class, order_by)
                if desc_order:
                    query = query.order_by(order_field.desc())
                else:
                    query = query.order_by(order_field)

            # Apply pagination
            if page_size is not None:
                if page is not None:
                    query = query.offset(page * page_size).limit(page_size)
                else:
                    query = query.limit(page_size)  # 默认从第0页开始

            results = query.all()
            GLOG.DEBUG(f"Found {len(results)} {self.model_class.__name__} records")

            # Detach objects from session with performance consideration
            if len(results) > 100:  # Large dataset: use batch expunge for performance
                s.expunge_all()
            else:  # Small dataset: use precise expunge for safety
                for obj in results:
                    s.expunge(obj)

            return self._convert_output_items(results)

    def _do_remove(self, filters: Dict[str, Any], session: Optional[Session] = None) -> None:
        """
        Hook method: Override to customize remove logic.
        """
        if session is None:
            conn = self._get_connection()
            session_context = conn.get_session()
        else:
            session_context = session

        with session_context as s:
            if self._is_clickhouse:
                # ClickHouse requires native SQL for DELETE operations
                from ginkgo.enums import EnumBase  # Import for enum conversion
                sql_parts = []
                params = {}

                for key, value in filters.items():
                    # Convert enum objects to integers for ClickHouse compatibility
                    if isinstance(value, EnumBase):
                        value = value.value
                    elif isinstance(value, list):
                        value = [item.value if isinstance(item, EnumBase) else item for item in value]

                    if "__" in key:
                        field, operator = key.split("__", 1)
                        if hasattr(self.model_class, field):
                            param_name = f"param_{field}_{operator}"
                            if operator == "gte":
                                sql_parts.append(f"{field} >= :{param_name}")
                            elif operator == "lte":
                                sql_parts.append(f"{field} <= :{param_name}")
                            elif operator == "gt":
                                sql_parts.append(f"{field} > :{param_name}")
                            elif operator == "lt":
                                sql_parts.append(f"{field} < :{param_name}")
                            elif operator == "in":
                                # Handle IN operator specially
                                placeholders = [f":param_{field}_in_{i}" for i in range(len(value))]
                                sql_parts.append(f"{field} IN ({','.join(placeholders)})")
                                for i, val in enumerate(value):
                                    params[f"param_{field}_in_{i}"] = val
                                continue
                            elif operator == "like":
                                sql_parts.append(f"{field} LIKE :{param_name}")
                            params[param_name] = value
                    else:
                        # Standard equality filter
                        if hasattr(self.model_class, key):
                            param_name = f"param_{key}"
                            sql_parts.append(f"{key} = :{param_name}")
                            params[param_name] = value

                if sql_parts:
                    s.execute(
                        text(f"DELETE FROM {self.model_class.__tablename__} WHERE {' AND '.join(sql_parts)}"), params
                    )
                    GLOG.DEBUG(f"Deleted {self.model_class.__name__} records from ClickHouse")
            else:
                # MySQL can use SQLAlchemy ORM with enhanced filters
                filter_conditions = self._parse_filters(filters)
                if filter_conditions:
                    stmt = delete(self.model_class).where(and_(*filter_conditions))
                    result = s.execute(stmt)
                    deleted_rows = result.rowcount if result else 0
                    GLOG.DEBUG(f"Deleted {deleted_rows} {self.model_class.__name__} records from MySQL")
                    return deleted_rows
                else:
                    GLOG.DEBUG(f"No filter conditions provided for MySQL delete operation")
                    return 0
            s.commit()

    def _do_modify(self, filters: Dict[str, Any], updates: Dict[str, Any], session: Optional[Session] = None) -> int:
        """
        Hook method: Override to customize modify logic.

        Returns:
            int: Number of records updated
        """
        if session is None:
            conn = self._get_connection()
            session_context = conn.get_session()
        else:
            session_context = session

        with session_context as s:
            # Build filter conditions
            filter_conditions = []
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    filter_conditions.append(getattr(self.model_class, field) == value)

            # Automatically update update_at timestamp for MySQL models
            if self._is_mysql and hasattr(self.model_class, "update_at"):
                import datetime

                updates = updates.copy()  # Don't modify original dict
                updates["update_at"] = datetime.datetime.now()

            # Execute update
            if filter_conditions:
                stmt = update(self.model_class).where(and_(*filter_conditions)).values(updates)
                result = s.execute(stmt)
                updated_rows = result.rowcount if result else 0
                print(f"Updated {self.model_class.__name__} records: {updated_rows}")
                return updated_rows
            return 0

    def _do_count(self, filters: Optional[Dict[str, Any]] = None, session: Optional[Session] = None) -> int:
        """
        Hook method: Override to customize count logic.
        """
        if session is None:
            conn = self._get_connection()
            session_context = conn.get_session()
        else:
            session_context = session

        with session_context as s:
            query = s.query(self.model_class)

            if filters:
                filter_conditions = self._parse_filters(filters)
                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))

            count = query.count()
            GLOG.DEBUG(f"Counted {count} {self.model_class.__name__} records")
            return count

    def _do_exists(self, filters: Optional[Dict[str, Any]] = None, session: Optional[Session] = None) -> bool:
        """
        Hook method: Override to customize exists logic.
        """
        if session is None:
            conn = self._get_connection()
            session_context = conn.get_session()
        else:
            session_context = session

        with session_context as s:
            query = s.query(self.model_class)

            if filters:
                filter_conditions = self._parse_filters(filters)
                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))

            # Use exists() for better performance than count()
            exists = s.query(query.exists()).scalar()
            GLOG.DEBUG(f"Checked existence of {self.model_class.__name__} records: {exists}")
            # Explicitly convert to bool (ClickHouse may return 1/0 instead of True/False)
            return bool(exists)

    def _do_soft_remove(self, filters: Dict[str, Any], session: Optional[Session] = None) -> None:
        """
        Hook method: Override to customize soft remove logic.
        """
        if self._is_clickhouse:
            # ClickHouse: soft remove = hard remove
            GLOG.DEBUG(f"ClickHouse soft remove: calling remove() for {self.model_class.__name__}")
            self._do_remove(filters, session)  # Pass session to _do_remove
        else:
            # MySQL: set is_del=True and update_at
            import datetime

            updates = {"is_del": True, "update_at": datetime.datetime.now()}
            GLOG.DEBUG(f"MySQL soft remove: setting is_del=True and updating timestamp for {self.model_class.__name__}")
            self._do_modify(filters, updates, session)  # Pass session to _do_modify

    def _parse_filters(self, filters: Dict[str, Any]) -> List[Any]:
        """
        Parse enhanced filters with operator support.
        Supports operators: gte, lte, gt, lt, in, like, and __or__ combinator.
        Uses _get_enum_mappings() for precise enum-to-integer conversion.

        Args:
            filters: Dictionary with field__operator keys
                   Examples: {"timestamp__gte": "2023-01-01", "volume__in": [100, 200]}
                   OR combinator: {"__or__": [{"code__like": "x"}, {"name__like": "x"}]}

        Returns:
            List of SQLAlchemy filter conditions
        """
        # 🎯 First, convert enum values based on mappings for precise handling
        converted_filters = self._convert_enum_values(filters)

        conditions = []

        for key, value in converted_filters.items():
            # __or__ combinator: each sub-dict is parsed recursively, combined with or_()
            if key == "__or__":
                from sqlalchemy import or_
                or_conditions = []
                for sub_filters in value:
                    or_conditions.extend(self._parse_filters(sub_filters))
                if or_conditions:
                    conditions.append(or_(*or_conditions))
            elif "__" in key:
                field, operator = key.split("__", 1)
                if hasattr(self.model_class, field):
                    attr = getattr(self.model_class, field)
                    if operator == "gte":
                        conditions.append(attr >= value)
                    elif operator == "lte":
                        conditions.append(attr <= value)
                    elif operator == "gt":
                        conditions.append(attr > value)
                    elif operator == "lt":
                        conditions.append(attr < value)
                    elif operator == "in":
                        conditions.append(attr.in_(value))
                    elif operator == "like":
                        conditions.append(attr.like(f"%{value}%"))
                    else:
                        from ginkgo.libs import GLOG
                        GLOG.DEBUG(f"Unknown filter operator: {operator}")
            else:
                # Standard equality filter
                if hasattr(self.model_class, key):
                    conditions.append(getattr(self.model_class, key) == value)

        return conditions


class BaseCRUD(_CoreCRUD, _Conversion, _Validation, _Streaming, Generic[T], ABC):
    """CRUD 基类。

    将 _CoreCRUD、_Conversion、_Validation、_Streaming 通过多重继承组合。
    这是为了文件组织的拆分，不是 Mixin 模式——各部分不可独立使用。

    子类继承此类即可获得全部功能，38 个现有子类零改动。
    """
    pass
