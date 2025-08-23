"""
Utils module for Ginkgo library
"""

from .common import (
    try_wait_counter, str2bool, time_logger, format_time_seconds,
    skip_if_ran, retry, datasource_retry, cache_with_expiration, RichProgress
)
from .display import (
    pretty_repr, base_repr, fix_string_length, chinese_count, GinkgoColor
)

# Optional imports
try:
    from .codes import cn_index
except ImportError:
    pass

try:
    from .links import GinkgoSingleLinkedNode, GinkgoSingleLinkedList
except ImportError:
    pass

try:
    from .process import find_process_by_keyword
except ImportError:
    pass

__all__ = [
    # Common utilities
    "try_wait_counter", "str2bool", "time_logger", "format_time_seconds",
    "skip_if_ran", "retry", "datasource_retry", "cache_with_expiration", "RichProgress",
    
    # Display utilities
    "pretty_repr", "base_repr", "fix_string_length", "chinese_count", "GinkgoColor",
    
    # Optional imports
    "cn_index", "GinkgoSingleLinkedNode", "GinkgoSingleLinkedList", "find_process_by_keyword"
]