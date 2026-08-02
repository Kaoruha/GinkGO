# Upstream: ParamService (参数管理业务服务)、ComponentParameterExtractor (组件参数提取和存储)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MParam (MySQL参数模型)、SOURCE_TYPES (数据源枚举SIM/LIVE/BACKTEST/OTHER)
# Role: ParamCRUD参数CRUD操作继承BaseCRUD提供参数配置增删改查和查询功能






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Any, Dict
import pandas as pd

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MParam
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG, cache_with_expiration


@restrict_crud_access
class ParamCRUD(BaseCRUD[MParam]):
    """
    Param CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MParam

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

    # ADR-029 §Decision 1：转换钩子 override 已退役。
    # 调用方 mapping_service.add_batch:575 / deployment_service.add:509 均传 MParam 实例。

    # Business Helper Methods
    def find_by_mapping_id(self, mapping_id: str) -> list:
        """
        Business helper: Find parameter by mapping ID.
        """
        return self.find(filters={"mapping_id": mapping_id}, order_by="index")

    def find_by_index_range(self, mapping_id: str, min_index: int, max_index: int) -> list:
        """
        Business helper: Find parameters by index range.
        """
        filters = {
            "mapping_id": mapping_id,
            "index__gte": min_index,
            "index__lte": max_index
        }
        return self.find(filters=filters, order_by="index")

    def find_by_value_pattern(self, value_pattern: str) -> list:
        """
        Business helper: Find parameters by value pattern.
        """
        return self.find(filters={"value__like": value_pattern}, order_by="update_at", desc_order=True)

    def get_param_value(self, mapping_id: str, index: int, default_value: str = "") -> str:
        """
        Business helper: Get parameter value by mapping ID and index.
        """
        result = self.find(filters={"mapping_id": mapping_id, "index": index})
        if result:
            return result[0].value or default_value
        return default_value

    def set_param_value(self, mapping_id: str, index: int, value: str, source: SOURCE_TYPES = SOURCE_TYPES.SIM) -> None:
        """
        Business helper: Set parameter value (upsert).
        """
        existing = self.find(filters={"mapping_id": mapping_id, "index": index})
        if existing:
            self.modify({"mapping_id": mapping_id, "index": index}, {"value": value})
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

