"""
通用数据结果模块
提供数据验证、完整性检查和同步结果的通用类
"""

from .data_validation_result import DataValidationResult
from .data_integrity_result import DataIntegrityCheckResult
from .data_sync_result import DataSyncResult

__all__ = [
    'DataValidationResult',
    'DataIntegrityCheckResult',
    'DataSyncResult'
]