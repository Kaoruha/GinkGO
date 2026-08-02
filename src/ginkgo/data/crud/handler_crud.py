# Upstream: EngineCRUD, 引擎装配层
# Downstream: BaseCRUD, MHandler模型
# Role: 处理器(Handler)配置CRUD，管理自定义处理器(信号/风控等)的注册和查询






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MHandler
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG


@restrict_crud_access
class HandlerCRUD(BaseCRUD[MHandler]):
    """
    Handler CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MHandler

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
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    # Business Helper Methods
    def find_by_uuid(self, uuid: str) -> List[MHandler]:
        """
        Business helper: Find handler by UUID.
        """
        return self.find(filters={"uuid": uuid}, page_size=1)

    def find_by_name_pattern(self, name_pattern: str) -> List[MHandler]:
        """
        Business helper: Find handlers by name pattern.
        """
        return self.find(filters={"name__like": name_pattern}, order_by="update_at", desc_order=True)

    def find_by_lib_path(self, lib_path: str) -> List[MHandler]:
        """
        Business helper: Find handlers by library path.
        """
        return self.find(filters={"lib_path": lib_path}, order_by="update_at", desc_order=True)

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

