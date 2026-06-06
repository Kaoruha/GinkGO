# Upstream: 数据同步 API (update_data), 数据概览页 (sync/history)
# Downstream: BaseService (继承), DataSyncRecordCRUD (数据访问)
# Role: 数据同步记录业务服务，提供同步开始记录、完成更新、历史查询

"""
Data Sync Record Service

数据同步记录的业务服务层，封装 CRUD 操作并提供业务语义接口。
"""

from typing import Optional, Dict, Any

from ginkgo.data.services.base_service import BaseService, ServiceResult


class DataSyncRecordService(BaseService):
    """
    数据同步记录服务

    提供：
    - record_start: 记录同步开始
    - record_complete: 更新同步结果
    - record_fail: 更新为失败状态
    - get_history: 分页查询同步历史
    """

    def record_start(
        self,
        sync_type: str,
        code: str,
    ) -> ServiceResult:
        """
        记录同步开始

        Args:
            sync_type: 同步类型 (stockinfo/bars/ticks/adjustfactor)
            code: 股票代码，stockinfo 用 "ALL"

        Returns:
            ServiceResult: 包含 uuid 和 status
        """
        try:
            record = self._crud_repo.record_start(
                sync_type=sync_type,
                code=code,
            )
            if record:
                return ServiceResult.success(
                    data={"uuid": record.uuid, "status": record.status},
                    message=f"Sync start recorded for {sync_type}/{code}",
                )
            return ServiceResult.error("Failed to record sync start")
        except Exception as e:
            return ServiceResult.error(f"Failed to record sync start: {str(e)}")

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
    ) -> ServiceResult:
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
            ServiceResult
        """
        try:
            success = self._crud_repo.record_complete(
                uuid=uuid,
                status=status,
                duration_ms=duration_ms,
                records_processed=records_processed,
                records_added=records_added,
                records_updated=records_updated,
                records_failed=records_failed,
                error_message=error_message,
                sync_strategy=sync_strategy,
            )
            if success:
                return ServiceResult.success(
                    data={"uuid": uuid, "status": status},
                    message=f"Sync record updated to {status}",
                )
            return ServiceResult.error("Failed to complete sync record")
        except Exception as e:
            return ServiceResult.error(f"Failed to complete sync record: {str(e)}")

    def record_fail(
        self,
        uuid: str,
        error_message: str,
    ) -> ServiceResult:
        """
        更新同步记录为失败状态

        Args:
            uuid: 记录 ID
            error_message: 失败原因

        Returns:
            ServiceResult
        """
        return self.record_complete(
            uuid=uuid,
            status="failed",
            error_message=error_message,
        )

    def get_history(
        self,
        sync_type: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> ServiceResult:
        """
        分页查询同步历史

        Args:
            sync_type: 按类型筛选 (可选)
            page: 页码（从 0 开始）
            page_size: 每页数量

        Returns:
            ServiceResult: {"items": [...], "total": N}
        """
        try:
            items = self._crud_repo.find_recent(
                sync_type=sync_type,
                page=page,
                page_size=page_size,
            )
            total = self._crud_repo.count(
                filters={"sync_type": sync_type} if sync_type else {},
            )

            data = []
            for item in items:
                data.append({
                    "uuid": item.uuid,
                    "sync_type": item.sync_type,
                    "code": item.code,
                    "status": item.status,
                    "started_at": item.started_at.isoformat() if item.started_at else None,
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                    "duration_ms": item.duration_ms,
                    "records_processed": item.records_processed,
                    "records_added": item.records_added,
                    "records_updated": item.records_updated,
                    "records_failed": item.records_failed,
                    "error_message": item.error_message,
                    "sync_strategy": item.sync_strategy,
                })

            return ServiceResult.success(
                data={"items": data, "total": total},
                message=f"Found {total} sync records",
            )
        except Exception as e:
            return ServiceResult.error(f"Failed to get sync history: {str(e)}")
