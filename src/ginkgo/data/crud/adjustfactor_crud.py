from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MAdjustfactor
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class AdjustfactorCRUD(BaseCRUD[MAdjustfactor]):
    """
    Adjustfactor CRUD operations - Only overrides hook methods, never template methods.

    Features:
    - Inherits ALL decorators (@time_logger, @retry, @cache) from BaseCRUD template methods
    - Only provides Adjustfactor-specific conversion and creation logic via hook methods
    - Supports complex adjustment factor calculations and historical tracking
    - Maintains architectural purity of template method pattern

    Usage:
    Use BaseCRUD template methods directly:
    - adjustfactor.create(timestamp="2023-01-01", code="000001.SZ", ...) - From parameters
    - adjustfactor.add_batch([factor1, factor2, factor3]) - Batch addition
    - adjustfactor.find(filters={"code": "000001.SZ"}) - Query with filters
    - adjustfactor.remove({"code": "000001.SZ"}) - Delete by filters
    - adjustfactor.count({"code": "000001.SZ"}) - Count records
    """

    # 类级别声明，支持自动注册
    _model_class = MAdjustfactor

    def __init__(self):
        super().__init__(MAdjustfactor)

    def _get_field_config(self) -> dict:
        """
        定义 Adjustfactor 数据的字段配置
        
        注意：source字段不在此配置中，使用模型的默认值 SOURCE_TYPES.OTHER
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 股票代码 - 非空字符串
            'code': {
                'type': 'string',
                'min': 1
            },
            
            # 前复权因子 - 必须大于0的数值
            'foreadjustfactor': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.001
            },
            
            # 后复权因子 - 必须大于0的数值
            'backadjustfactor': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.001
            },
            
            # 复权因子 - 必须大于0的数值
            'adjustfactor': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.001
            },
            
            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            }
            
            # source字段已移除 - 使用模型默认值 SOURCE_TYPES.OTHER
        }

    # ============================================================================
    # Hook Methods Only - These are called by BaseCRUD template methods
    # ============================================================================

    def _create_from_params(self, **kwargs) -> MAdjustfactor:
        """
        Hook method: Create MAdjustfactor from parameters.
        Called by BaseCRUD.create() template method.
        Automatically gets @time_logger + @retry effects.
        """
        return MAdjustfactor(
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            code=kwargs.get("code"),
            foreadjustfactor=to_decimal(kwargs.get("foreadjustfactor", 1.0)),
            backadjustfactor=to_decimal(kwargs.get("backadjustfactor", 1.0)),
            adjustfactor=to_decimal(kwargs.get("adjustfactor", 1.0)),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.TUSHARE)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MAdjustfactor]:
        """
        Hook method: Convert adjustment factor objects to MAdjustfactor for database operations.
        Called by BaseCRUD.add_batch() template method.
        Automatically gets @time_logger + @retry effects.
        """
        if hasattr(item, "timestamp") and hasattr(item, "code") and hasattr(item, "adjustfactor"):
            return MAdjustfactor(
                timestamp=datetime_normalize(getattr(item, "timestamp")),
                code=getattr(item, "code"),
                foreadjustfactor=to_decimal(getattr(item, "foreadjustfactor", 1.0)),
                backadjustfactor=to_decimal(getattr(item, "backadjustfactor", 1.0)),
                adjustfactor=to_decimal(getattr(item, "adjustfactor", 1.0)),
                source=SOURCE_TYPES.validate_input(getattr(item, "source", SOURCE_TYPES.TUSHARE)),
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for Adjustfactor.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES  # 数据源字段映射
        }

    def _convert_models_to_business_objects(self, models: List[MAdjustfactor]) -> List[MAdjustfactor]:
        """
        🎯 Convert MAdjustfactor models to business objects.

        Args:
            models: List of MAdjustfactor models with enum fields already fixed

        Returns:
            List of MAdjustfactor models (Adjustfactor business object doesn't exist yet)
        """
        # For now, return models as-is since Adjustfactor business object doesn't exist yet
        return models

    def _convert_output_items(self, items: List[MAdjustfactor], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MAdjustfactor objects for business layer.
        Called by BaseCRUD.find() template method.
        Automatically gets @time_logger effects.
        """
        return items  # Return model objects directly

    # ============================================================================
    # Business Helper Methods - Use these for common query patterns
    # ============================================================================

    def find_by_code(
        self,
        code: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        desc_order: bool = True,
        as_dataframe: bool = False,
    ) -> Union[List[MAdjustfactor], pd.DataFrame]:
        """
        Business helper: Find adjustment factors by stock code.
        Calls BaseCRUD.find() template method to get all decorators.
        """
        filters = {"code": code}

        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="timestamp",
            desc_order=desc_order,
            as_dataframe=as_dataframe,
        )

    def find_latest_factor(
        self, code: str, as_of_date: Optional[Any] = None, as_dataframe: bool = False
    ) -> Union[List[MAdjustfactor], pd.DataFrame]:
        """
        Business helper: Find latest adjustment factor for a stock.
        Calls BaseCRUD.find() template method to get all decorators.
        """
        filters = {"code": code}

        if as_of_date:
            filters["timestamp__lte"] = datetime_normalize(as_of_date)

        return self.find(
            filters=filters,
            page_size=1,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
        )

    def find_by_date_range(
        self,
        start_date: Any,
        end_date: Any,
        codes: Optional[List[str]] = None,
        as_dataframe: bool = False,
    ) -> Union[List[MAdjustfactor], pd.DataFrame]:
        """
        Business helper: Find adjustment factors by date range.
        Calls BaseCRUD.find() template method to get all decorators.
        """
        filters = {"timestamp__gte": datetime_normalize(start_date), "timestamp__lte": datetime_normalize(end_date)}

        if codes:
            filters["code__in"] = codes

        return self.find(
            filters=filters, order_by="timestamp", desc_order=True, as_dataframe=as_dataframe
        )

    def delete_by_code(self, code: str, start_date: Optional[Any] = None, end_date: Optional[Any] = None) -> None:
        """
        Business helper: Delete adjustment factors by code.
        Calls BaseCRUD.remove() template method to get all decorators.
        """
        if not code:
            raise ValueError("code不能为空")

        filters = {"code": code}

        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        GLOG.WARN(f"删除股票 {code} 的复权因子数据")
        return self.remove(filters)

    def count_by_code(self, code: str) -> int:
        """
        Business helper: Count adjustment factors for a specific stock.
        Calls BaseCRUD.count() template method to get @cache_with_expiration.
        """
        return self.count({"code": code})

    def get_adjustment_summary(
        self, code: str, start_date: Optional[Any] = None, end_date: Optional[Any] = None
    ) -> dict:
        """
        Business helper: Get adjustment factor summary for a stock.
        """

        filters = {"code": code}

        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        factors = self.find(filters=filters, as_dataframe=False)

        if not factors:
            return {
                "code": code,
                "total_adjustments": 0,
                "latest_factor": 1.0,
                "cumulative_factor": 1.0,
                "date_range": (None, None),
            }

        # Sort by timestamp
        factors.sort(key=lambda x: x.timestamp)

        # Calculate cumulative adjustment
        cumulative_factor = 1.0
        for factor in factors:
            if factor.adjustfactor:
                cumulative_factor *= float(factor.adjustfactor)

        return {
            "code": code,
            "total_adjustments": len(factors),
            "latest_factor": float(factors[-1].adjustfactor) if factors[-1].adjustfactor else 1.0,
            "cumulative_factor": cumulative_factor,
            "date_range": (factors[0].timestamp, factors[-1].timestamp),
        }

    def get_all_codes(self) -> List[str]:
        """
        Business helper: Get all distinct stock codes with adjustment factors.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            codes = self.find(distinct_field="code")
            return [code for code in codes if code]
        except Exception as e:
            GLOG.ERROR(f"Failed to get adjustment factor codes: {e}")
            return []

    def modify(self, filters: Dict[str, Any], updates: Dict[str, Any]) -> int:
        """
        Modify method using replace for ClickHouse compatibility.

        For all databases (ClickHouse and MySQL), uses replace method:
        1. Find existing records matching filters
        2. Create updated records with new values
        3. Use replace method for atomic delete-then-insert operation

        Args:
            filters: Dictionary of field -> value filters for selection
            updates: Dictionary of field -> value updates to apply

        Returns:
            int: Number of records updated
        """
        if not filters or not updates:
            GLOG.ERROR("Modify operation requires both filters and updates")
            return 0

        try:
            # Step 1: Find existing records matching filters
            existing_records = self.find(filters=filters)

            if not existing_records:
                GLOG.DEBUG(f"No records found matching filters {filters}")
                return 0

            # Step 2: Create updated records
            updated_records = []
            for record in existing_records:
                # Create a copy of the record with updated fields
                updated_data = {
                    'timestamp': record.timestamp,
                    'code': record.code,
                    'foreadjustfactor': record.foreadjustfactor,
                    'backadjustfactor': record.backadjustfactor,
                    'adjustfactor': record.adjustfactor,
                    'source': record.source
                }

                # Apply updates
                for field, new_value in updates.items():
                    if hasattr(record, field):
                        if field == 'timestamp':
                            updated_data[field] = datetime_normalize(new_value)
                        elif field in ['foreadjustfactor', 'backadjustfactor', 'adjustfactor']:
                            updated_data[field] = to_decimal(new_value)
                        elif field == 'source':
                            updated_data[field] = SOURCE_TYPES.validate_input(new_value)
                        else:
                            updated_data[field] = new_value
                    else:
                        GLOG.WARN(f"Field {field} not found in MAdjustfactor model")

                # Convert to MAdjustfactor object
                updated_record = self._create_from_params(**updated_data)
                updated_records.append(updated_record)

            # Step 3: Use replace method for atomic delete-then-insert operation
            replaced_items = self.replace(filters=filters, new_items=updated_records)
            GLOG.DEBUG(f"Replaced {len(replaced_items)} records using modify operation")

            return len(replaced_items)

        except Exception as e:
            GLOG.ERROR(f"Modify operation failed: {e}")
            raise
