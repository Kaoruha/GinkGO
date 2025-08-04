from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MStockInfo
from ...enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES
from ...libs import datetime_normalize, GLOG, cache_with_expiration
from ..access_control import restrict_crud_access


@restrict_crud_access
class StockInfoCRUD(BaseCRUD[MStockInfo]):
    """
    StockInfo CRUD operations.
    """

    def __init__(self):
        super().__init__(MStockInfo)

    def _get_field_config(self) -> dict:
        """
        定义 StockInfo 数据的字段配置 - delist_date 为可选字段
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 股票代码 - 非空字符串，最大32字符
            'code': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 股票名称 - 非空字符串，最大32字符
            'code_name': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 行业 - 非空字符串，最大32字符
            'industry': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 交易市场 - 枚举值  
            'market': {
                'type': 'enum',
                'choices': [
                    MARKET_TYPES.CHINA,
                    MARKET_TYPES.NASDAQ,
                    MARKET_TYPES.OTHER
                ]
            },
            
            # 货币类型 - 枚举值
            'currency': {
                'type': 'enum', 
                'choices': [
                    CURRENCY_TYPES.CNY,
                    CURRENCY_TYPES.USD,
                    CURRENCY_TYPES.OTHER
                ]
            },
            
            # 上市时间 - datetime 或字符串
            'list_date': {
                'type': ['datetime', 'string']
            },
            
            # 退市时间 - datetime 或字符串 (使用默认值处理 None)
            'delist_date': {
                'type': ['datetime', 'string']
            },
            
            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [
                    SOURCE_TYPES.TUSHARE,
                    SOURCE_TYPES.YAHOO,
                    SOURCE_TYPES.AKSHARE,
                    SOURCE_TYPES.BAOSTOCK,
                    SOURCE_TYPES.OTHER
                ]
            }
        }

    def _create_from_params(self, **kwargs) -> MStockInfo:
        """
        Hook method: Create MStockInfo from parameters.
        """
        # Convert string market values to enum if needed
        market = kwargs.get("market", MARKET_TYPES.CHINA)
        if isinstance(market, str):
            market_mapping = {
                "CHINA": MARKET_TYPES.CHINA,
                "SSE": MARKET_TYPES.CHINA,
                "SZSE": MARKET_TYPES.OTHER,
                "NASDAQ": MARKET_TYPES.NASDAQ,
                "NYSE": MARKET_TYPES.OTHER,
                "US": MARKET_TYPES.OTHER,
                "OTHER": MARKET_TYPES.OTHER,
            }
            market = market_mapping.get(market.upper(), MARKET_TYPES.OTHER)
        
        # Convert string currency values to enum if needed  
        currency = kwargs.get("currency", CURRENCY_TYPES.CNY)
        if isinstance(currency, str):
            currency_mapping = {
                "CNY": CURRENCY_TYPES.CNY,
                "USD": CURRENCY_TYPES.USD,
                "OTHER": CURRENCY_TYPES.OTHER,
            }
            currency = currency_mapping.get(currency.upper(), CURRENCY_TYPES.OTHER)
        
        return MStockInfo(
            code=kwargs.get("code"),
            code_name=kwargs.get("code_name", ""),
            industry=kwargs.get("industry", ""),
            market=market,
            list_date=datetime_normalize(kwargs.get("list_date")),
            delist_date=datetime_normalize(kwargs.get("delist_date")),
            currency=currency,
            source=kwargs.get("source", SOURCE_TYPES.TUSHARE),
        )

    def _convert_input_item(self, item: Any) -> Optional[MStockInfo]:
        """
        Hook method: Convert stock info objects to MStockInfo.
        """
        if hasattr(item, 'code') and hasattr(item, 'code_name'):
            return MStockInfo(
                code=getattr(item, 'code'),
                code_name=getattr(item, 'code_name', ''),
                industry=getattr(item, 'industry', ''),
                market=getattr(item, 'market', MARKET_TYPES.CHINA),
                list_date=datetime_normalize(getattr(item, 'list_date', datetime.now())),
                delist_date=datetime_normalize(getattr(item, 'delist_date', datetime.now())),
                currency=getattr(item, 'currency', CURRENCY_TYPES.CNY),
                source=getattr(item, 'source', SOURCE_TYPES.TUSHARE),
            )
        return None

    def _convert_output_items(self, items: List[MStockInfo], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MStockInfo objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_market(self, market: str, as_dataframe: bool = False) -> Union[List[MStockInfo], pd.DataFrame]:
        """
        Business helper: Find stocks by market.
        """
        # Convert string market values to enum if needed
        if isinstance(market, str):
            market_mapping = {
                "CHINA": MARKET_TYPES.CHINA,
                "SSE": MARKET_TYPES.CHINA,
                "SZSE": MARKET_TYPES.OTHER,
                "NASDAQ": MARKET_TYPES.NASDAQ,
                "NYSE": MARKET_TYPES.OTHER,
                "US": MARKET_TYPES.OTHER,
                "OTHER": MARKET_TYPES.OTHER,
            }
            market = market_mapping.get(market.upper(), MARKET_TYPES.OTHER)
        
        return self.find(filters={"market": market}, as_dataframe=as_dataframe, output_type="model")

    def find_by_industry(self, industry: str, as_dataframe: bool = False) -> Union[List[MStockInfo], pd.DataFrame]:
        """
        Business helper: Find stocks by industry.
        """
        return self.find(filters={"industry": industry}, as_dataframe=as_dataframe, output_type="model")

    def search_by_name(self, name_pattern: str, as_dataframe: bool = False) -> Union[List[MStockInfo], pd.DataFrame]:
        """
        Business helper: Search stocks by name pattern.
        """
        return self.find(filters={"code_name__like": name_pattern}, as_dataframe=as_dataframe, output_type="model")

    def get_all_codes(self, market: Optional[str] = None) -> List[str]:
        """
        Business helper: Get all stock codes.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        filters = {}
        if market:
            filters["market"] = market
        
        try:
            codes = self.find(filters=filters, distinct_field="code")
            return [code for code in codes if code]
        except Exception as e:
            GLOG.ERROR(f"Failed to get stock codes: {e}")
            return []
