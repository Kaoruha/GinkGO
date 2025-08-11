from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MEnginePortfolioMapping
from ...enums import SOURCE_TYPES
from ...libs import GLOG, cache_with_expiration


@restrict_crud_access
class EnginePortfolioMappingCRUD(BaseCRUD[MEnginePortfolioMapping]):
    """
    EnginePortfolioMapping CRUD operations.
    """

    def __init__(self):
        super().__init__(MEnginePortfolioMapping)

    def _get_field_config(self) -> dict:
        """
        定义 EnginePortfolioMapping 数据的字段配置
        
        Returns:
            dict: 字段配置字典
        """
        return {
            'engine_id': {'type': 'string', 'min': 1},
            'portfolio_id': {'type': 'string', 'min': 1}
            # is_active、priority、source字段移除验证配置，使用_create_from_params中的默认值
        }

    def _create_from_params(self, **kwargs) -> MEnginePortfolioMapping:
        """
        Hook method: Create MEnginePortfolioMapping from parameters.
        只使用模型实际支持的字段：engine_id, portfolio_id, engine_name, portfolio_name, source
        """
        return MEnginePortfolioMapping(
            engine_id=kwargs.get("engine_id"),
            portfolio_id=kwargs.get("portfolio_id"),
            engine_name=kwargs.get("engine_name", ""),
            portfolio_name=kwargs.get("portfolio_name", ""),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MEnginePortfolioMapping]:
        """
        Hook method: Convert mapping objects to MEnginePortfolioMapping.
        只使用模型实际支持的字段：engine_id, portfolio_id, engine_name, portfolio_name, source
        """
        if hasattr(item, 'engine_id') and hasattr(item, 'portfolio_id'):
            return MEnginePortfolioMapping(
                engine_id=getattr(item, 'engine_id'),
                portfolio_id=getattr(item, 'portfolio_id'),
                engine_name=getattr(item, 'engine_name', ''),
                portfolio_name=getattr(item, 'portfolio_name', ''),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _convert_output_items(self, items: List[MEnginePortfolioMapping], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MEnginePortfolioMapping objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_engine(self, engine_id: str,
                      as_dataframe: bool = False) -> Union[List[MEnginePortfolioMapping], pd.DataFrame]:
        """
        Business helper: Find portfolio mappings by engine ID.
        """
        filters = {"engine_id": engine_id}
        
        return self.find(filters=filters, order_by="uuid",
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_portfolio(self, portfolio_id: str,
                         as_dataframe: bool = False) -> Union[List[MEnginePortfolioMapping], pd.DataFrame]:
        """
        Business helper: Find engine mappings by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}
        
        return self.find(filters=filters, order_by="uuid",
                        as_dataframe=as_dataframe, output_type="model")

    def get_portfolios_for_engine(self, engine_id: str) -> List[str]:
        """
        Business helper: Get all portfolio IDs for an engine.
        """
        mappings = self.find_by_engine(engine_id, as_dataframe=False)
        return [m.portfolio_id for m in mappings if m.portfolio_id]

    def get_engines_for_portfolio(self, portfolio_id: str) -> List[str]:
        """
        Business helper: Get all engine IDs for a portfolio.
        """
        mappings = self.find_by_portfolio(portfolio_id, as_dataframe=False)
        return [m.engine_id for m in mappings if m.engine_id]


    def delete_mapping(self, engine_id: str, portfolio_id: str) -> None:
        """
        Delete a specific mapping.
        """
        GLOG.INFO(f"删除引擎-组合映射: {engine_id} -> {portfolio_id}")
        return self.remove({"engine_id": engine_id, "portfolio_id": portfolio_id})
