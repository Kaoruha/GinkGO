# Upstream: StockinfoService (股票信息业务服务)、Data Query (查询股票代码/名称/行业等信息)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MStockInfo (MySQL股票信息模型)、StockInfo实体(业务股票信息实体)、MARKET_TYPES/CURRENCY_TYPES (市场类型和货币类型枚举)
# Role: StockInfoCRUD股票信息CRUD继承BaseCRUD提供股票信息管理功能






from typing import List, Optional, Union, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MStockInfo
from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access


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

    # ADR-029 Task 3：_convert_input_item override 已删。
    # 原 override 把 StockInfo Entity→MStockInfo（含 market/source/_source side-channel/uuid None-coalesce）
    # 收敛到 StockInfoMapper.entity_to_model。入站调用方（stockinfo_service:225,265,274）
    # 已显式走 mapper，CRUD add_batch 收到的就是 MStockInfo 实例，
    # BaseCRUD._convert_input_batch 走 isinstance(model_class) 分支直接放行，无需 override。

    # Business Helper Methods
    def find_by_market(self, market: str) -> list:
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

    def find_by_industry(self, industry: str) -> list:
        """
        Business helper: Find stocks by industry.
        """
        return self.find(filters={"industry": industry})

    def search_by_name(self, name_pattern: str) -> list:
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
