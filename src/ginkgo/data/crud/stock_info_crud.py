# Upstream: StockinfoService (股票信息业务服务)、Data Query (查询股票代码/名称/行业等信息)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MStockInfo (MySQL股票信息模型)、StockInfo实体(业务股票信息实体)、MARKET_TYPES/CURRENCY_TYPES (市场类型和货币类型枚举)
# Role: StockInfoCRUD股票信息CRUD继承BaseCRUD提供股票信息管理功能






from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MStockInfo
from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access
from ginkgo.entities import StockInfo
from ginkgo.data.crud.model_conversion import ModelList


@restrict_crud_access
class StockInfoCRUD(BaseCRUD[MStockInfo]):
    """
    StockInfo CRUD operations.
    """


    # 类级别声明，支持自动注册


    _model_class = MStockInfo


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
            market=MARKET_TYPES.validate_input(market),
            list_date=datetime_normalize(kwargs.get("list_date")),
            delist_date=datetime_normalize(kwargs.get("delist_date")),
            currency=CURRENCY_TYPES.validate_input(currency),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.TUSHARE)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MStockInfo]:
        """
        Hook method: Convert StockInfo business objects to MStockInfo data models.
        只处理StockInfo业务对象，符合架构设计原则。
        """
        from ginkgo.entities import StockInfo

        # 只处理StockInfo业务对象
        if isinstance(item, StockInfo):
            # 获取source信息，如果业务对象有设置的话
            source = getattr(item, '_source', SOURCE_TYPES.TUSHARE)

            return MStockInfo(
                code=item.code,
                code_name=item.code_name,
                industry=item.industry,
                market=item.market,
                list_date=item.list_date,
                delist_date=item.delist_date,
                currency=item.currency,
                source=source,
                uuid=item.uuid if item.uuid else None
            )

        # 不再支持字典格式，强制使用业务对象
        self._logger.WARN(f"Unsupported type for StockInfo conversion: {type(item)}. Please use StockInfo business object.")
        return None

    def _convert_output_items(self, items: List[MStockInfo], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MStockInfo objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_market(self, market: str) -> ModelList[MStockInfo]:
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

        return self.find(filters={"market": market})

    def find_by_industry(self, industry: str) -> ModelList[MStockInfo]:
        """
        Business helper: Find stocks by industry.
        """
        return self.find(filters={"industry": industry})

    def search_by_name(self, name_pattern: str) -> ModelList[MStockInfo]:
        """
        Business helper: Search stocks by name pattern.
        """
        return self.find(filters={"code_name__like": name_pattern})

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

    # ============================================================================
    # BaseCRUD Hook Methods - Enum Mapping and Business Object Conversion
    # ============================================================================

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for StockInfo.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'market': MARKET_TYPES,     # market字段对应MARKET_TYPES枚举
            'currency': CURRENCY_TYPES,  # currency字段对应CURRENCY_TYPES枚举
            'source': SOURCE_TYPES      # source字段对应SOURCE_TYPES枚举
        }

    def _convert_models_to_business_objects(self, models: List[MStockInfo]) -> List[StockInfo]:
        """
        🎯 Convert MStockInfo models to StockInfo business objects.

        Args:
            models: List of MStockInfo models with enum fields already fixed

        Returns:
            List of StockInfo business objects
        """
        business_objects = []
        for model in models:
            # Convert to business object (此时枚举字段已经是正确的枚举对象)
            stock_info = StockInfo.from_model(model)
            business_objects.append(stock_info)

        return business_objects

    
