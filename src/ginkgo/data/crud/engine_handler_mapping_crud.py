from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MEngineHandlerMapping
from ...enums import SOURCE_TYPES
from ...libs import GLOG, cache_with_expiration


@restrict_crud_access
class EngineHandlerMappingCRUD(BaseCRUD[MEngineHandlerMapping]):
    """
    EngineHandlerMapping CRUD operations.
    """

    def __init__(self):
        super().__init__(MEngineHandlerMapping)

    def _get_field_config(self) -> dict:
        """
        定义 EngineHandlerMapping 数据的字段配置
        
        Returns:
            dict: 字段配置字典
        """
        return {
            'engine_id': {'type': 'string', 'min': 1},
            'handler_id': {'type': 'string', 'min': 1}
            # priority、is_active、source字段已移除 - 模型中不存在这些字段
        }

    def _create_from_params(self, **kwargs) -> MEngineHandlerMapping:
        """
        Hook method: Create MEngineHandlerMapping from parameters.
        """
        return MEngineHandlerMapping(
            engine_id=kwargs.get("engine_id"),
            handler_id=kwargs.get("handler_id"),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MEngineHandlerMapping]:
        """
        Hook method: Convert mapping objects to MEngineHandlerMapping.
        """
        if hasattr(item, 'engine_id') and hasattr(item, 'handler_id'):
            return MEngineHandlerMapping(
                engine_id=getattr(item, 'engine_id'),
                handler_id=getattr(item, 'handler_id'),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _convert_output_items(self, items: List[MEngineHandlerMapping], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MEngineHandlerMapping objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_engine(self, engine_id: str,
                      as_dataframe: bool = False) -> Union[List[MEngineHandlerMapping], pd.DataFrame]:
        """
        Business helper: Find handler mappings by engine ID.
        """
        filters = {"engine_id": engine_id}
        
        return self.find(filters=filters, order_by="uuid",
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_handler(self, handler_id: str,
                       as_dataframe: bool = False) -> Union[List[MEngineHandlerMapping], pd.DataFrame]:
        """
        Business helper: Find engine mappings by handler ID.
        """
        filters = {"handler_id": handler_id}
        
        return self.find(filters=filters, order_by="uuid",
                        as_dataframe=as_dataframe, output_type="model")

    def get_handlers_for_engine(self, engine_id: str) -> List[str]:
        """
        Business helper: Get all handler IDs for an engine.
        """
        mappings = self.find_by_engine(engine_id, as_dataframe=False)
        return [m.handler_id for m in mappings if m.handler_id]

    def get_engines_for_handler(self, handler_id: str) -> List[str]:
        """
        Business helper: Get all engine IDs for a handler.
        """
        mappings = self.find_by_handler(handler_id, as_dataframe=False)
        return [m.engine_id for m in mappings if m.engine_id]

