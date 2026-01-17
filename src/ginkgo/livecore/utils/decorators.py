# Upstream: TaskTimer (定时任务调度器)
# Downstream: 无（工具函数）
# Role: 装饰器工具函数

import functools
from typing import Callable, Any
from ginkgo.libs import GLOG


def safe_job_wrapper(func: Callable) -> Callable:
    """
    任务安全包装装饰器

    提供任务崩溃隔离，异常捕获，错误日志功能。
    用于TaskTimer的定时任务方法，确保单个任务失败不影响其他任务。

    Args:
        func: 被装饰的函数

    Returns:
        包装后的函数

    Example:
        @safe_job_wrapper
        def _bar_snapshot_job(self):
            # 任务代码
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            GLOG.DEBUG(f"Job {func.__name__} started")
            result = func(*args, **kwargs)
            GLOG.DEBUG(f"Job {func.__name__} completed")
            return result

        except Exception as e:
            GLOG.ERROR(f"Job {func.__name__} failed: {e}")
            # 可以添加告警通知逻辑
            # send_alert(f"TaskTimer job {func.__name__} failed: {e}")
            return None

    return wrapper
