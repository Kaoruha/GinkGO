from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MAnalyzerRecord
from ...enums import SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration
from ..access_control import restrict_crud_access


@restrict_crud_access
class AnalyzerRecordCRUD(BaseCRUD[MAnalyzerRecord]):
    """
    AnalyzerRecord CRUD operations.
    """

    def __init__(self):
        super().__init__(MAnalyzerRecord)

    def _get_field_config(self) -> dict:
        """
        定义 AnalyzerRecord 数据的字段配置 - 所有字段都是必填的
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合ID - 非空字符串
            'portfolio_id': {
                'type': 'string',
                'min': 1
            },
            
            # 引擎ID - 非空字符串
            'engine_id': {
                'type': 'string',
                'min': 1
            },
            
            # 分析器名称 - 非空字符串
            'analyzer_name': {
                'type': 'string',
                'min': 1,
                'max': 50
            },
            
            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            },
            
            # 分析结果值 - 数值
            'value': {
                'type': ['decimal', 'float', 'int']
            },
            
            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [
                    SOURCE_TYPES.SIM,
                    SOURCE_TYPES.LIVE,
                    SOURCE_TYPES.BACKTEST,
                    SOURCE_TYPES.OTHER
                ]
            }
        }

    def _create_from_params(self, **kwargs) -> MAnalyzerRecord:
        """
        Hook method: Create MAnalyzerRecord from parameters.
        """
        return MAnalyzerRecord(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"), 
            analyzer_name=kwargs.get("analyzer_name"),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            value=to_decimal(kwargs.get("value", 0)),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MAnalyzerRecord]:
        """
        Hook method: Convert analyzer record objects to MAnalyzerRecord.
        """
        if hasattr(item, 'portfolio_id') and hasattr(item, 'analyzer_name'):
            return MAnalyzerRecord(
                portfolio_id=getattr(item, 'portfolio_id'),
                engine_id=getattr(item, 'engine_id', ''),
                analyzer_name=getattr(item, 'analyzer_name'),
                timestamp=datetime_normalize(getattr(item, 'timestamp', datetime.now())),
                value=to_decimal(getattr(item, 'value', 0)),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _convert_output_items(self, items: List[MAnalyzerRecord], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MAnalyzerRecord objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_portfolio(self, portfolio_id: str, analyzer_name: Optional[str] = None, 
                         start_date: Optional[Any] = None, end_date: Optional[Any] = None,
                         as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Find analyzer records by portfolio.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if analyzer_name:
            filters["analyzer_name"] = analyzer_name
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(filters=filters, order_by="timestamp", desc_order=True, 
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_analyzer(self, analyzer_name: str, portfolio_id: Optional[str] = None,
                        as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Find records by analyzer name.
        """
        filters = {"analyzer_name": analyzer_name}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
            
        return self.find(filters=filters, order_by="timestamp", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def get_latest_values(self, portfolio_id: str, as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Get latest analyzer values for a portfolio.
        """
        return self.find_by_portfolio(portfolio_id, page_size=10, as_dataframe=as_dataframe)

    def get_portfolio_ids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio_ids from analyzer_record table.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_ids = self.find(distinct_field="portfolio_id")
            return [pid for pid in portfolio_ids if pid is not None]
        except Exception as e:
            GLOG.ERROR(f"Failed to get portfolio ids from analyzer records: {e}")
            return []

    def get_engine_ids(self) -> List[str]:
        """
        Business helper: Get all distinct engine_ids from analyzer_record table.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            engine_ids = self.find(distinct_field="engine_id")
            return [eid for eid in engine_ids if eid is not None]
        except Exception as e:
            GLOG.ERROR(f"Failed to get engine ids from analyzer records: {e}")
            return []
