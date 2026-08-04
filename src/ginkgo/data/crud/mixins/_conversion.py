"""BaseCRUD 内部实现：枚举处理与 create/DF hook 残留。

此模块是 BaseCRUD 的文件拆分部分，不是独立的 Mixin。
仅通过 BaseCRUD 使用，不对外导出。

ADR-029 §Decision 1：Entity↔ORM 转换钩子族（``_convert_input_batch`` /
``_convert_input_item`` / ``_convert_output_items`` /
``_convert_to_business_objects`` / ``_convert_models_to_business_objects`` /
``_convert_models_to_dataframe``）已退役，转换收敛到 ``ginkgo.data.mappers``
（``entity_to_model`` / ``models_to_dataframe``）。本模块仅保留 enum 处理
（真值下沉到 model 字段 ``info``，``_get_enum_mappings`` 反射）与
``_create_from_params``（``create()`` 模板方法 hook）。
"""

from typing import Any, Dict, List, Optional
import pandas as pd


class _Conversion:
    """BaseCRUD 的枚举处理与 ``_create_from_params`` hook 实现。

    依赖 CoreCRUD.__init__ 设置的实例属性：
    - self.model_class
    """

    def _validate_item_enum_fields(self, item: Any) -> Any:
        """
        🎯 Validate and convert enum fields in an item based on _get_enum_mappings().
        Ensures enum fields are properly converted to their integer values for database storage.

        Args:
            item: Item to validate (model instance, entity, or dict)

        Returns:
            Validated item with enum fields converted to integers
        """
        enum_mappings = self._get_enum_mappings()
        if not enum_mappings:
            return item  # No enum mappings, return as-is

        # Handle different item types
        if hasattr(item, '__dict__'):
            # Model instance or object with attributes
            for field, enum_class in enum_mappings.items():
                if hasattr(item, field):
                    value = getattr(item, field)
                    if value is not None:
                        converted_value = self._normalize_single_enum_value(value, enum_class, field)
                        if converted_value is not None:
                            try:
                                setattr(item, field, converted_value)
                            except AttributeError:
                                # Skip read-only properties (common in business entities)
                                from ginkgo.libs import GLOG
                                GLOG.DEBUG(f"Skipping read-only property {field} for {type(item).__name__}")
        elif isinstance(item, dict):
            # Dictionary
            for field, enum_class in enum_mappings.items():
                if field in item and item[field] is not None:
                    converted_value = self._normalize_single_enum_value(item[field], enum_class, field)
                    if converted_value is not None:
                        item[field] = converted_value

        return item

    def _create_from_params(self, **kwargs):
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

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """字段→enum 映射(ADR c1):真值下沉到 model 字段定义。

        默认实现反射 ``self.model_class.__table__.columns``，取每列
        ``mapped_column(..., info={'enum': XxxTypes})`` 声明的 enum 类。
        子类仍可 override（迁移期 fallback；全量迁移后 override 应清零，
        真值单源归位字段定义）。CH(MClickBase)/MySQL(MMysqlBase) 同属 SA
        DeclarativeBase，反射两库通用；Mongo(MMongoBase) 走 Pydantic
        model_dump，不经此路径。
        """
        model_cls = getattr(self, "model_class", None)
        if model_cls is None or not hasattr(model_cls, "__table__"):
            return {}
        mappings: Dict[str, Any] = {}
        for col in model_cls.__table__.columns:
            enum_cls = (col.info or {}).get("enum")
            if enum_cls is not None:
                mappings[col.name] = enum_cls
        return mappings

    def _process_dataframe_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🎯 Hook method: Process DataFrame output with enum conversions.
        Applies enum mappings to DataFrame columns.

        Args:
            df: Raw DataFrame from database

        Returns:
            DataFrame with enum fields properly converted
        """
        enum_mappings = self._get_enum_mappings()
        if not enum_mappings:
            return df

        df_converted = df.copy()
        for column, enum_class in enum_mappings.items():
            if column in df_converted.columns:
                df_converted[column] = df_converted[column].apply(
                    lambda x: self._safe_enum_convert(x, enum_class)
                )

        return df_converted

    def _safe_enum_convert(self, value, enum_class):
        """
        Utility method: Safe enum conversion with error handling.

        Args:
            value: Value to convert (typically int)
            enum_class: Enum class to convert to

        Returns:
            Enum instance or original value if conversion fails
        """
        try:
            if value is None:
                return None
            return enum_class(value)
        except (ValueError, TypeError):
            return value  # Return original value if conversion fails

    def _convert_enum_values(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 Convert enum values based on _get_enum_mappings() for precise enum handling.
        Only processes fields defined in enum_mappings, avoiding unnecessary type checks.

        Args:
            filters: Original filters dictionary

        Returns:
            Filters dictionary with enum values converted to integers
        """
        enum_mappings = self._get_enum_mappings()
        if not enum_mappings:
            return filters  # No enum mappings, return as-is

        converted_filters = filters.copy()

        for field, enum_class in enum_mappings.items():
            # Handle direct field matches
            if field in converted_filters:
                value = converted_filters[field]
                converted_filters[field] = self._normalize_single_enum_value(value, enum_class, field)

            # Handle operator suffixed fields (e.g., status__in, direction__gte)
            for suffix in ['__gte', '__lte', '__gt', '__lt', '__in', '__like']:
                field_with_suffix = field + suffix
                if field_with_suffix in converted_filters:
                    value = converted_filters[field_with_suffix]
                    converted_filters[field_with_suffix] = self._normalize_single_enum_value(value, enum_class, field)

        return converted_filters

    def _normalize_single_enum_value(self, value, enum_class, field_name: str):
        """
        🎯 Normalize a single enum value based on the expected enum class.

        Args:
            value: The value to normalize (enum, int, or list)
            enum_class: The expected enum class
            field_name: Field name for logging purposes

        Returns:
            Normalized value (enum converted to int, int validated, or original value)
        """
        if value is None:
            return None

        if isinstance(value, enum_class):
            # Convert enum to its integer value
            return value.value
        elif isinstance(value, list):
            # Handle lists containing enum values
            return [
                item.value if isinstance(item, enum_class) else item
                for item in value if item is not None
            ]
        elif isinstance(value, int):
            # Validate that the integer is a valid enum value
            try:
                enum_class(value)  # This will raise ValueError if invalid
                return value
            except ValueError:
                from ginkgo.libs import GLOG
                GLOG.WARN(f"Invalid enum value {value} for field {field_name}, expected {enum_class.__name__}")
                return value  # Return original value instead of None
        else:
            # Not an enum field value, return as-is
            return value
