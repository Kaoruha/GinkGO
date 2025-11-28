"""
通用数据同步结果类
用于所有数据类型的同步操作统一返回格式
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime


@dataclass
class DataSyncResult:
    """通用数据同步结果"""

    # 同步实体信息
    entity_type: str    # "bars", "ticks", "stockinfo", "orders" 等
    entity_identifier: str  # 具体实体标识，如股票代码
    sync_range: Tuple[Optional[datetime], Optional[datetime]]

    # 同步统计
    records_processed: int
    records_added: int
    records_updated: int
    records_skipped: int  # 已存在，跳过
    records_failed: int

    # 同步元信息
    sync_duration: float
    is_idempotent: bool
    sync_strategy: str  # "full", "incremental", "fast"

    # 错误和警告
    errors: List[Tuple[int, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # 扩展元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, row_index: int, error_message: str):
        """添加错误信息"""
        self.errors.append((row_index, error_message))

    def add_warning(self, warning_message: str):
        """添加警告信息"""
        self.warnings.append(warning_message)

    def set_metadata(self, key: str, value: Any):
        """设置实体特定的元数据"""
        self.metadata[key] = value

    def get_success_rate(self) -> float:
        """计算成功率"""
        if self.records_processed == 0:
            return 0.0
        return (self.records_added + self.records_updated) / self.records_processed

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0 or self.records_failed > 0

    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def is_successful(self) -> bool:
        """是否成功（无错误）"""
        return not self.has_errors()

    def get_total_changes(self) -> int:
        """获取总变更记录数"""
        return self.records_added + self.records_updated

    def get_efficiency_score(self) -> float:
        """获取同步效率评分 (0-100)"""
        if self.records_processed == 0:
            return 100.0

        # 基础效率分数
        efficiency = self.get_success_rate() * 100

        # 跳过记录表示高效幂等性，加分
        if self.records_skipped > 0:
            skip_ratio = self.records_skipped / self.records_processed
            efficiency += skip_ratio * 20  # 最多加20分

        # 错误记录减分
        if self.records_failed > 0:
            error_ratio = self.records_failed / self.records_processed
            efficiency -= error_ratio * 50  # 最多减50分

        return max(0.0, min(100.0, efficiency))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        sync_range_str = (
            (self.sync_range[0].isoformat() if self.sync_range[0] else None,
             self.sync_range[1].isoformat() if self.sync_range[1] else None)
        )

        return {
            "entity_type": self.entity_type,
            "entity_identifier": self.entity_identifier,
            "sync_range": sync_range_str,
            "records_processed": self.records_processed,
            "records_added": self.records_added,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "records_failed": self.records_failed,
            "sync_duration": self.sync_duration,
            "is_idempotent": self.is_idempotent,
            "sync_strategy": self.sync_strategy,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "success_rate": self.get_success_rate(),
            "efficiency_score": self.get_efficiency_score(),
            "is_successful": self.is_successful()
        }

    @classmethod
    def create_for_entity(
        cls,
        entity_type: str,
        entity_identifier: str,
        sync_range: Tuple[Optional[datetime], Optional[datetime]] = (None, None),
        sync_strategy: str = "incremental"
    ) -> 'DataSyncResult':
        """为特定实体创建同步结果实例"""
        return cls(
            entity_type=entity_type,
            entity_identifier=entity_identifier,
            sync_range=sync_range,
            records_processed=0,
            records_added=0,
            records_updated=0,
            records_skipped=0,
            records_failed=0,
            sync_duration=0.0,
            is_idempotent=False,
            sync_strategy=sync_strategy
        )

    def __str__(self) -> str:
        """字符串表示"""
        status = "成功" if self.is_successful() else "失败"
        return (
            f"{self.entity_type}({self.entity_identifier}) 同步{status}: "
            f"处理{self.records_processed}条, "
            f"新增{self.records_added}条, "
            f"更新{self.records_updated}条, "
            f"跳过{self.records_skipped}条, "
            f"失败{self.records_failed}条"
        )