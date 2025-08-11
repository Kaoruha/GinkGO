from typing import TypeVar, Generic, List, Optional, Any, Union, Dict
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
                    GLOG.WARN(f"Deleted {self.model_class.__name__} records from MySQL")
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
                    GLOG.WARN(f"Cannot convert item {type(item)} to {self.model_class.__name__}")
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
                        GLOG.WARN(f"Unknown filter operator: {operator}")
            else:
                # Standard equality filter
                if hasattr(self.model_class, key):
                    conditions.append(getattr(self.model_class, key) == value)

        return conditions
