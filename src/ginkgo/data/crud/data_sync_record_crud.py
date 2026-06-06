# Upstream: DataSyncRecordService (同步记录业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力), MDataSyncRecord (MySQL同步记录模型)
# Role: DataSyncRecordCRUD 数据同步记录CRUD，提供同步开始、完成更新、历史查询

"""
Data Sync Record CRUD Operations

数据同步记录的增删改查操作，支持同步生命周期追踪（running → success/partial/failed）。
"""

from typing import Optional, Dict, Any
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MDataSyncRecord
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class DataSyncRecordCRUD(BaseCRUD[MDataSyncRecord]):
    """
    数据同步记录 CRUD

    支持：
    - 记录同步开始 (INSERT running)
    - 更新同步结果 (UPDATE success/partial/failed)
    - 按条件查询同步历史
    """

    _model_class = MDataSyncRecord

    def __init__(self):
        super().__init__(MDataSyncRecord)

    def _get_field_config(self) -> dict:
        return {}

    def _create_from_params(self, **kwargs) -> MDataSyncRecord:
        model = MDataSyncRecord()
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        return model

    def record_start(
        self,
        sync_type: str,
        code: str,
    ) -> Optional[MDataSyncRecord]:
        """
        记录同步开始，创建 running 记录

        Args:
            sync_type: 同步类型 (stockinfo/bars/ticks/adjustfactor)
            code: 股票代码，stockinfo 用 "ALL"

        Returns:
            创建的记录（含 uuid），失败返回 None
        """
        try:
            model = MDataSyncRecord()
            model.sync_type = sync_type
            model.code = code
            model.status = "running"
            model.started_at = datetime.now()
            self.add(model)
            return model
        except Exception as e:
            GLOG.ERROR(f"Failed to record sync start for {sync_type}/{code}: {e}")
            return None

    def record_complete(
        self,
        uuid: str,
        status: str,
        duration_ms: int = 0,
        records_processed: int = 0,
        records_added: int = 0,
        records_updated: int = 0,
        records_failed: int = 0,
        error_message: Optional[str] = None,
        sync_strategy: str = "",
    ) -> bool:
        """
        更新同步记录为完成状态

        Args:
            uuid: 记录 ID
            status: success / partial / failed
            duration_ms: 耗时毫秒
            records_*: 同步统计
            error_message: 失败原因
            sync_strategy: 同步策略

        Returns:
            是否更新成功
        """
        try:
            self.modify(
                filters={"uuid": uuid},
                updates={
                    "status": status,
                    "completed_at": datetime.now(),
                    "duration_ms": duration_ms,
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "records_updated": records_updated,
                    "records_failed": records_failed,
                    "error_message": error_message,
                    "sync_strategy": sync_strategy,
                },
            )
            return True
        except Exception as e:
            GLOG.ERROR(f"Failed to complete sync record {uuid}: {e}")
            return False

    def record_fail(
        self,
        uuid: str,
        error_message: str,
    ) -> bool:
        """
        更新同步记录为失败状态

        Args:
            uuid: 记录 ID
            error_message: 失败原因

        Returns:
            是否更新成功
        """
        return self.record_complete(
            uuid=uuid,
            status="failed",
            error_message=error_message,
        )

    def find_recent(
        self,
        sync_type: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> ModelList:
        """查询最近的同步记录，按开始时间倒序"""
        filters: Dict[str, Any] = {}
        if sync_type:
            filters["sync_type"] = sync_type
        return self.find(
            filters=filters,
            order_by="started_at",
            desc_order=True,
            page=page,
            page_size=page_size,
        )

    def count_by_status(self, status: str) -> int:
        """按状态统计数量"""
        return self.count(filters={"status": status})
