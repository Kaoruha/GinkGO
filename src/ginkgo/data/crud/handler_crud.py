from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MHandler
from ...enums import SOURCE_TYPES
from ...libs import GLOG


@restrict_crud_access
class HandlerCRUD(BaseCRUD[MHandler]):
    """
    Handler CRUD operations.
    """

    def __init__(self):
        super().__init__(MHandler)

    def _get_field_config(self) -> dict:
        """
        定义 Handler 数据的字段配置 - 只验证必需字段
        
        Returns:
            dict: 字段配置字典
        """
        return {
            'name': {'type': 'string', 'min': 1, 'max': 32}
        }

    def _create_from_params(self, **kwargs) -> MHandler:
        """
        Hook method: Create MHandler from parameters.
        """
        return MHandler(
            name=kwargs.get("name", "test_handler"),
            lib_path=kwargs.get("lib_path", ""),
            func_name=kwargs.get("func_name", ""),
            source=kwargs.get("source", SOURCE_TYPES.SIM),
        )

    def _convert_input_item(self, item: Any) -> Optional[MHandler]:
        """
        Hook method: Convert handler objects to MHandler.
        """
        if hasattr(item, 'name'):
            return MHandler(
                name=getattr(item, 'name', 'test_handler'),
                lib_path=getattr(item, 'lib_path', ''),
                func_name=getattr(item, 'func_name', ''),
                source=getattr(item, 'source', SOURCE_TYPES.SIM),
            )
        return None

    def _convert_output_items(self, items: List[MHandler], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MHandler objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_uuid(self, uuid: str, as_dataframe: bool = False) -> Union[List[MHandler], pd.DataFrame]:
        """
        Business helper: Find handler by UUID.
        """
        return self.find(filters={"uuid": uuid}, page_size=1,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_name_pattern(self, name_pattern: str, as_dataframe: bool = False) -> Union[List[MHandler], pd.DataFrame]:
        """
        Business helper: Find handlers by name pattern.
        """
        return self.find(filters={"name__like": name_pattern}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_lib_path(self, lib_path: str, as_dataframe: bool = False) -> Union[List[MHandler], pd.DataFrame]:
        """
        Business helper: Find handlers by library path.
        """
        return self.find(filters={"lib_path": lib_path}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def get_all_uuids(self) -> List[str]:
        """
        Business helper: Get all distinct handler UUIDs.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            handler_uuids = self.find(distinct_field="uuid")
            return [huid for huid in handler_uuids if huid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get handler uuids: {e}")
            return []

    def delete_by_uuid(self, uuid: str) -> None:
        """
        Delete handler by UUID.
        """
        if not uuid:
            raise ValueError("uuid不能为空")
        
        GLOG.WARN(f"删除处理器 {uuid}")
        return self.remove({"uuid": uuid})

    def update_lib_path(self, uuid: str, lib_path: str) -> None:
        """
        Update handler library path.
        """
        return self.modify({"uuid": uuid}, {"lib_path": lib_path})

    def update_func_name(self, uuid: str, func_name: str) -> None:
        """
        Update handler function name.
        """
        return self.modify({"uuid": uuid}, {"func_name": func_name})
