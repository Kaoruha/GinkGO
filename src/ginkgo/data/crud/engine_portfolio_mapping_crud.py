# Upstream: EngineCRUD, PortfolioCRUD, 引擎装配层
# Downstream: BaseCRUD, MEnginePortfolioMapping模型, ModelCRUDMapping
# Role: 引擎-投资组合映射CRUD，管理引擎与Portfolio的绑定关系






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MEnginePortfolioMapping
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG, cache_with_expiration
from ginkgo.data.crud.model_crud_mapping import ModelCRUDMapping


@restrict_crud_access
class EnginePortfolioMappingCRUD(BaseCRUD[MEnginePortfolioMapping]):
    """
    EnginePortfolioMapping CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MEnginePortfolioMapping

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

    # ADR-029 §Decision 1：转换钩子 override 已退役。
    # 调用方 mapping_service.add_batch:306 传 MEnginePortfolioMapping 实例。

    # Business Helper Methods
    
    
    def find_by_engine(self, engine_id: str) -> List[MEnginePortfolioMapping]:
        """
        Business helper: Find portfolio mappings by engine ID.
        """
        filters = {"engine_id": engine_id}

        return self.find(filters=filters, order_by="uuid")

    def find_by_portfolio(self, portfolio_id: str) -> List[MEnginePortfolioMapping]:
        """
        Business helper: Find engine mappings by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}

        return self.find(filters=filters, order_by="uuid")

    def get_portfolios_for_engine(self, engine_id: str) -> List[str]:
        """
        Business helper: Get all portfolio IDs for an engine.
        """
        return [m.portfolio_id for m in mappings if m.portfolio_id]

    def get_engines_for_portfolio(self, portfolio_id: str) -> List[str]:
        """
        Business helper: Get all engine IDs for a portfolio.
        """
        return [m.engine_id for m in mappings if m.engine_id]


    def delete_mapping(self, engine_id: str, portfolio_id: str) -> None:
        """
        Delete a specific mapping.
        """
        GLOG.DEBUG(f"删除引擎-组合映射: {engine_id} -> {portfolio_id}")
        return self.remove({"engine_id": engine_id, "portfolio_id": portfolio_id})
