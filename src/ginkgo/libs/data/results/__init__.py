# Upstream: All Modules
# Downstream: Standard Library
# Role: 结果类模块导出数据验证/数据同步/数据完整性等服务结果类支持交易系统功能封装服务返回结果提供统一的返回格式






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