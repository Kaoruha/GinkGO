from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd

from .base_crud import BaseCRUD
from ..models import MParam
from ...enums import SOURCE_TYPES
from ...libs import GLOG, cache_with_expiration


@restrict_crud_access
class ParamCRUD(BaseCRUD[MParam]):
    """
    Param CRUD operations.
    """

    def __init__(self):
        super().__init__(MParam)

    def _get_field_config(self) -> dict:
        """
        定义 Param 数据的字段配置
        
        Returns:
            dict: 字段配置字典
        """
        return {
            'mapping_id': {'type': 'string', 'min': 1},
            'index': {'type': 'int', 'min': 0},
            'value': {'type': 'string'}
            # source字段已移除 - 使用模型默认值 SOURCE_TYPES.OTHER
        }

    def _create_from_params(self, **kwargs) -> MParam:
        """
        Hook method: Create MParam from parameters.
        """
        return MParam(
            mapping_id=kwargs.get("mapping_id", ""),
            index=kwargs.get("index", 0),
            value=kwargs.get("value", ""),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MParam]:
        """
        Hook method: Convert param objects to MParam.
        """
        if hasattr(item, 'mapping_id'):
            return MParam(
                mapping_id=getattr(item, 'mapping_id', ''),
                index=getattr(item, 'index', 0),
                value=getattr(item, 'value', ''),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _convert_output_items(self, items: List[MParam], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MParam objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_mapping_id(self, mapping_id: str, as_dataframe: bool = False) -> Union[List[MParam], pd.DataFrame]:
        """
        Business helper: Find parameter by mapping ID.
        """
        return self.find(filters={"mapping_id": mapping_id}, order_by="index",
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_index_range(self, mapping_id: str, min_index: int, max_index: int,
                           as_dataframe: bool = False) -> Union[List[MParam], pd.DataFrame]:
        """
        Business helper: Find parameters by index range.
        """
        filters = {
            "mapping_id": mapping_id,
            "index__gte": min_index,
            "index__lte": max_index
        }
        return self.find(filters=filters, order_by="index",
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_value_pattern(self, value_pattern: str, as_dataframe: bool = False) -> Union[List[MParam], pd.DataFrame]:
        """
        Business helper: Find parameters by value pattern.
        """
        return self.find(filters={"value__like": value_pattern}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def get_param_value(self, mapping_id: str, index: int, default_value: str = "") -> str:
        """
        Business helper: Get parameter value by mapping ID and index.
        """
        result = self.find(filters={"mapping_id": mapping_id, "index": index}, as_dataframe=False)
        if result:
            return result[0].value or default_value
        return default_value

    def set_param_value(self, mapping_id: str, index: int, value: str, source: SOURCE_TYPES = SOURCE_TYPES.SIM) -> None:
        """
        Business helper: Set parameter value.
        """
        existing = self.find(filters={"mapping_id": mapping_id, "index": index}, as_dataframe=False)
        if existing:
            return self.modify({"mapping_id": mapping_id, "index": index}, {"value": value})
        else:
            self.create(mapping_id=mapping_id, index=index, value=value, source=source)

    def get_all_mapping_ids(self) -> List[str]:
        """
        Business helper: Get all distinct mapping IDs.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            mapping_ids = self.find(distinct_field="mapping_id")
            return [mid for mid in mapping_ids if mid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get mapping ids: {e}")
            return []

    def delete_by_uuid(self, uuid: str) -> None:
        """
        Delete parameter by UUID.
        """
        if not uuid:
            raise ValueError("uuid不能为空")
        
        GLOG.WARN(f"删除参数 {uuid}")
        return self.remove({"uuid": uuid})

    def update_value(self, uuid: str, value: str) -> None:
        """
        Update parameter value.
        """
        return self.modify({"uuid": uuid}, {"value": value})
