from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MTick
from ...backtest import Tick
from ...enums import TICKDIRECTION_TYPES, SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal

# Global registry for dynamically created tick models
tick_model_registry = {}


def get_tick_model(code: str) -> type:
    """
    Get or create dynamic Tick model for specific stock code.
    Tick data uses partitioning - each stock code has its own table.

    Args:
        code: Stock code (e.g., "000001.SZ")

    Returns:
        Dynamically created MTick subclass for the specific code
    """
    global tick_model_registry
    table_name = f"{code.replace('.', '_')}_Tick"

    if table_name not in tick_model_registry:
        # Dynamically create new model class
        newclass = type(
            table_name,
            (MTick,),
            {
                "__tablename__": table_name,
                "__abstract__": False,
            },
        )
        tick_model_registry[table_name] = newclass
        GLOG.DEBUG(f"Created dynamic tick model: {table_name}")

    return tick_model_registry[table_name]


@restrict_crud_access
class TickCRUD(BaseCRUD):
    """
    Tick CRUD operations with dynamic table partitioning support.

    Features:
    - Supports dynamic table creation for each stock code
    - Inherits ALL decorators (@time_logger, @retry, @cache) from BaseCRUD template methods
    - Only provides Tick-specific conversion and creation logic via hook methods
    - Maintains architectural purity of template method pattern

    Usage:
    # Create CRUD instance for specific stock
    tick_crud = TickCRUD("000001.SZ")

    # Use BaseCRUD template methods directly:
    - tick_crud.create(price=10.5, volume=1000, ...) - From parameters
    - tick_crud.add_batch([tick1, tick2, tick3]) - Batch addition
    - tick_crud.find(filters={"price__gte": 10.0}) - Query with filters
    - tick_crud.remove({"timestamp__gte": "2023-01-01"}) - Delete by filters
    - tick_crud.count({"direction": TICKDIRECTION_TYPES.UP}) - Count records
    """

    def __init__(self, code: str):
        """
        Initialize TickCRUD for specific stock code.

        Args:
            code: Stock code (e.g., "000001.SZ")
        """
        if not code:
            raise ValueError("Stock code cannot be empty")

        self.code = code
        self.model_class = get_tick_model(code)

        # 确保tick表存在
        self._ensure_table_exists()

        # Initialize parent with dynamically created model
        super().__init__(self.model_class)

    def _ensure_table_exists(self):
        """确保当前股票代码对应的tick表存在"""
        from ...libs import GLOG
        from ..drivers import create_table, is_table_exists
        
        try:
            if not is_table_exists(self.model_class):
                GLOG.INFO(f"Creating tick table for {self.code}: {self.model_class.__tablename__}")
                create_table(self.model_class)
                GLOG.INFO(f"Successfully created tick table: {self.model_class.__tablename__}")
                
                # 再次检查表是否创建成功
                if is_table_exists(self.model_class):
                    GLOG.DEBUG(f"Table creation verified: {self.model_class.__tablename__}")
                else:
                    GLOG.ERROR(f"Table creation failed - table still not exists: {self.model_class.__tablename__}")
            else:
                GLOG.DEBUG(f"Tick table already exists: {self.model_class.__tablename__}")
        except Exception as e:
            GLOG.ERROR(f"Failed to ensure tick table for {self.code}: {e}")
            # 不抛出异常，让调用者处理

    def _get_field_config(self) -> dict:
        """
        定义 Tick 数据的字段配置 - 所有字段都是必填的

        Returns:
            dict: 字段配置字典
        """
        return {
            # 股票代码 - 非空字符串，最大32字符
            "code": {"type": "string", "min": 1, "max": 32},
            # 成交价格 - 非负数值
            "price": {"type": ["decimal", "float", "int"], "min": 0},
            # 成交量 - 非负整数
            "volume": {"type": ["int", "float"], "min": 0},
            # 方向 - 枚举值
            "direction": {
                "type": "enum",
                "choices": [d for d in TICKDIRECTION_TYPES],
            },
            # 时间戳 - datetime 或字符串
            "timestamp": {"type": ["datetime", "string"]},
        }

    # ============================================================================
    # Hook Methods Only - These are called by BaseCRUD template methods
    # ============================================================================

    def _create_from_params(self, **kwargs):
        """
        Hook method: Create MTick from parameters.
        Called by BaseCRUD.create() template method.
        Automatically gets @time_logger + @retry effects.
        """
        return self.model_class(
            code=kwargs.get("code", self.code),  # Default to instance code
            price=to_decimal(kwargs.get("price", 0)),
            volume=kwargs.get("volume", 0),
            direction=kwargs.get("direction", TICKDIRECTION_TYPES.OTHER),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            source=kwargs.get("source", SOURCE_TYPES.TDX),
        )

    def _convert_input_item(self, item: Any):
        """
        Hook method: Convert Tick objects to MTick for database operations.
        Called by BaseCRUD.add_batch() template method.
        Automatically gets @time_logger + @retry effects.
        """
        if isinstance(item, Tick):
            return self.model_class(
                code=item.code,
                price=item.price,
                volume=item.volume,
                direction=item.direction,
                timestamp=item.timestamp,
                source=item.source if hasattr(item, "source") else SOURCE_TYPES.TDX,
            )
        return None

    def _convert_output_items(self, items: List, output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MTick objects to Tick objects for business layer.
        Called by BaseCRUD.find() template method.
        Automatically gets @time_logger effects.
        """
        if output_type == "tick":
            return [
                Tick(
                    code=item.code,
                    price=item.price,
                    volume=item.volume,
                    direction=item.direction,
                    timestamp=item.timestamp,
                )
                for item in items
            ]
        return items

    # ============================================================================
    # Business Helper Methods - Use these for common query patterns
    # ============================================================================

    def find_by_time_range(
        self,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        direction: Optional[TICKDIRECTION_TYPES] = None,
        min_volume: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Tick], pd.DataFrame]:
        """
        Business helper: Find ticks by time range and conditions.
        Calls BaseCRUD.find() template method to get all decorators.
        """
        filters = {}

        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)
        if direction:
            filters["direction"] = direction
        if min_volume:
            filters["volume__gte"] = min_volume

        return self.find(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="timestamp",
            desc_order=False,  # Ticks usually sorted chronologically
            as_dataframe=as_dataframe,
            output_type="tick" if not as_dataframe else "model",
        )

    def find_by_price_range(
        self,
        min_price: Optional[Number] = None,
        max_price: Optional[Number] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Tick], pd.DataFrame]:
        """
        Business helper: Find ticks by price range.
        Calls BaseCRUD.find() template method to get all decorators.
        """
        filters = {}

        if min_price is not None:
            filters["price__gte"] = to_decimal(min_price)
        if max_price is not None:
            filters["price__lte"] = to_decimal(max_price)
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=False,
            as_dataframe=as_dataframe,
            output_type="tick" if not as_dataframe else "model",
        )

    def find_large_volume_ticks(
        self,
        min_volume: int,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        limit: Optional[int] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Tick], pd.DataFrame]:
        """
        Business helper: Find large volume ticks.
        Calls BaseCRUD.find() template method to get all decorators.
        """
        filters = {"volume__gte": min_volume}

        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        return self.find(
            filters=filters,
            page_size=limit,
            order_by="volume",
            desc_order=True,  # Largest volume first
            as_dataframe=as_dataframe,
            output_type="tick" if not as_dataframe else "model",
        )

    def get_latest_ticks(self, limit: int = 100, as_dataframe: bool = False) -> Union[List[Tick], pd.DataFrame]:
        """
        Business helper: Get latest ticks for the stock.
        Calls BaseCRUD.find() template method to get all decorators.
        """
        return self.find(
            filters={},
            page_size=limit,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="tick" if not as_dataframe else "model",
        )

    def delete_by_time_range(self, start_time: Optional[Any] = None, end_time: Optional[Any] = None) -> None:
        """
        Business helper: Delete ticks by time range.
        Calls BaseCRUD.remove() template method to get all decorators.
        """
        if not start_time and not end_time:
            raise ValueError("Must specify at least start_time or end_time for safety")

        filters = {}
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        GLOG.WARN(f"删除股票 {self.code} 的tick数据，时间范围: {start_time} - {end_time}")
        return self.remove(filters)

    def delete_all(self) -> None:
        """
        Business helper: Delete all tick data for this stock - DANGEROUS OPERATION.
        Calls BaseCRUD.remove() template method to get all decorators.
        """
        GLOG.ERROR(f"危险操作：删除股票 {self.code} 的所有tick数据")
        # Use a condition that matches all records
        return self.remove({"code": self.code})

    def count_by_direction(self, direction: TICKDIRECTION_TYPES) -> int:
        """
        Business helper: Count ticks by direction.
        Calls BaseCRUD.count() template method to get @cache_with_expiration.
        """
        return self.count({"direction": direction})

    def count_by_time_range(self, start_time: Optional[Any] = None, end_time: Optional[Any] = None) -> int:
        """
        Business helper: Count ticks in time range.
        Calls BaseCRUD.count() template method to get @cache_with_expiration.
        """
        filters = {}
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        return self.count(filters)

    def get_trading_summary(self, start_time: Optional[Any] = None, end_time: Optional[Any] = None) -> dict:
        """
        Business helper: Get trading summary statistics.
        """
        filters = {}
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        ticks = self.find(filters=filters, as_dataframe=False, output_type="model")

        if not ticks:
            return {
                "total_count": 0,
                "total_volume": 0,
                "avg_price": 0,
                "min_price": 0,
                "max_price": 0,
                "price_range": 0,
            }

        prices = [float(tick.price) for tick in ticks if tick.price]
        volumes = [tick.volume for tick in ticks if tick.volume]

        return {
            "total_count": len(ticks),
            "total_volume": sum(volumes) if volumes else 0,
            "avg_price": sum(prices) / len(prices) if prices else 0,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "price_range": max(prices) - min(prices) if prices else 0,
        }
