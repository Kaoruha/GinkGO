# Upstream: libs顶层模块(__init__.py)、各业务模块
# Downstream: datetime_normalize, Number/to_decimal, t_test/chi2_test, cal_fee, DataValidationResult/DataIntegrityCheckResult/DataSyncResult
# Role: 数据工具包入口，导出时间标准化/数字处理/费用计算/统计检验和数据结果类等通用数据处理工具






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
