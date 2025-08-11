from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MTickSummary
from ...enums import SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal


@restrict_crud_access
class TickSummaryCRUD(BaseCRUD[MTickSummary]):
    """
    TickSummary CRUD operations.
    """

    def __init__(self):
        super().__init__(MTickSummary)

    def _get_field_config(self) -> dict:
        """
        定义 TickSummary 数据的字段配置 - 根据MTickSummary模型字段
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 股票代码 - 非空字符串，最大32位
            'code': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 价格 - 非负数
            'price': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 成交量 - 非负整数
            'volume': {
                'type': ['int', 'float'],
                'min': 0
            },
            
            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            },
            
            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [s for s in SOURCE_TYPES]
            }
        }

    def _create_from_params(self, **kwargs) -> MTickSummary:
        """
        Hook method: Create MTickSummary from parameters.
        """
        return MTickSummary(
            code=kwargs.get("code", ""),
            price=to_decimal(kwargs.get("price", 0)),
            volume=kwargs.get("volume", 0),
            timestamp=datetime_normalize(kwargs.get("timestamp", datetime.now())),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.OTHER)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MTickSummary]:
        """
        Hook method: Convert tick summary objects to MTickSummary.
        """
        if hasattr(item, 'code') and hasattr(item, 'timestamp'):
            return MTickSummary(
                code=getattr(item, 'code', ''),
                price=to_decimal(getattr(item, 'price', 0)),
                volume=getattr(item, 'volume', 0),
                timestamp=datetime_normalize(getattr(item, 'timestamp')),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.OTHER)),
            )
        return None

    def _convert_output_items(self, items: List[MTickSummary], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MTickSummary objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_code(self, code: str, start_date: Optional[Any] = None, 
                    end_date: Optional[Any] = None, as_dataframe: bool = False) -> Union[List[MTickSummary], pd.DataFrame]:
        """
        Business helper: Find tick summaries by stock code.
        """
        filters = {"code": code}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(filters=filters, order_by="timestamp", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_date(self, date: Any, codes: Optional[List[str]] = None,
                    as_dataframe: bool = False) -> Union[List[MTickSummary], pd.DataFrame]:
        """
        Business helper: Find tick summaries by date.
        """
        filters = {"timestamp": datetime_normalize(date)}
        
        if codes:
            filters["code__in"] = codes

        return self.find(filters=filters, order_by="code", 
                        as_dataframe=as_dataframe, output_type="model")

    def get_daily_summary(self, date: Any, code: str) -> Optional[dict]:
        """
        Business helper: Get daily tick summary for a specific stock.
        """
        result = self.find(filters={"code": code, "timestamp": datetime_normalize(date)},
                          page_size=1, as_dataframe=False, output_type="model")
        
        if result:
            summary = result[0]
            return {
                "code": summary.code,
                "date": summary.timestamp,
                "price": float(summary.price) if summary.price else 0,
                "volume": summary.volume,
                "source": summary.source,
            }
        return None
