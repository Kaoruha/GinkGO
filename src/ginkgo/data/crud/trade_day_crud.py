from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MTradeDay
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.trading.entities.tradeday import TradeDay
from ginkgo.data.crud.model_conversion import ModelList


@restrict_crud_access
class TradeDayCRUD(BaseCRUD[MTradeDay]):
    """
    TradeDay CRUD operations.
    """

    # 类级别声明，支持自动注册
    _model_class = MTradeDay

    def __init__(self):
        super().__init__(MTradeDay)

    def _get_field_config(self) -> dict:
        """
        定义 TradeDay 数据的字段配置 - 所有字段都是必填的
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            },
            
            # 市场类型 - 枚举值
            'market': {
                'type': 'enum',
                'choices': [m for m in MARKET_TYPES]
            },
            
            # 是否开市 - 布尔值
            'is_open': {
                'type': 'bool'
            },
            
            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [
                    SOURCE_TYPES.TUSHARE,
                    SOURCE_TYPES.YAHOO,
                    SOURCE_TYPES.AKSHARE,
                    SOURCE_TYPES.BAOSTOCK,
                    SOURCE_TYPES.OTHER,
                    SOURCE_TYPES.TEST
                ]
            }
        }

    def _convert_models_to_business_objects(self, models: List[MTradeDay]) -> List[TradeDay]:
        """
        Convert MTradeDay models to TradeDay business objects.

        Args:
            models: List of MTradeDay models with enum fields already fixed

        Returns:
            List of TradeDay business objects
        """
        return [TradeDay.from_model(model) for model in models]

    def _create_from_params(self, **kwargs) -> MTradeDay:
        """
        Hook method: Create MTradeDay from parameters.
        """
        return MTradeDay(
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            market=MARKET_TYPES.validate_input(kwargs.get("market", MARKET_TYPES.CHINA)) or MARKET_TYPES.CHINA.value,
            is_open=kwargs.get("is_open", True),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.TUSHARE)) or SOURCE_TYPES.TUSHARE.value,
        )

    def _convert_input_item(self, item: Any) -> Optional[MTradeDay]:
        """
        Hook method: Convert trade day objects to MTradeDay.
        """
        if hasattr(item, 'timestamp'):
            return MTradeDay(
                timestamp=datetime_normalize(getattr(item, 'timestamp')),
                market=MARKET_TYPES.validate_input(getattr(item, 'market', MARKET_TYPES.CHINA)) or MARKET_TYPES.CHINA.value,
                is_open=getattr(item, 'is_open', True),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.TUSHARE)) or SOURCE_TYPES.TUSHARE.value,
            )
        return None


    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'market': MARKET_TYPES,
            'source': SOURCE_TYPES
        }

    def _convert_output_items(self, items: List, output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_trading_days(self, start_date: Any, end_date: Any) -> ModelList[MTradeDay]:
        """
        Business helper: Find trading days in date range.
        """
        filters = {
            "timestamp__gte": datetime_normalize(start_date),
            "timestamp__lte": datetime_normalize(end_date),
            "is_open": True
        }
        return self.find(filters=filters, order_by="timestamp")

    def find_non_trading_days(self, start_date: Any, end_date: Any) -> ModelList[MTradeDay]:
        """
        Business helper: Find non-trading days in date range.
        """
        filters = {
            "timestamp__gte": datetime_normalize(start_date),
            "timestamp__lte": datetime_normalize(end_date),
            "is_open": False
        }
        return self.find(filters=filters, order_by="timestamp")

    def is_open(self, date: Any) -> bool:
        """
        Business helper: Check if a specific date is a trading day.
        """
        result = self.find(filters={"timestamp": datetime_normalize(date)},
                          page_size=1)
        return result[0].is_open if result else False

    def get_next_trading_day(self, date: Any) -> Optional[datetime]:
        """
        Business helper: Get next trading day after given date.
        """
        result = self.find(filters={
            "timestamp__gt": datetime_normalize(date),
            "is_open": True
        }, page_size=1, order_by="timestamp")
        return result[0].timestamp if result else None
