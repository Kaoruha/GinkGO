# Upstream: All Modules
# Downstream: Standard Library
# Role: 数据工具模块导出时间规范化/数字处理/费用计算/统计检验等数据处理工具支持交易系统功能和组件集成提供完整业务支持






"""
Data processing utilities for Ginkgo library
"""

from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.libs.data.number import Number, to_decimal
from ginkgo.libs.data.statistics import t_test, chi2_test
from ginkgo.libs.data.math import cal_fee
from ginkgo.libs.data.results import (
    DataValidationResult,
    DataIntegrityCheckResult,
    DataSyncResult
)

__all__ = [
    "datetime_normalize",
    "Number", "to_decimal",
    "t_test", "chi2_test",
    "cal_fee",
    "DataValidationResult",
    "DataIntegrityCheckResult",
    "DataSyncResult"
]