from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MEngine
from ...enums import SOURCE_TYPES, ENGINESTATUS_TYPES
from ...libs import datetime_normalize, GLOG, cache_with_expiration
from ..access_control import restrict_crud_access


@restrict_crud_access
class EngineCRUD(BaseCRUD[MEngine]):
    """
    Engine CRUD operations.
    """

    def __init__(self):
        super().__init__(MEngine)

    def _get_field_config(self) -> dict:
        """
        定义 Engine 数据的字段配置 - 必填字段验证

        Returns:
            dict: 字段配置字典
        """
        return {
            # 引擎名称 - 非空字符串
            "name": {"type": "string", "min": 1, "max": 100},  # 限制名称长度
            # status字段移除验证配置，使用模型默认值 ENGINESTATUS_TYPES.IDLE
            # source字段移除验证配置，使用模型默认值 SOURCE_TYPES.SIM
            # 是否实时交易 - 布尔值
            "is_live": {"type": "bool"},
        }

    def _create_from_params(self, **kwargs) -> MEngine:
        """
        Hook method: Create MEngine from parameters.
        """
        return MEngine(
            name=kwargs.get("name", "test_engine"),
            status=kwargs.get("status", ENGINESTATUS_TYPES.IDLE),
            is_live=kwargs.get("is_live", False),
            source=kwargs.get("source", SOURCE_TYPES.SIM),
        )

    def _convert_input_item(self, item: Any) -> Optional[MEngine]:
        """
        Hook method: Convert engine objects to MEngine.
        """
        if hasattr(item, "name"):
            return MEngine(
                name=getattr(item, "name", "test_engine"),
                status=getattr(item, "status", ENGINESTATUS_TYPES.IDLE),
                is_live=getattr(item, "is_live", False),
                source=getattr(item, "source", SOURCE_TYPES.SIM),
            )
        return None

    def _convert_output_items(self, items: List[MEngine], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MEngine objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_uuid(self, uuid: str, as_dataframe: bool = False) -> Union[List[MEngine], pd.DataFrame]:
        """
        Business helper: Find engine by UUID.
        """
        return self.find(filters={"uuid": uuid}, page_size=1, as_dataframe=as_dataframe, output_type="model")

    def find_by_status(
        self, status: ENGINESTATUS_TYPES, as_dataframe: bool = False
    ) -> Union[List[MEngine], pd.DataFrame]:
        """
        Business helper: Find engines by status.
        """
        return self.find(
            filters={"status": status},
            order_by="update_at",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model",
        )

    def find_by_name_pattern(self, name_pattern: str, as_dataframe: bool = False) -> Union[List[MEngine], pd.DataFrame]:
        """
        Business helper: Find engines by name pattern.
        """
        return self.find(
            filters={"name__like": name_pattern},
            order_by="update_at",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model",
        )

    def get_all_uuids(self) -> List[str]:
        """
        Business helper: Get all distinct engine UUIDs.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            engine_uuids = self.find(distinct_field="uuid")
            return [eid for eid in engine_uuids if eid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get engine uuids: {e}")
            return []

    def get_engine_statuses(self) -> List[ENGINESTATUS_TYPES]:
        """
        Business helper: Get all distinct engine statuses.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            engine_statuses = self.find(distinct_field="status")
            return [estatus for estatus in engine_statuses if estatus]
        except Exception as e:
            GLOG.ERROR(f"Failed to get engine statuses: {e}")
            return []

    def delete_by_uuid(self, uuid: str, session=None) -> None:
        """
        Business helper: Delete engine by UUID.
        """
        if not uuid:
            raise ValueError("uuid不能为空")

        GLOG.WARN(f"删除引擎 {uuid}")
        return self.remove({"uuid": uuid}, session)

    def update_status(self, uuid: str, status: ENGINESTATUS_TYPES) -> None:
        """
        Update engine status.
        """
        return self.modify({"uuid": uuid}, {"status": status})
