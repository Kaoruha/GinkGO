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
    """从 GLOG _trace_id_ctx 读 trace_id 注入 LogRecord，让 api 层标准 logging 也带 trace_id。

    与 src 层 GLOG ecs_processor 共享同一 _trace_id_ctx 源头（#6784 可观测层接入 1/4）。
    TraceIdMiddleware 在请求入口 set _trace_id_ctx，本 filter 让 api 层 logger 输出同步可见。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if GINKGO_GLOG_AVAILABLE:
            try:
                record.trace_id = GLOG.get_trace_id() or "-"
            except Exception:
                record.trace_id = "-"
        else:
            record.trace_id = "-"
        return True


def setup_logging(name: str = "apiserver"):
    """设置API Server日志"""

    # 总是创建独立logger，避免GLOG的API不兼容问题
    # 如果需要集成GLOG，可以通过处理器方式添加

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # trace_id 注入（#6784）：logger 级 filter，所有 handler 输出经 %(trace_id)s 可见
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
        handler.setFormatter(logging.Formatter("[trace_id=%(trace_id)s] %(message)s"))
    else:
        # JSON格式用于文件输出
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(trace_id)s %(message)s'
        )
        handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


# 默认日志实例（用于直接导入）
logger = setup_logging()
