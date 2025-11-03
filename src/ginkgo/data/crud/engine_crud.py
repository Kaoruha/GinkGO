from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MEngine
from ginkgo.enums import SOURCE_TYPES, ENGINESTATUS_TYPES
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class EngineCRUD(BaseCRUD[MEngine]):
    """
    Engine CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MEngine

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
            # status字段 - 枚举类型，由验证器处理转换
            "status": {
                "type": "ENGINESTATUS_TYPES",  # 使用枚举类型名称
                "default": ENGINESTATUS_TYPES.IDLE.value
            },
            # source字段 - 枚举类型，由验证器处理转换
            "source": {
                "type": "SOURCE_TYPES",  # 使用枚举类型名称
                "default": SOURCE_TYPES.SIM.value
            },
            # 是否实时交易 - 布尔值
            "is_live": {"type": "bool"},
            # run_count字段 - 正整数，最小值0
            "run_count": {
                "type": "int",
                "min": 0
            },
            # config_hash字段 - 字符串
            "config_hash": {"type": "string"},
            # current_run_id字段 - 字符串
            "current_run_id": {"type": "string"},
            # config_snapshot字段 - 字符串
            "config_snapshot": {"type": "string"},
        }

    def _create_from_params(self, **kwargs) -> MEngine:
        """
        Hook method: Create MEngine from parameters.
        """
        # 处理枚举字段，确保插入数据库的是数值
        status_value = kwargs.get("status", ENGINESTATUS_TYPES.IDLE)
        if isinstance(status_value, ENGINESTATUS_TYPES):
            status_value = status_value.value
        else:
            status_value = ENGINESTATUS_TYPES.validate_input(status_value)

        source_value = kwargs.get("source", SOURCE_TYPES.SIM)
        if isinstance(source_value, SOURCE_TYPES):
            source_value = source_value.value
        else:
            source_value = SOURCE_TYPES.validate_input(source_value)

        return MEngine(
            name=kwargs.get("name", "test_engine"),
            status=status_value,
            is_live=kwargs.get("is_live", False),
            source=source_value,
            config_hash=kwargs.get("config_hash", ""),
            current_run_id=kwargs.get("current_run_id", ""),
            run_count=kwargs.get("run_count", 0),
            config_snapshot=kwargs.get("config_snapshot", "{}"),
        )

    def _convert_input_item(self, item: Any) -> Optional[MEngine]:
        """
        Hook method: Convert engine objects to MEngine.
        """
        if hasattr(item, "name"):
            return MEngine(
                name=getattr(item, "name", "test_engine"),
                status=ENGINESTATUS_TYPES.validate_input(getattr(item, "status", ENGINESTATUS_TYPES.IDLE)),
                is_live=getattr(item, "is_live", False),
                source=SOURCE_TYPES.validate_input(getattr(item, "source", SOURCE_TYPES.SIM)),
                config_hash=getattr(item, "config_hash", ""),
                current_run_id=getattr(item, "current_run_id", ""),
                run_count=getattr(item, "run_count", 0),
                config_snapshot=getattr(item, "config_snapshot", "{}"),
            )
        return None


    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'status': ENGINESTATUS_TYPES,
            'source': SOURCE_TYPES
        }

    def _convert_models_to_business_objects(self, models: List) -> List:
        """
        🎯 Convert models to business objects.

        Args:
            models: List of models with enum fields already fixed

        Returns:
            List of models (business object doesn't exist yet)
        """
        # For now, return models as-is since business object doesn't exist yet
        return models

    def _convert_output_items(self, items: List, output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert objects for business layer.
        """
        return items

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
