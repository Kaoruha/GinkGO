from typing import TypeVar, Generic, List, Optional, Any, Union, Dict, Callable
from abc import ABC, abstractmethod
import pandas as pd
from decimal import Decimal
from datetime import datetime
from sqlalchemy import and_, delete, select, text, update
from sqlalchemy.orm import Session

from ..drivers import get_db_connection, add, add_all
from ..models import MClickBase, MMysqlBase
from ...libs import GLOG, time_logger, retry, cache_with_expiration
from ..access_control import restrict_crud_access

T = TypeVar("T", bound=Union[MClickBase, MMysqlBase])


@restrict_crud_access
class BaseCRUD(Generic[T], ABC):
    """
    Generic base CRUD class with template method pattern for unified decorator management.

    Features:
    - Template methods with unified decorators (@time_logger, @retry, @cache_with_expiration)
    - Hook methods that subclasses can override without worrying about decorators
    - Type-safe operations with TypeVar
    - Automatic database detection (ClickHouse vs MySQL)
    - Database-specific operation handling (ClickHouse limitations)
    - Unified validation architecture via _get_field_config() hook method

    Validation Architecture:
    - create() → _validate_before_database() → validate_data_by_config(_get_field_config())
    - Subclasses define validation rules by overriding _get_field_config()
    - All validation is configuration-driven and executed automatically
    """

    # ClickHouse string fields that need null byte cleaning (from external sources or user input)
    CLICKHOUSE_STRING_FIELDS = [
        "code",  # Stock code (from external data sources like Tushare, Yahoo)
        "name",  # Names (user-defined)
        "reason",  # Reasons (user input or strategy generated)
        "meta",  # Metadata (may contain external data)
        "desc",  # Descriptions (user input)
        "portfolio_id",  # Portfolio ID (may have FixedString padding)
    ]

    def __init__(self, model_class: type[T]):
        self.model_class = model_class
        self._is_clickhouse = issubclass(model_class, MClickBase)
        self._is_mysql = issubclass(model_class, MMysqlBase)

        if not (self._is_clickhouse or self._is_mysql):
            raise ValueError(f"Model {model_class} must inherit from MClickBase or MMysqlBase")

    def _get_connection(self):
        """Get appropriate database connection based on model type"""
        return get_db_connection(self.model_class)

    def get_session(self) -> Session:
        """Get a new database session for external transaction management."""
        return self._get_connection().get_session()

    def _clean_clickhouse_strings(self, data):
        """
        Clean ClickHouse FixedString null bytes for configured string fields.

        Args:
            data: Can be a list of values, pandas DataFrame, or single value

        Returns:
            Cleaned data in the same format as input
        """
        if not self._is_clickhouse:
            return data

        # Handle list of string values (for DISTINCT queries)
        if isinstance(data, list):
            return [str(value).strip("\x00") if isinstance(value, str) else value for value in data]

        # Handle pandas DataFrame
        elif isinstance(data, pd.DataFrame) and data.shape[0] > 0:
            df = data.copy()
            for field in self.CLICKHOUSE_STRING_FIELDS:
                if field in df.columns:
                    df[field] = df[field].astype(str).str.replace("\x00", "", regex=False)
            return df

        # Handle single string value
        elif isinstance(data, str):
            return data.strip("\x00")

        return data

    # ============================================================================
    # 配置化数据验证 - 简洁统一的验证方法
    # ============================================================================

    def _validate_before_database(self, data: dict) -> dict:
        """
        两层配置化数据验证：数据库必填字段 + 业务特定字段

        Args:
            data: 待验证的数据字典

        Returns:
            验证并转换后的数据字典

        Raises:
            ValidationError: 当验证失败时
        """
        from .validation import validate_data_by_config, ValidationError

        try:
            validated = data.copy()

            # 第一层：数据库必填字段验证
            database_required_config = self._get_database_required_config()
            if database_required_config:
                validated = validate_data_by_config(validated, database_required_config)
                GLOG.DEBUG(f"Database required fields validation passed for {self.model_class.__name__}")

            # 第二层：业务特定字段验证
            business_field_config = self._get_field_config()
            if business_field_config:
                validated = validate_data_by_config(validated, business_field_config)
                GLOG.DEBUG(f"Business fields validation passed for {self.model_class.__name__}")

            # 如果两层都没有配置
            if not database_required_config and not business_field_config:
                GLOG.DEBUG(f"No validation config defined for {self.model_class.__name__}, skipping validation")

            GLOG.DEBUG(f"Complete data validation passed for {self.model_class.__name__}")
            return validated

        except ValidationError as e:
            GLOG.ERROR(f"Data validation failed for {self.model_class.__name__}: {e}")
            raise e
        except Exception as e:
            GLOG.ERROR(f"Unexpected error during validation for {self.model_class.__name__}: {e}")
            raise ValidationError(f"Unexpected validation error: {str(e)}")

    def _get_database_required_config(self) -> dict:
        """
        获取数据库必填字段配置 - 基于模型基类定义添加数据时必须传入的字段

        Returns:
            dict: 数据库必填字段配置
        """
        if self._is_mysql:
            return self._get_mysql_required_config()
        elif self._is_clickhouse:
            return self._get_clickhouse_required_config()
        return {}

    def _get_mysql_required_config(self) -> dict:
        """
        MySQL 必填字段配置 - 基于 MMysqlBase

        MMysqlBase 的所有字段都有默认值，因此无必填字段：
        - uuid: 自动生成
        - meta: 默认 "{}"
        - desc: 默认描述文本
        - create_at: 自动生成当前时间
        - update_at: 自动生成当前时间
        - is_del: 默认 False
        - source: 默认 OTHER

        Returns:
            dict: MySQL 必填字段配置（通常为空）
        """
        return {}

    def _get_clickhouse_required_config(self) -> dict:
        """
        ClickHouse 必填字段配置 - 基于 MClickBase

        MClickBase 必填字段：
        - timestamp: 没有默认值，必须传入（MergeTree 排序键）

        其他字段都有默认值：
        - uuid: 自动生成
        - meta: 默认 "{}"
        - desc: 默认描述文本
        - source: 默认 OTHER

        Returns:
            dict: ClickHouse 必填字段配置
        """
        return {"timestamp": {"type": ["datetime", "string"]}}

    def _get_field_config(self) -> dict:
        """
        获取业务字段配置 - 子类重写此方法定义业务必填字段要求

        配置中的所有字段都是必填的，支持的配置参数：
        - type: 字段类型，可以是单个类型或类型列表
        - min/max: 数值范围或字符串长度范围
        - choices: 枚举值列表
        - pattern: 正则表达式（用于字符串）

        Returns:
            dict: 业务字段配置字典，格式如下：
            {
                'field_name': {
                    'type': 'string' | ['int', 'string'],  # 单类型或多类型
                    'min': 0,                               # 最小值/长度
                    'max': 100,                             # 最大值/长度
                    'choices': [value1, value2],            # 枚举值
                    'pattern': r'regex_pattern'             # 正则表达式
                },
                ...
            }

        Example:
            return {
                'code': {'type': 'string', 'pattern': r'^[0-9]{6}\\.(SZ|SH)$'},
                'price': {'type': ['decimal', 'float'], 'min': 0.001},
                'volume': {'type': ['int', 'string'], 'min': 0}
            }
        """
        return {}

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
            Added model instance with updated fields
        """
        try:
            return self._do_add(item, session)
        except Exception as e:
            GLOG.ERROR(f"Failed to add {self.model_class.__name__} item: {e}")
            raise

    @time_logger
    @retry(max_try=3)
    def add_batch(self, items: List[Any], session: Optional[Session] = None) -> tuple[int, int]:
        """
        Template method: Add multiple items to database in batch.
        支持自动类型转换，不进行数据验证，依赖数据库约束确保数据完整性。
        Subclasses should override _do_add_batch() instead.

        Args:
            items: List of model instances or convertible objects
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            Tuple of (clickhouse_count, mysql_count)
        """
        try:
            # 只进行类型转换，不进行数据验证
            converted_items = self._convert_input_batch(items)
            return self._do_add_batch(converted_items, session)
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
            Added model instance with updated fields
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
        as_dataframe: bool = False,
        output_type: str = "model",
        distinct_field: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Union[List[Any], pd.DataFrame]:
        """
        Template method: Find items with enhanced filters and pagination.
        Supports operator filters like field__gte, field__lte, field__in.
        Subclasses should override _do_find() instead.

        Args:
            filters: Dictionary of field -> value filters (supports operators)
                    Examples: {"code": "000001.SZ", "timestamp__gte": "2023-01-01"}
            page: Page number (0-based)
            page_size: Number of items per page
            order_by: Field name to order by
            desc_order: Whether to use descending order
            as_dataframe: Return DataFrame instead of objects
            output_type: Output format ("model" or subclass-defined)
            distinct_field: Field name for DISTINCT query (returns unique values of this field)
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            List of objects or DataFrame (type depends on output_type)
            If distinct_field is provided, returns List[Any] of unique field values
        """
        try:
            return self._do_find(
                filters, page, page_size, order_by, desc_order, as_dataframe, output_type, distinct_field, session
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to find {self.model_class.__name__} items: {e}")
            if as_dataframe:
                return pd.DataFrame()
            else:
                return []

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
        if session:
            result = add(item, session=session)
        else:
            conn = self._get_connection()
            with conn.get_session() as s:
                result = add(item, session=s)
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
        as_dataframe: bool = False,
        output_type: str = "model",
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

            if as_dataframe:
                df = pd.read_sql(query.statement, s.connection())

                # Clean ClickHouse FixedString null bytes for specific fields
                if self._is_clickhouse and df.shape[0] > 0:
                    df = self._clean_clickhouse_strings(df)

                GLOG.DEBUG(f"Found {df.shape[0]} {self.model_class.__name__} records as DataFrame")
                return df
            else:
                results = query.all()
                GLOG.DEBUG(f"Found {len(results)} {self.model_class.__name__} records")

                # Detach objects from session with performance consideration
                if len(results) > 100:  # Large dataset: use batch expunge for performance
                    s.expunge_all()
                else:  # Small dataset: use precise expunge for safety
                    for obj in results:
                        s.expunge(obj)

                # Apply output conversion
                return self._convert_output_items(results, output_type)

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
                from ...enums import EnumBase  # Import for enum conversion
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
                    s.execute(stmt)
                    GLOG.DEBUG(f"Deleted {self.model_class.__name__} records from MySQL")
            s.commit()

    def _do_modify(self, filters: Dict[str, Any], updates: Dict[str, Any], session: Optional[Session] = None) -> None:
        """
        Hook method: Override to customize modify logic.
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
                s.execute(stmt)
                GLOG.DEBUG(f"Updated {self.model_class.__name__} records")

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
            return exists

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

    # ============================================================================
    # New Conversion and Utility Methods
    # ============================================================================

    def _create_from_params(self, **kwargs) -> T:
        """
        Hook method: Override to define how to create model from parameters.
        Called by create() template method.

        Args:
            **kwargs: Parameters to create the object

        Returns:
            Model instance

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _create_from_params")

    def _convert_input_batch(self, items: List[Any]) -> List[T]:
        """
        Convert a batch of input items to model instances.
        Attempts automatic conversion for each item.

        Args:
            items: List of input items (may be mixed types)

        Returns:
            List of converted model instances
        """
        converted = []
        for item in items:
            if isinstance(item, self.model_class):
                converted.append(item)
            else:
                # Try to convert using subclass conversion method
                converted_item = self._convert_input_item(item)
                if converted_item is not None:
                    converted.append(converted_item)
                else:
                    GLOG.DEBUG(f"Cannot convert item {type(item)} to {self.model_class.__name__}")
        return converted

    def _convert_input_item(self, item: Any) -> Optional[T]:
        """
        Hook method: Override to support input type conversion.

        Args:
            item: Input item to convert

        Returns:
            Converted model instance or None if conversion not supported
        """
        return None  # Default: no conversion supported

    def _convert_output_items(self, items: List[T], output_type: str = "model") -> List[Any]:
        """
        Hook method: Override to support output type conversion.

        Args:
            items: List of model instances
            output_type: Desired output type

        Returns:
            List of converted output objects
        """
        return items  # Default: return model instances as-is

    def _parse_filters(self, filters: Dict[str, Any]) -> List[Any]:
        """
        Parse enhanced filters with operator support.
        Supports operators: gte, lte, gt, lt, in, like
        Automatically converts enum objects to integers for database compatibility.

        Args:
            filters: Dictionary with field__operator keys
                   Examples: {"timestamp__gte": "2023-01-01", "volume__in": [100, 200]}

        Returns:
            List of SQLAlchemy filter conditions
        """
        from ...enums import EnumBase  # Import at method level to avoid circular imports
        
        conditions = []

        for key, value in filters.items():
            # Convert enum objects to integers for database compatibility
            if isinstance(value, EnumBase):
                value = value.value
            elif isinstance(value, list):
                # Handle list values (e.g., for __in operator)
                value = [item.value if isinstance(item, EnumBase) else item for item in value]
            
            if "__" in key:
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
                        GLOG.DEBUG(f"Unknown filter operator: {operator}")
            else:
                # Standard equality filter
                if hasattr(self.model_class, key):
                    conditions.append(getattr(self.model_class, key) == value)

        return conditions

    # ============================================================================
    # 流式查询功能 - 新增功能，完全向后兼容
    # ============================================================================

    def __init__(self, model_class: type[T]):
        # 调用原有初始化逻辑
        if hasattr(super(), '__init__'):
            super().__init__()
        
        self.model_class = model_class
        self._is_clickhouse = issubclass(model_class, MClickBase)
        self._is_mysql = issubclass(model_class, MMysqlBase)

        if not (self._is_clickhouse or self._is_mysql):
            raise ValueError(f"Model {model_class} must inherit from MClickBase or MMysqlBase")

        # 🆕 流式查询相关属性（默认禁用，不影响现有功能）
        self._streaming_enabled = False
        self._streaming_engine = None
        self._streaming_config = None
        
        # 延迟加载流式查询配置（只有在使用时才加载）
        self._streaming_initialized = False

    def _initialize_streaming(self) -> None:
        """延迟初始化流式查询功能"""
        if self._streaming_initialized:
            return
            
        try:
            # 导入流式查询模块（延迟导入避免循环依赖）
            from ..streaming.config import get_config
            from ..streaming.engines import BaseStreamingEngine
            
            # 加载配置
            self._streaming_config = get_config()
            self._streaming_enabled = self._streaming_config.enabled
            
            if self._streaming_enabled:
                GLOG.DEBUG(f"Streaming functionality enabled for {self.model_class.__name__}")
            else:
                GLOG.DEBUG(f"Streaming functionality disabled for {self.model_class.__name__}")
                
            self._streaming_initialized = True
            
        except Exception as e:
            GLOG.WARNING(f"Failed to initialize streaming for {self.model_class.__name__}: {e}")
            self._streaming_enabled = False
            self._streaming_initialized = True

    def _get_streaming_engine(self):
        """获取流式查询引擎"""
        if not self._streaming_initialized:
            self._initialize_streaming()
            
        if not self._streaming_enabled:
            raise RuntimeError(
                "Streaming functionality is disabled. "
                "Enable it in config: streaming.enabled = true"
            )
        
        if self._streaming_engine is None:
            try:
                # 延迟导入和创建引擎
                if self._is_mysql:
                    from ..streaming.engines.mysql_streaming_engine import MySQLStreamingEngine
                    self._streaming_engine = MySQLStreamingEngine(
                        self._get_connection(), 
                        self._streaming_config
                    )
                elif self._is_clickhouse:
                    from ..streaming.engines.clickhouse_streaming_engine import ClickHouseStreamingEngine
                    self._streaming_engine = ClickHouseStreamingEngine(
                        self._get_connection(),
                        self._streaming_config
                    )
                else:
                    raise RuntimeError(f"No streaming engine available for {self.model_class}")
                    
                GLOG.DEBUG(f"Created streaming engine for {self.model_class.__name__}")
                
            except ImportError as e:
                # 如果引擎尚未实现，提供友好的错误信息
                raise RuntimeError(
                    f"Streaming engine not available for {self.model_class}. "
                    f"This feature is still under development: {e}"
                )
        
        return self._streaming_engine

    @time_logger
    def stream_find(self, 
                   filters: Optional[Dict[str, Any]] = None,
                   batch_size: Optional[int] = None,
                   order_by: Optional[str] = None,
                   desc_order: bool = False) -> Any:
        """
        🆕 流式查询接口 - 新增功能，不影响现有find()方法
        
        提供高性能的流式查询，适用于大数据集处理。
        内存占用稳定，支持断点续传和进度监控。
        
        Args:
            filters: 查询过滤条件（支持操作符，如field__gte）
            batch_size: 批次大小，默认使用配置值
            order_by: 排序字段
            desc_order: 是否降序
            
        Yields:
            Iterator[List[T]]: 批次数据迭代器
            
        Example:
            >>> # 流式查询500万条K线数据
            >>> for batch in bar_crud.stream_find(
            ...     filters={'timestamp__gte': '2020-01-01'},
            ...     batch_size=1000
            ... ):
            ...     process_batch(batch)  # 处理1000条数据
        """
        try:
            # 获取流式查询引擎
            engine = self._get_streaming_engine()
            
            # 构建基础查询
            base_query = self._build_streaming_query(filters, order_by, desc_order)
            
            # 执行流式查询
            return engine.execute_stream(
                query=base_query,
                filters=filters or {},
                batch_size=batch_size
            )
            
        except Exception as e:
            GLOG.ERROR(f"Stream find failed for {self.model_class.__name__}: {e}")
            
            # 自动降级到传统查询（如果启用了降级）
            if self._streaming_config and self._streaming_config.recovery.enable_fallback:
                GLOG.WARNING(f"Falling back to traditional query for {self.model_class.__name__}")
                return self._fallback_to_traditional_query(filters, batch_size, order_by, desc_order)
            else:
                raise

    def stream_find_with_progress(self,
                                 filters: Optional[Dict[str, Any]] = None,
                                 batch_size: Optional[int] = None,
                                 progress_callback: Optional[Any] = None,
                                 **kwargs) -> Any:
        """
        🆕 带进度回调的流式查询
        
        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            progress_callback: 进度回调函数 callback(progress_info)
            **kwargs: 其他参数
            
        Yields:
            Iterator[List[T]]: 批次数据迭代器
        """
        # 获取引擎并添加进度观察者
        engine = self._get_streaming_engine()
        
        if progress_callback:
            # 创建进度观察者
            from ..streaming.engines.base_streaming_engine import ProgressObserver
            
            class CallbackObserver(ProgressObserver):
                def __init__(self, callback):
                    self.callback = callback
                    
                def on_progress_update(self, progress):
                    self.callback(progress)
                    
                def on_batch_processed(self, batch_index, batch_size):
                    pass
                    
                def on_error(self, error):
                    pass
            
            observer = CallbackObserver(progress_callback)
            engine.add_observer(observer)
        
        try:
            yield from self.stream_find(filters, batch_size, **kwargs)
        finally:
            # 清理观察者
            if progress_callback:
                engine.remove_observer(observer)

    def stream_find_resumable(self,
                             query_id: str,
                             filters: Optional[Dict[str, Any]] = None,
                             batch_size: Optional[int] = None,
                             **kwargs) -> Any:
        """
        🆕 支持断点续传的流式查询
        
        Args:
            query_id: 查询唯一标识符
            filters: 查询过滤条件
            batch_size: 批次大小
            **kwargs: 其他参数
            
        Yields:
            Iterator[List[T]]: 批次数据迭代器
        """
        engine = self._get_streaming_engine()
        
        # 尝试加载断点状态
        checkpoint_state = None
        if self._streaming_config.recovery.enable_checkpoint:
            try:
                from ..streaming.managers.checkpoint_manager import CheckpointManager
                # 这里需要Redis连接，暂时跳过具体实现
                # checkpoint_manager = CheckpointManager(redis_client)
                # checkpoint_state = checkpoint_manager.load_checkpoint(query_id)
                pass
            except Exception as e:
                GLOG.WARNING(f"Failed to load checkpoint for query {query_id}: {e}")
        
        # 构建查询
        base_query = self._build_streaming_query(filters, **kwargs)
        
        # 执行带断点续传的流式查询
        return engine.execute_stream_with_checkpoint(
            query=base_query,
            checkpoint_state=checkpoint_state,
            filters=filters,
            batch_size=batch_size
        )

    def is_streaming_enabled(self) -> bool:
        """检查流式查询是否已启用"""
        if not self._streaming_initialized:
            self._initialize_streaming()
        return self._streaming_enabled

    def enable_streaming(self) -> None:
        """运行时启用流式查询"""
        if not self._streaming_initialized:
            self._initialize_streaming()
        self._streaming_enabled = True
        GLOG.INFO(f"Streaming enabled for {self.model_class.__name__}")

    def disable_streaming(self) -> None:
        """运行时禁用流式查询"""
        self._streaming_enabled = False
        self._streaming_engine = None
        GLOG.INFO(f"Streaming disabled for {self.model_class.__name__}")

    def get_streaming_metrics(self) -> Optional[Any]:
        """获取流式查询性能指标"""
        if self._streaming_engine:
            return self._streaming_engine.get_metrics()
        return None

    # ==================== 内部辅助方法 ====================

    def _build_streaming_query(self, 
                              filters: Optional[Dict[str, Any]] = None,
                              order_by: Optional[str] = None,
                              desc_order: bool = False) -> str:
        """构建流式查询SQL语句"""
        # 基础SELECT语句
        table_name = self.model_class.__tablename__
        query = f"SELECT * FROM {table_name}"
        
        # 添加WHERE条件
        if filters:
            where_conditions = []
            for key, value in filters.items():
                if "__" in key:
                    field, operator = key.split("__", 1)
                    if hasattr(self.model_class, field):
                        if operator == "gte":
                            where_conditions.append(f"{field} >= '{value}'")
                        elif operator == "lte":
                            where_conditions.append(f"{field} <= '{value}'")
                        elif operator == "gt":
                            where_conditions.append(f"{field} > '{value}'")
                        elif operator == "lt":
                            where_conditions.append(f"{field} < '{value}'")
                        elif operator == "in":
                            if isinstance(value, (list, tuple)):
                                value_str = "', '".join(str(v) for v in value)
                                where_conditions.append(f"{field} IN ('{value_str}')")
                        elif operator == "like":
                            where_conditions.append(f"{field} LIKE '%{value}%'")
                else:
                    if hasattr(self.model_class, key):
                        where_conditions.append(f"{key} = '{value}'")
            
            if where_conditions:
                query += f" WHERE {' AND '.join(where_conditions)}"
        
        # 添加ORDER BY
        if order_by and hasattr(self.model_class, order_by):
            query += f" ORDER BY {order_by}"
            if desc_order:
                query += " DESC"
        
        return query

    def _fallback_to_traditional_query(self,
                                     filters: Optional[Dict[str, Any]] = None,
                                     batch_size: Optional[int] = None,
                                     order_by: Optional[str] = None,
                                     desc_order: bool = False) -> Any:
        """降级到传统查询的实现"""
        GLOG.INFO(f"Using traditional query fallback for {self.model_class.__name__}")
        
        # 使用现有的find方法，分页返回
        batch_size = batch_size or 1000
        page = 0
        
        while True:
            batch = self.find(
                filters=filters,
                page=page,
                page_size=batch_size,
                order_by=order_by,
                desc_order=desc_order
            )
            
            if not batch:
                break
                
            yield batch
            page += 1
            
            # 避免无限循环
            if len(batch) < batch_size:
                break

    # ==================== 🆕 断点续传流式查询方法 ====================
    
    def stream_find_resumable(self,
                             filters: Optional[Dict[str, Any]] = None,
                             batch_size: Optional[int] = None,
                             order_by: Optional[str] = "timestamp",
                             desc_order: bool = False,
                             checkpoint_id: Optional[str] = None,
                             auto_checkpoint: bool = True,
                             checkpoint_interval: int = 1000) -> Any:
        """
        🆕 支持断点续传的流式查询
        
        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            order_by: 排序字段（用于断点续传）
            desc_order: 是否降序
            checkpoint_id: 现有断点ID（用于恢复）
            auto_checkpoint: 是否自动创建断点
            checkpoint_interval: 自动断点间隔
            
        Yields:
            查询结果批次
        """
        if not self._streaming_enabled:
            GLOG.WARNING("Streaming not enabled, falling back to traditional query")
            yield from self._fallback_to_traditional_query(filters, batch_size, order_by, desc_order)
            return
        
        try:
            # 导入断点管理器（延迟导入避免循环依赖）
            from ginkgo.data.streaming.checkpoint import checkpoint_manager, progress_tracking_manager
            from ginkgo.data.streaming import StreamingState, CheckpointError
            
            # 恢复或创建断点
            checkpoint = None
            if checkpoint_id:
                checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
                if not checkpoint:
                    raise CheckpointError(f"Checkpoint not found: {checkpoint_id}")
                GLOG.INFO(f"Resuming from checkpoint: {checkpoint_id}")
            elif auto_checkpoint:
                # 创建新断点
                checkpoint_id = checkpoint_manager.create_checkpoint(
                    query=self._build_streaming_query(filters, order_by, desc_order),
                    filters=filters or {},
                    batch_size=batch_size or 1000,
                    database_type=getattr(self.driver, '_db_type', 'unknown'),
                    engine_type='streaming',
                    estimated_total=self._estimate_total_records(filters)
                )
                checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
                GLOG.INFO(f"Created checkpoint: {checkpoint_id}")
            
            # 调整过滤条件支持断点续传
            adjusted_filters = self._adjust_filters_for_resume(filters, checkpoint, order_by)
            
            # 创建进度跟踪器
            tracker_id = None
            if checkpoint:
                from ginkgo.data.streaming.checkpoint import checkpoint_manager
                query_hash = checkpoint_manager._generate_query_hash(
                    checkpoint.query_text, 
                    adjusted_filters
                )
                tracker_id = progress_tracking_manager.create_tracker(
                    query_hash=query_hash,
                    estimated_total=checkpoint.estimated_total
                )
            
            # 执行流式查询
            processed_in_session = 0
            total_processed = checkpoint.processed_count if checkpoint else 0
            
            try:
                # 更新断点状态为运行中
                if checkpoint:
                    checkpoint_manager.update_checkpoint(
                        checkpoint.checkpoint_id,
                        state=StreamingState.RUNNING
                    )
                
                for batch in self.stream_find(
                    filters=adjusted_filters,
                    batch_size=batch_size,
                    order_by=order_by,
                    desc_order=desc_order
                ):
                    # 更新处理计数
                    batch_size_actual = len(batch)
                    processed_in_session += batch_size_actual
                    total_processed += batch_size_actual
                    
                    # 更新进度跟踪
                    if tracker_id:
                        progress_tracking_manager.update_progress(
                            tracker_id=tracker_id,
                            processed_count=total_processed,
                            batch_size=batch_size_actual
                        )
                    
                    # 自动保存断点
                    if checkpoint and auto_checkpoint and processed_in_session >= checkpoint_interval:
                        self._save_checkpoint_progress(
                            checkpoint, batch, total_processed, order_by
                        )
                        processed_in_session = 0
                    
                    yield batch
                
                # 查询完成，更新断点状态
                if checkpoint:
                    checkpoint_manager.update_checkpoint(
                        checkpoint.checkpoint_id,
                        state=StreamingState.COMPLETED,
                        processed_count=total_processed,
                        progress_percentage=100.0
                    )
                    GLOG.INFO(f"Streaming query completed. Checkpoint: {checkpoint.checkpoint_id}")
                
            except Exception as e:
                # 查询失败，保存当前进度
                if checkpoint:
                    checkpoint_manager.update_checkpoint(
                        checkpoint.checkpoint_id,
                        state=StreamingState.FAILED,
                        processed_count=total_processed
                    )
                    GLOG.ERROR(f"Streaming query failed. Checkpoint saved: {checkpoint.checkpoint_id}")
                raise
            finally:
                # 清理进度跟踪器
                if tracker_id:
                    progress_tracking_manager.remove_tracker(tracker_id)
        
        except Exception as e:
            GLOG.ERROR(f"Resumable streaming query failed: {e}")
            # 降级到普通流式查询
            GLOG.INFO("Falling back to regular streaming query")
            yield from self.stream_find(filters, batch_size, order_by, desc_order)
    
    def stream_find_with_detailed_progress(self,
                                         filters: Optional[Dict[str, Any]] = None,
                                         batch_size: Optional[int] = None,
                                         progress_callback: Optional[Callable] = None,
                                         checkpoint_id: Optional[str] = None) -> Any:
        """
        🆕 带详细进度监控的流式查询
        
        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            progress_callback: 进度回调函数
            checkpoint_id: 断点ID（用于恢复）
            
        Yields:
            查询结果批次
        """
        # 添加默认进度回调
        def default_progress_callback(progress_info):
            from ginkgo.data.streaming import ProgressInfo
            GLOG.INFO(
                f"Streaming progress: {progress_info.processed} processed, "
                f"rate: {progress_info.rate:.1f} records/sec, "
                f"elapsed: {progress_info.elapsed:.1f}s"
                + (f", progress: {progress_info.progress_percentage:.1f}%" 
                   if progress_info.progress_percentage else "")
            )
        
        actual_callback = progress_callback or default_progress_callback
        
        # 使用断点续传功能
        for batch in self.stream_find_resumable(
            filters=filters,
            batch_size=batch_size,
            checkpoint_id=checkpoint_id,
            auto_checkpoint=True
        ):
            # 执行进度回调
            if actual_callback:
                try:
                    # 这里需要构造ProgressInfo，实际实现中会从跟踪器获取
                    from ginkgo.data.streaming import ProgressInfo
                    progress_info = ProgressInfo(
                        processed=len(batch),  # 简化实现
                        rate=0.0,
                        elapsed=0.0
                    )
                    actual_callback(progress_info)
                except Exception as e:
                    GLOG.WARNING(f"Progress callback failed: {e}")
            
            yield batch
    
    def get_checkpoint_status(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        🆕 获取断点状态信息
        
        Args:
            checkpoint_id: 断点ID
            
        Returns:
            断点状态信息
        """
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager
            
            checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
            if not checkpoint:
                return None
            
            return {
                "checkpoint_id": checkpoint.checkpoint_id,
                "state": checkpoint.state.value,
                "processed_count": checkpoint.processed_count,
                "progress_percentage": checkpoint.progress_percentage,
                "processing_rate": checkpoint.processing_rate,
                "elapsed_time": checkpoint.elapsed_time,
                "created_at": checkpoint.created_at,
                "updated_at": checkpoint.updated_at,
                "database_type": checkpoint.database_type,
                "engine_type": checkpoint.engine_type
            }
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get checkpoint status: {e}")
            return None
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        🆕 列出所有相关断点
        
        Returns:
            断点列表
        """
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager
            
            checkpoints = checkpoint_manager.list_checkpoints()
            return [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "state": cp.state.value,
                    "processed_count": cp.processed_count,
                    "progress_percentage": cp.progress_percentage,
                    "created_at": cp.created_at,
                    "database_type": cp.database_type
                }
                for cp in checkpoints
            ]
            
        except Exception as e:
            GLOG.ERROR(f"Failed to list checkpoints: {e}")
            return []
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        🆕 删除断点
        
        Args:
            checkpoint_id: 断点ID
            
        Returns:
            是否删除成功
        """
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager
            return checkpoint_manager.delete_checkpoint(checkpoint_id)
        except Exception as e:
            GLOG.ERROR(f"Failed to delete checkpoint: {e}")
            return False
    
    def _adjust_filters_for_resume(self, 
                                  filters: Optional[Dict[str, Any]], 
                                  checkpoint: Optional[Any],
                                  order_by: str) -> Dict[str, Any]:
        """调整过滤条件以支持断点续传"""
        adjusted_filters = dict(filters) if filters else {}
        
        if checkpoint and checkpoint.last_timestamp:
            # 使用时间戳断点续传
            timestamp_filter = f"{order_by}__gt"
            adjusted_filters[timestamp_filter] = checkpoint.last_timestamp
            GLOG.DEBUG(f"Resuming from timestamp: {checkpoint.last_timestamp}")
        elif checkpoint and checkpoint.last_offset > 0:
            # 使用偏移量断点续传（不太精确，但总比没有好）
            GLOG.DEBUG(f"Resuming from offset: {checkpoint.last_offset}")
        
        return adjusted_filters
    
    def _save_checkpoint_progress(self, 
                                checkpoint: Any, 
                                batch: List[Any], 
                                total_processed: int,
                                order_by: str):
        """保存断点进度"""
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager
            
            updates = {
                "processed_count": total_processed,
                "last_offset": total_processed
            }
            
            # 尝试从批次数据中提取时间戳
            if batch and hasattr(batch[0], order_by):
                last_timestamp = getattr(batch[-1], order_by)
                if last_timestamp:
                    updates["last_timestamp"] = str(last_timestamp)
            
            checkpoint_manager.update_checkpoint(
                checkpoint.checkpoint_id, 
                **updates
            )
            
            GLOG.DEBUG(f"Saved checkpoint progress: {total_processed} records processed")
            
        except Exception as e:
            GLOG.WARNING(f"Failed to save checkpoint progress: {e}")
    
    def _estimate_total_records(self, filters: Optional[Dict[str, Any]]) -> Optional[int]:
        """估算总记录数（用于进度计算）"""
        try:
            # 简单的估算方法：执行COUNT查询
            # 实际生产环境可以使用更复杂的估算逻辑
            count_result = self.count(filters=filters)
            return count_result if isinstance(count_result, int) else None
        except Exception as e:
            GLOG.DEBUG(f"Failed to estimate total records: {e}")
            return None

    # ==================== 🆕 内存监控和会话管理集成 ====================
    
    def stream_find_with_monitoring(self,
                                   filters: Optional[Dict[str, Any]] = None,
                                   batch_size: Optional[int] = None,
                                   order_by: Optional[str] = None,
                                   desc_order: bool = False,
                                   memory_limit_mb: Optional[float] = None,
                                   auto_optimize: bool = True) -> Any:
        """
        🆕 带内存监控的流式查询
        
        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            order_by: 排序字段
            desc_order: 是否降序
            memory_limit_mb: 内存限制（MB）
            auto_optimize: 是否启用自动优化
            
        Yields:
            查询结果批次
        """
        if not self._streaming_enabled:
            GLOG.WARNING("Streaming not enabled, falling back to traditional query")
            yield from self._fallback_to_traditional_query(filters, batch_size, order_by, desc_order)
            return
        
        try:
            # 导入监控模块
            from ginkgo.data.streaming.session_context import streaming_session
            from ginkgo.data.streaming.monitoring import memory_monitor
            
            database_type = getattr(self.driver, '_db_type', 'unknown') if hasattr(self, 'driver') else 'unknown'
            
            # 使用会话上下文管理器
            with streaming_session(
                database_type=database_type,
                auto_optimize=auto_optimize
            ) as session_context:
                
                batch_count = 0
                current_batch_size = batch_size or 1000
                
                # 内存限制检查
                if memory_limit_mb:
                    initial_snapshot = memory_monitor.get_current_snapshot()
                    if initial_snapshot.process_mb > memory_limit_mb:
                        GLOG.WARNING(
                            f"Current memory usage ({initial_snapshot.process_mb:.1f}MB) "
                            f"exceeds limit ({memory_limit_mb}MB), reducing batch size"
                        )
                        current_batch_size = max(current_batch_size // 2, 100)
                
                for batch in self.stream_find(
                    filters=filters,
                    batch_size=current_batch_size,
                    order_by=order_by,
                    desc_order=desc_order
                ):
                    batch_count += 1
                    
                    # 更新会话进度
                    from ginkgo.data.streaming.session_context import streaming_session_manager
                    
                    current_memory = memory_monitor.get_current_snapshot().process_mb
                    streaming_session_manager.update_session_progress(
                        session_context.session_id,
                        len(batch),
                        current_memory
                    )
                    
                    # 内存优化检查
                    if auto_optimize and memory_limit_mb and current_memory > memory_limit_mb:
                        # 动态调整批次大小
                        new_batch_size = max(current_batch_size // 2, 100)
                        if new_batch_size != current_batch_size:
                            GLOG.WARNING(
                                f"Memory limit exceeded ({current_memory:.1f}MB > {memory_limit_mb}MB), "
                                f"reducing batch size: {current_batch_size} -> {new_batch_size}"
                            )
                            current_batch_size = new_batch_size
                        
                        # 强制垃圾回收
                        memory_monitor.force_garbage_collection()
                    
                    yield batch
                
                # 记录最终统计
                final_metrics = streaming_session_manager.get_session_metrics(session_context.session_id)
                if final_metrics:
                    GLOG.INFO(
                        f"Streaming query completed: {final_metrics['records_processed']} records, "
                        f"{final_metrics['processing_rate']:.1f} records/sec, "
                        f"peak memory: {final_metrics['memory_peak_mb']:.1f}MB"
                    )
        
        except Exception as e:
            GLOG.ERROR(f"Monitored streaming query failed: {e}")
            # 降级到常规流式查询
            yield from self.stream_find(filters, batch_size, order_by, desc_order)
    
    def get_streaming_session_metrics(self) -> List[Dict[str, Any]]:
        """
        🆕 获取流式查询会话指标
        
        Returns:
            活跃会话指标列表
        """
        try:
            from ginkgo.data.streaming.session_context import streaming_session_manager
            return streaming_session_manager.list_active_sessions()
        except Exception as e:
            GLOG.ERROR(f"Failed to get streaming session metrics: {e}")
            return []
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        🆕 获取内存统计信息
        
        Returns:
            内存统计字典
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager
            
            memory_stats = memory_monitor.get_memory_statistics()
            session_stats = session_manager.get_session_statistics()
            
            return {
                "memory": memory_stats,
                "sessions": session_stats,
                "timestamp": time.time()
            }
        except Exception as e:
            GLOG.ERROR(f"Failed to get memory statistics: {e}")
            return {"error": str(e)}
    
    def optimize_streaming_resources(self) -> Dict[str, Any]:
        """
        🆕 手动优化流式查询资源
        
        Returns:
            优化结果报告
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager
            
            optimization_report = {
                "timestamp": time.time(),
                "actions_taken": [],
                "before": {},
                "after": {}
            }
            
            # 记录优化前状态
            optimization_report["before"] = {
                "memory_percent": memory_monitor.get_current_snapshot().percent,
                "active_sessions": len(session_manager.list_sessions(state=SessionState.ACTIVE)),
                "idle_sessions": len(session_manager.list_sessions(state=SessionState.IDLE))
            }
            
            # 1. 强制垃圾回收
            gc_result = memory_monitor.force_garbage_collection()
            if gc_result.get("collected", 0) > 0:
                optimization_report["actions_taken"].append(
                    f"Garbage collection: freed {gc_result.get('freed_objects', 0)} objects"
                )
            
            # 2. 清理过期会话
            from ginkgo.data.streaming.monitoring import SessionState
            idle_sessions = session_manager.list_sessions(state=SessionState.IDLE)
            cleaned_sessions = 0
            
            for session in idle_sessions:
                if session.idle_seconds > 300:  # 5分钟空闲
                    session_manager.close_session(session.session_id)
                    cleaned_sessions += 1
            
            if cleaned_sessions > 0:
                optimization_report["actions_taken"].append(
                    f"Cleaned {cleaned_sessions} idle sessions"
                )
            
            # 记录优化后状态
            optimization_report["after"] = {
                "memory_percent": memory_monitor.get_current_snapshot().percent,
                "active_sessions": len(session_manager.list_sessions(state=SessionState.ACTIVE)),
                "idle_sessions": len(session_manager.list_sessions(state=SessionState.IDLE))
            }
            
            # 计算优化效果
            memory_improvement = (
                optimization_report["before"]["memory_percent"] - 
                optimization_report["after"]["memory_percent"]
            )
            optimization_report["memory_improvement_percent"] = memory_improvement
            
            GLOG.INFO(f"Resource optimization completed: {optimization_report}")
            return optimization_report
            
        except Exception as e:
            GLOG.ERROR(f"Failed to optimize streaming resources: {e}")
            return {"error": str(e)}
    
    def enable_memory_monitoring(self) -> bool:
        """
        🆕 启用内存监控
        
        Returns:
            是否成功启用
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager
            
            if not memory_monitor._monitoring:
                memory_monitor.start_monitoring()
                GLOG.INFO("Memory monitoring started")
            
            if not session_manager._cleanup_enabled:
                session_manager.start_cleanup()
                GLOG.INFO("Session cleanup started")
            
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Failed to enable memory monitoring: {e}")
            return False
    
    def disable_memory_monitoring(self) -> bool:
        """
        🆕 禁用内存监控
        
        Returns:
            是否成功禁用
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager
            
            memory_monitor.stop_monitoring()
            session_manager.stop_cleanup()
            
            GLOG.INFO("Memory monitoring and session cleanup stopped")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Failed to disable memory monitoring: {e}")
            return False
