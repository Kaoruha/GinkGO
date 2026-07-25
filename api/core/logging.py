"""
API Server日志配置
集成Ginkgo的GLOG和Rich格式化
"""

import logging
import sys
from pythonjsonlogger import jsonlogger

# 尝试导入Ginkgo的GLOG
try:
    from ginkgo.libs import GLOG
    GINKGO_GLOG_AVAILABLE = True
except ImportError:
    GINKGO_GLOG_AVAILABLE = False


class TraceIdFilter(logging.Filter):
    """注入 GLOG contextvar 的 trace_id 到 stdlib 日志 record (#6784)。

    API 业务层用 stdlib logging (与 GINKGO 的 structlog 分离)，本 Filter 让
    stdlib 日志也携带请求级 trace_id，与 GLOG/ecs_processor 输出对齐，
    使一个 trace_id 能 grep 出该请求在 API 进程内的全部日志行。
    """

    def filter(self, record):
        try:
            from ginkgo.libs.core.logger import _trace_id_ctx

            tid = _trace_id_ctx.get()
        except ImportError:
            tid = None
        record.trace_id = tid or "-"
        return True


def setup_logging(name: str = "apiserver"):
    """设置API Server日志"""

    # 总是创建独立logger，避免GLOG的API不兼容问题
    # 如果需要集成GLOG，可以通过处理器方式添加

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # #6784: 注入请求级 trace_id 到每条 stdlib 日志 record (TraceIdFilter 读
    # GLOG contextvar)，使 stdlib 日志与 GLOG/ecs_processor 输出对齐
    logger.addFilter(TraceIdFilter())

    # 控制台处理器（使用Rich格式）
    if sys.stdout.isatty():
        from rich.logging import RichHandler

        handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=False,
            show_path=False,
        )
        # local 模式：trace_id 行内可见
        handler.setFormatter(logging.Formatter("trace=%(trace_id)s %(message)s"))
    else:
        # JSON格式用于文件输出 (container 模式：trace_id 平铺字段)
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(trace_id)s'
        )
        handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


# 默认日志实例（用于直接导入）
logger = setup_logging()
