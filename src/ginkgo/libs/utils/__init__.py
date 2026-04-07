# Upstream: libs顶层模块(__init__.py)、各业务模块
# Downstream: common(try_wait_counter/str2bool/time_logger/retry/cache_with_expiration/RichProgress), display(pretty_repr/base_repr/GinkgoColor), codes(cn_index), process(find_process_by_keyword)
# Role: 通用工具包入口，导出重试/缓存/日志装饰器、进度条、显示格式化和进程查找等工具函数






"""
Utils module for Ginkgo library
"""

from ginkgo.libs.utils.common import (
    try_wait_counter, str2bool, time_logger, format_time_seconds,
    skip_if_ran, retry, datasource_retry, cache_with_expiration, RichProgress
)
from ginkgo.libs.utils.display import (
    pretty_repr, base_repr, fix_string_length, chinese_count, GinkgoColor
)

# Optional imports
try:
    from ginkgo.libs.utils.codes import cn_index
except ImportError:
    pass

try:
    from ginkgo.libs.utils.process import find_process_by_keyword
except ImportError:
    pass

try:
    from ginkgo.libs.utils.log_utils import is_container_environment, get_container_metadata
except ImportError:
    pass

__all__ = [
    # Common utilities
    "try_wait_counter", "str2bool", "time_logger", "format_time_seconds",
    "skip_if_ran", "retry", "datasource_retry", "cache_with_expiration", "RichProgress",
    
    # Display utilities
    "pretty_repr", "base_repr", "fix_string_length", "chinese_count", "GinkgoColor",
    
    # Optional imports
    "cn_index", "find_process_by_keyword",

    # Log utilities
    "is_container_environment", "get_container_metadata"
]
