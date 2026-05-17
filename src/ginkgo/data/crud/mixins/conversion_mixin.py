"""Type conversion and enum handling Mixin for CRUD operations."""

from typing import Any, Dict, List, Optional, Type
import pandas as pd
from decimal import Decimal


class ConversionMixin:
    """Mixin providing type conversion and enum handling for CRUD operations.

    Depends on instance attributes set by CoreCRUD.__init__:
    - self.model_class
    - self._is_clickhouse
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

    def _convert_input_batch(self, items: List[Any]) -> list:
        """
        Convert a batch of input items to model instances.
        Attempts automatic conversion for each item.
        🎯 Also validates enum fields for all items.

        Args:
            items: List of input items (may be mixed types)

        Returns:
            List of converted model instances with validated enum fields
        """
        converted = []
        for item in items:
            if isinstance(item, self.model_class):
                # 🎯 Validate enum fields for existing model instances
                validated_item = self._validate_item_enum_fields(item)
                converted.append(validated_item)
            else:
                # Try to convert using subclass conversion method
                converted_item = self._convert_input_item(item)
                if converted_item is not None:
                    # 🎯 Validate enum fields for converted items
                    validated_item = self._validate_item_enum_fields(converted_item)
                    converted.append(validated_item)
        return converted

    def _convert_input_item(self, item: Any):
        """
        Hook method: Override to support input type conversion.

        Args:
            item: Input item to convert

        Returns:
            Converted model instance or None if conversion not supported
        """
        return None  # Default: no conversion supported

    def _convert_output_items(self, items: list, output_type: str = "model") -> list:
        """
        Hook method: Override to support output type conversion.

        Args:
            items: List of model instances
            output_type: Desired output type

        Returns:
            List of converted output objects
        """
        return items  # Default: return model instances as-is

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Hook method: Override to define field-to-enum mappings.
        Subclasses should return a dictionary mapping field names to enum classes.

        Returns:
            Dictionary mapping field names to enum classes
            Example: {'market': MARKET_TYPES, 'currency': CURRENCY_TYPES}
        """
        return {}  # Default: no enum conversions

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

    def _convert_to_business_objects(self, raw_results: list) -> list:
        """
        🎯 Hook method: Convert raw models to business objects.
        First fixes enum fields, then calls business object conversion hook.

        Args:
            raw_results: List of raw model instances from database

        Returns:
            List of converted business objects
        """
        # First fix enum fields in raw models
        enum_mappings = self._get_enum_mappings()
        for model in raw_results:
            for column, enum_class in enum_mappings.items():
                if hasattr(model, column):
                    current_value = getattr(model, column)
                    converted_value = self._safe_enum_convert(current_value, enum_class)
                    if converted_value is not None:
                        setattr(model, column, converted_value)

        # Then call business object conversion hook
        return self._convert_models_to_business_objects(raw_results)

    def _convert_models_to_business_objects(self, models: list) -> list:
        """
        🎯 Hook method: Convert enum-fixed models to business objects.
        Subclasses should override this method to implement specific business logic.

        Args:
            models: List of models with enum fields already fixed

        Returns:
            List of business objects
        """
        return models  # Default: return models as-is

    def _convert_models_to_dataframe(self, models: list) -> pd.DataFrame:
        """
        🎯 Convert models to pandas DataFrame with enum conversion.

        Args:
            models: List of model instances

        Returns:
            pandas DataFrame with enum fields converted to their proper representation
        """
        if not models:
            return pd.DataFrame()

        # First fix enum fields in models
        enum_mappings = self._get_enum_mappings()
        for model in models:
            for column, enum_class in enum_mappings.items():
                if hasattr(model, column):
                    current_value = getattr(model, column)
                    converted_value = self._safe_enum_convert(current_value, enum_class)
                    if converted_value is not None:
                        setattr(model, column, converted_value)

        # Convert to DataFrame
        data = []
        for model in models:
            model_dict = model.__dict__.copy()
            # Remove SQLAlchemy internal state
            model_dict.pop('_sa_instance_state', None)
            data.append(model_dict)

        return pd.DataFrame(data)

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
