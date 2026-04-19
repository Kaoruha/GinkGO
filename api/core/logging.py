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


def setup_logging(name: str = "apiserver"):
    """设置API Server日志"""

    # 总是创建独立logger，避免GLOG的API不兼容问题
    # 如果需要集成GLOG，可以通过处理器方式添加

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 控制台处理器（使用Rich格式）
    if sys.stdout.isatty():
        from rich.logging import RichHandler

        handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=False,
            show_path=False,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # JSON格式用于文件输出
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


# 默认日志实例（用于直接导入）
logger = setup_logging()
