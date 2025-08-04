"""
Ginkgo 工具库统一入口
重构后的模块化导入接口，保持向后兼容性
"""

# 核心模块导入
from .core.config import GinkgoConfig
from .core.logger import GinkgoLogger
from .core.threading import GinkgoThreadManager

# 数据处理模块导入
from .data.normalize import datetime_normalize
from .data.number import Number, to_decimal
from .data.statistics import t_test, chi2_test
from .data.math import cal_fee

# 工具模块导入
from .utils.common import (
    try_wait_counter,
    str2bool,
    time_logger,
    format_time_seconds,
    skip_if_ran,
    retry,
    cache_with_expiration,
    RichProgress,
)
from .utils.display import pretty_repr, base_repr, fix_string_length, chinese_count, GinkgoColor

# 尝试导入其他工具模块的内容
try:
    from .utils.codes import cn_index
except ImportError:
    cn_index = None

try:
    from .utils.links import GinkgoSingleLinkedNode, GinkgoSingleLinkedList
except ImportError:
    GinkgoSingleLinkedNode = None
    GinkgoSingleLinkedList = None

try:
    from .utils.process import find_process_by_keyword
except ImportError:
    find_process_by_keyword = None

try:
    from .utils.health_check import (
        ensure_services_ready,
        wait_for_ginkgo_services,
        check_clickhouse_ready,
        check_mysql_ready,
        check_redis_ready,
        check_kafka_ready,
        check_docker_containers_running
    )
except ImportError:
    ensure_services_ready = None
    wait_for_ginkgo_services = None
    check_clickhouse_ready = None
    check_mysql_ready = None
    check_redis_ready = None
    check_kafka_ready = None
    check_docker_containers_running = None

# 创建全局实例（保持向后兼容）
GLOG = GinkgoLogger(logger_name="ginkgo", file_names=["ginkgo.log"], console_log=True)
GCONF = GinkgoConfig()
GTM = GinkgoThreadManager()

# 尝试导入校验器模块
try:
    from .validators import (
        validate_component,
        test_component,
        BaseValidator,
        ValidationResult,
        ValidationLevel,
        StrategyValidator,
        AnalyzerValidator,
        RiskValidator,
        SizerValidator,
        ComponentTester,
        ValidationRules
    )
except ImportError:
    # 校验器模块导入失败时设为None
    validate_component = None
    test_component = None
    BaseValidator = None
    ValidationResult = None
    ValidationLevel = None
    StrategyValidator = None
    AnalyzerValidator = None
    RiskValidator = None
    SizerValidator = None
    ComponentTester = None
    ValidationRules = None

# 导出列表 - 保持与原来的 __all__ 兼容
__all__ = [
    # 核心组件
    "GinkgoLogger",
    "GinkgoConfig",
    "GinkgoThreadManager",
    "GLOG",
    "GCONF",
    "GTM",
    # 数据处理
    "datetime_normalize",
    "Number",
    "to_decimal",
    "cal_fee",
    "t_test",
    "chi2_test",
    # 工具函数 - 保持原有的导出名称
    "try_wait_counter",
    "str2bool",
    "time_logger",
    "retry",
    "skip_if_ran",
    "chinese_count",
    "pretty_repr",
    "base_repr",
    "fix_string_length",
    "RichProgress",
    "GinkgoColor",
    # 新增的工具函数
    "format_time_seconds",
    "cache_with_expiration",
    # 其他工具（如果存在）
    "cn_index",
    "GinkgoSingleLinkedNode",
    "GinkgoSingleLinkedList",
    "find_process_by_keyword",
    # 健康检查工具
    "ensure_services_ready",
    "wait_for_ginkgo_services",
    "check_clickhouse_ready",
    "check_mysql_ready",
    "check_redis_ready",
    "check_kafka_ready",
    "check_docker_containers_running",
    # 组件校验器
    "validate_component",
    "test_component",
    "BaseValidator",
    "ValidationResult",
    "ValidationLevel",
    "StrategyValidator",
    "AnalyzerValidator",
    "RiskValidator",
    "SizerValidator",
    "ComponentTester",
    "ValidationRules",
]
