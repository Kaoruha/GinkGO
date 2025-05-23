from ginkgo.libs.ginkgo_normalize import *
from ginkgo.libs.ginkgo_pretty import *
from ginkgo.libs.ginkgo_libs import *
from ginkgo.libs.ginkgo_math import *
from ginkgo.libs.ginkgo_number import *
from ginkgo.libs.ginkgo_links import *
from ginkgo.libs.ginkgo_conf import *
from ginkgo.libs.ginkgo_logger import *
from ginkgo.libs.ginkgo_thread import *

GLOG = GinkgoLogger(logger_name="ginkgo", file_names=["ginkgo.log"], console_log=True)
GCONF = GinkgoConfig()
GTM = GinkgoThreadManager()

__all__ = [
    "GinkgoLogger",
    "GinkgoThreadManager",
    "GTM",
    "GLOG",
    "GCONF",
    "datetime_normalize",
    "try_wait_counter",
    "Number",
    "to_decimal",
    "time_logger",
    "retry",
    "chinese_count",
    "pretty_repr",
    "base_repr",
    "fix_string_length",
    "RichProgress",
    "redis_cache",
    "skip_if_ran",
]
