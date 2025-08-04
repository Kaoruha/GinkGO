from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MTradeDay
from ...enums import SOURCE_TYPES, MARKET_TYPES
from ...libs import datetime_normalize, GLOG, cache_with_expiration


@restrict_crud_access
class TradeDayCRUD(BaseCRUD[MTradeDay]):
    """
    TradeDay CRUD operations.
    """

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
                'choices': [s for s in SOURCE_TYPES]
            }
        }

    def _create_from_params(self, **kwargs) -> MTradeDay:
        """
        Hook method: Create MTradeDay from parameters.
        """
        return MTradeDay(
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            market=kwargs.get("market", MARKET_TYPES.CHINA),
            is_open=kwargs.get("is_open", True),
            source=kwargs.get("source", SOURCE_TYPES.TUSHARE),
        )

    def _convert_input_item(self, item: Any) -> Optional[MTradeDay]:
        """
        Hook method: Convert trade day objects to MTradeDay.
        """
        if hasattr(item, 'timestamp'):
            return MTradeDay(
                timestamp=datetime_normalize(getattr(item, 'timestamp')),
                market=getattr(item, 'market', MARKET_TYPES.CHINA),
                is_open=getattr(item, 'is_open', True),
                source=getattr(item, 'source', SOURCE_TYPES.TUSHARE),
            )
        return None

    def _convert_output_items(self, items: List[MTradeDay], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MTradeDay objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_trading_days(self, start_date: Any, end_date: Any, 
                         as_dataframe: bool = False) -> Union[List[MTradeDay], pd.DataFrame]:
        """
        Business helper: Find trading days in date range.
        """
        filters = {
            "timestamp__gte": datetime_normalize(start_date),
            "timestamp__lte": datetime_normalize(end_date),
            "is_open": True
        }
        return self.find(filters=filters, order_by="timestamp", as_dataframe=as_dataframe, output_type="model")

    def find_non_trading_days(self, start_date: Any, end_date: Any,
                             as_dataframe: bool = False) -> Union[List[MTradeDay], pd.DataFrame]:
        """
        Business helper: Find non-trading days in date range.
        """
        filters = {
            "timestamp__gte": datetime_normalize(start_date),
            "timestamp__lte": datetime_normalize(end_date),
            "is_open": False
        }
        return self.find(filters=filters, order_by="timestamp", as_dataframe=as_dataframe, output_type="model")

    def is_open(self, date: Any) -> bool:
        """
        Business helper: Check if a specific date is a trading day.
        """
        result = self.find(filters={"timestamp": datetime_normalize(date)}, 
                          page_size=1, as_dataframe=False, output_type="model")
        return result[0].is_open if result else False

    def get_next_trading_day(self, date: Any) -> Optional[datetime]:
        """
        Business helper: Get next trading day after given date.
        """
        result = self.find(filters={
            "timestamp__gt": datetime_normalize(date),
            "is_open": True
        }, page_size=1, order_by="timestamp", as_dataframe=False, output_type="model")
        return result[0].timestamp if result else None
