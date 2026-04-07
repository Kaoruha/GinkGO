# Upstream: 数据模块(__init__.py)、各CRUD/Service模块 (使用结果类封装返回)
# Downstream: DataValidationResult, DataIntegrityCheckResult, DataSyncResult
# Role: 数据结果类包入口，导出验证/完整性检查/同步三种通用结果类，提供统一的服务返回格式






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
