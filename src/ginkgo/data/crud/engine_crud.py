# Upstream: EngineService (引擎业务服务)、EngineFactory (创建和查询引擎配置)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MEngine (MySQL引擎模型)、ENGINESTATUS_TYPES/ATTITUDE_TYPES (引擎状态和Broker态度枚举)
# Role: EngineCRUD引擎CRUD操作继承BaseCRUD提供引擎配置管理功能






from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MEngine
from ginkgo.enums import SOURCE_TYPES, ENGINESTATUS_TYPES, ATTITUDE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access
from sqlalchemy.orm import Session


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
            # 时间范围字段 - 可选的日期时间
            "backtest_start_date": {"type": "datetime", "required": False},
            "backtest_end_date": {"type": "datetime", "required": False},
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

        # 处理broker_attitude字段
        broker_attitude_value = kwargs.get("broker_attitude", ATTITUDE_TYPES.OPTIMISTIC)
        if isinstance(broker_attitude_value, ATTITUDE_TYPES):
            broker_attitude_value = broker_attitude_value.value
        else:
            broker_attitude_value = ATTITUDE_TYPES.validate_input(broker_attitude_value) or 2

        return MEngine(
            name=kwargs.get("name", "test_engine"),
            status=status_value,
            is_live=kwargs.get("is_live", False),
            source=source_value,
            config_hash=kwargs.get("config_hash", ""),
            current_run_id=kwargs.get("current_run_id", ""),
            run_count=kwargs.get("run_count", 0),
            config_snapshot=kwargs.get("config_snapshot", "{}"),
            backtest_start_date=kwargs.get("backtest_start_date"),
            backtest_end_date=kwargs.get("backtest_end_date"),
            broker_attitude=broker_attitude_value
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
                broker_attitude=ATTITUDE_TYPES.validate_input(getattr(item, "broker_attitude", ATTITUDE_TYPES.OPTIMISTIC)),
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
    def find_by_uuid(self, uuid: str) -> List[MEngine]:
        """
        Business helper: Find engine by UUID.
        """
        return self.find(filters={"uuid": uuid}, page_size=1)

    def find_by_status(
        self, status: ENGINESTATUS_TYPES
    ) -> List[MEngine]:
        """
        Business helper: Find engines by status.
        """
        return self.find(
            filters={"status": status},
            order_by="update_at",
            desc_order=True,
            output_type="model",
        )

    def find_by_name_pattern(self, name_pattern: str) -> List[MEngine]:
        """
        Business helper: Find engines by name pattern.
        """
        return self.find(
            filters={"name__like": name_pattern},
            order_by="update_at",
            desc_order=True,
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

    def fuzzy_search(
        self,
        query: str,
        fields: Optional[List[str]] = None
    ) -> ModelList[MEngine]:
        """
        Fuzzy search engines across multiple fields with OR logic.

        This method uses multiple separate queries and combines results to avoid
        SQLAlchemy session issues while providing OR-like functionality.

        Supports intelligent string matching for:
        - UUID: Partial UUID match
        - Name: Partial name match (case-insensitive)
        - Type: "backtest"/"live" → is_live bool field
        - Status: String names like "live"/"running" → ENGINESTATUS_TYPES values

        Args:
            query: Search string
            fields: Fields to search in. Default: ['uuid', 'name', 'is_live', 'status']

        Returns:
            ModelList of matching engines
        """
        if not query or not query.strip():
            return ModelList([], self)

        from ginkgo.libs import GLOG

        query_lower = query.lower().strip()

        # Default fields to search
        if fields is None:
            fields = ['uuid', 'name', 'is_live', 'status']

        all_results = []
        seen_uuids = set()

        # UUID search - partial match
        if 'uuid' in fields:
            try:
                results = self.find(filters={"uuid__like": f"%{query_lower}%", "is_del": False})
                if hasattr(results, '__iter__'):
                    for item in results:
                        if hasattr(item, 'uuid') and item.uuid not in seen_uuids:
                            all_results.append(item)
                            seen_uuids.add(item.uuid)
            except Exception as e:
                GLOG.WARN(f"UUID fuzzy search failed: {e}")

        # Name search - partial match
        if 'name' in fields:
            try:
                results = self.find(filters={"name__like": f"%{query_lower}%", "is_del": False})
                if hasattr(results, '__iter__'):
                    for item in results:
                        if hasattr(item, 'uuid') and item.uuid not in seen_uuids:
                            all_results.append(item)
                            seen_uuids.add(item.uuid)
            except Exception as e:
                GLOG.WARN(f"Name fuzzy search failed: {e}")

        # Type search - map "backtest"/"live" to is_live boolean
        if 'is_live' in fields:
            try:
                if query_lower in ['live', 'real', 'production']:
                    results = self.find(filters={"is_live": True, "is_del": False})
                elif query_lower in ['backtest', 'test', 'simulation', 'sim']:
                    results = self.find(filters={"is_live": False, "is_del": False})
                else:
                    results = []

                if hasattr(results, '__iter__'):
                    for item in results:
                        if hasattr(item, 'uuid') and item.uuid not in seen_uuids:
                            all_results.append(item)
                            seen_uuids.add(item.uuid)
            except Exception as e:
                GLOG.WARN(f"Type fuzzy search failed: {e}")

        # Status search - map string names to ENGINESTATUS_TYPES values
        if 'status' in fields:
            status_matches = []

            # Map common status strings to enum values
            status_mappings = {
                'idle': ENGINESTATUS_TYPES.IDLE.value,
                'initial': ENGINESTATUS_TYPES.INITIALIZING.value,
                'initializing': ENGINESTATUS_TYPES.INITIALIZING.value,
                'init': ENGINESTATUS_TYPES.INITIALIZING.value,
                'run': ENGINESTATUS_TYPES.RUNNING.value,
                'running': ENGINESTATUS_TYPES.RUNNING.value,
                'pause': ENGINESTATUS_TYPES.PAUSED.value,
                'paused': ENGINESTATUS_TYPES.PAUSED.value,
                'stop': ENGINESTATUS_TYPES.STOPPED.value,
                'stopped': ENGINESTATUS_TYPES.STOPPED.value,
            }

            # Find matching status values
            for key, value in status_mappings.items():
                if key in query_lower:
                    status_matches.append(value)

            # Also try exact enum name matching
            try:
                # Remove ENGINESTATUS_TYPES prefix if present
                clean_query = query_lower.replace('enginestatus_types.', '')
                enum_value = ENGINESTATUS_TYPES.validate_input(clean_query.upper())
                if enum_value is not None:
                    status_matches.append(enum_value.value)
            except Exception as e:
                GLOG.ERROR(f"Failed to parse engine status query '{query_lower}': {e}")

            # Search for each matching status
            if status_matches:
                try:
                    # Use IN operator to search for multiple status values
                    results = self.find(filters={"status__in": status_matches, "is_del": False})
                    if hasattr(results, '__iter__'):
                        for item in results:
                            if hasattr(item, 'uuid') and item.uuid not in seen_uuids:
                                all_results.append(item)
                                seen_uuids.add(item.uuid)
                except Exception as e:
                    GLOG.WARN(f"Status fuzzy search failed: {e}")

        # Return ModelList for consistency with other CRUD methods
        return ModelList(all_results, self)

